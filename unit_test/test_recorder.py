# -*- coding: utf-8 -*-
"""运行事件采集回归测试（recorder）

覆盖：事件 schema 完整性、按日落盘、run_id 分文件、
追加不覆盖、非法类型报错、过滤查询。
"""

import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from harness.core import recorder

SCHEMA_FIELDS = set(recorder.EVENT_SCHEMA_FIELDS)


class TestRecorder(unittest.TestCase):
    """recorder 采集与落盘。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.runlog = self.root / "runlog"

    def tearDown(self):
        self._tmp.cleanup()

    def test_record_event_schema(self):
        """事件字段齐全且符合 schema。"""
        ev = recorder.record_event(
            self.runlog,
            run_id="20260814任务A",
            node=3,
            node_name="单元测试",
            event_type="node_start",
            status="running",
            project="hetu-thoth",
            round_=1,
        )
        self.assertEqual(set(ev.keys()), SCHEMA_FIELDS)
        self.assertEqual(ev["run_id"], "20260814任务A")
        self.assertEqual(ev["node"], "3")
        self.assertEqual(ev["source"], "live")

    def test_daily_dir_and_run_file(self):
        """按日落盘、按 run_id 分文件。"""
        ts = datetime(2026, 8, 14, 10, 0, 0)
        recorder.record_event(
            self.runlog, "20260814任务A", 1, "分析", "node_start", "running", ts=ts
        )
        recorder.record_event(
            self.runlog, "20260814任务B", 1, "分析", "node_start", "running", ts=ts
        )
        path_a = recorder.event_file_for(self.runlog, "20260814任务A", ts)
        path_b = recorder.event_file_for(self.runlog, "20260814任务B", ts)
        self.assertTrue(path_a.is_file())
        self.assertTrue(path_b.is_file())
        self.assertEqual(path_a.parent.name, "20260814")
        # 各文件仅含本任务事件
        self.assertEqual(len(list(recorder.iter_events(self.runlog))), 2)

    def test_append_not_overwrite(self):
        """追加写不覆盖：同文件两次写入 → 两行。"""
        recorder.record_event(self.runlog, "R1", 0, "校验", "node_start", "running")
        recorder.record_event(self.runlog, "R1", 0, "校验", "node_end", "pass")
        path = recorder.event_file_for(self.runlog, "R1")
        lines = path.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(lines), 2)

    def test_invalid_event_type_rejected(self):
        """非法 event_type → ValueError。"""
        with self.assertRaises(ValueError):
            recorder.record_event(
                self.runlog, "R1", 1, "分析", "bogus_type", "running"
            )

    def test_invalid_status_rejected(self):
        """非法 status → ValueError。"""
        with self.assertRaises(ValueError):
            recorder.record_event(
                self.runlog, "R1", 1, "分析", "node_start", "bogus"
            )

    def test_events_for_run_filters(self):
        """events_for_run 按 run_id 过滤且按时间升序。"""
        recorder.record_event(
            self.runlog, "R1", 1, "分析", "node_end", "pass",
            ts=datetime(2026, 8, 14, 11, 0, 0),
        )
        recorder.record_event(
            self.runlog, "R1", 1, "分析", "node_start", "running",
            ts=datetime(2026, 8, 14, 10, 0, 0),
        )
        recorder.record_event(
            self.runlog, "R2", 1, "分析", "node_start", "running",
            ts=datetime(2026, 8, 14, 9, 0, 0),
        )
        events = recorder.events_for_run(self.runlog, "R1")
        self.assertEqual(len(events), 2)
        self.assertTrue(events[0]["ts"] < events[1]["ts"])
        self.assertTrue(all(e["run_id"] == "R1" for e in events))

    def test_detail_and_extra_preserved(self):
        """detail/extra 字段原样保留。"""
        ev = recorder.record_event(
            self.runlog, "R1", 3, "单元测试", "gate_block", "blocked",
            detail={"msg": "门禁未过", "tool": "bash"},
            extra={"code": "GATE_MISSING"},
        )
        self.assertEqual(ev["detail"]["msg"], "门禁未过")
        self.assertEqual(ev["extra"]["code"], "GATE_MISSING")


if __name__ == "__main__":
    unittest.main()
