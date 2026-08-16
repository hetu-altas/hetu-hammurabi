# -*- coding: utf-8 -*-
"""H4 续签机制回归测试：re-seal 刷新 updated_at 不篡改其余字段

覆盖：
- 落闸后模拟 11 分钟 → GATE_STALE（10 分钟窗口外）
- re-seal 后同一操作放行
- re-seal 不改 run_id/result_files/total/passed/test_passed
- re-seal 前重读核对（result 被改 → 拒绝）
- result 文件缺失 → 拒绝续签
- 无 .gate.json → 拒绝续签
- re_seal 审计事件落盘（runlog JSONL，event_type=re_seal）
- schema_version / run_id 不符 → 拒绝续签
- 并发更新（updated_at 已变）→ 拒绝续签
"""

import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from harness.core import gate, recorder, seal

SECRET = "test-secret-for-lease"

RESULT_TEXT = """\
测试总数: 5
成功: 5
失败: 0
错误: 0
"""


class TestGateLease(unittest.TestCase):
    """续签机制（正常/反例/边界）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.task = self.root / "opencode_schedule" / "20260815" / "20260815任务L"
        self.task.mkdir(parents=True)
        self.run_id = "20260815任务L"
        self.result = self.task / "unit_test" / "test" / "r.txt"
        self.result.parent.mkdir(parents=True)
        self.result.write_text(RESULT_TEXT, encoding="utf-8")
        self.gate_file = self.task / gate.GATE_FILENAME

    def tearDown(self):
        self._tmp.cleanup()

    def _seal(self, updated_at: str) -> dict:
        """以指定时间落闸。"""
        g = gate.build_gate_v2(
            run_id=self.run_id,
            task_dir=str(self.task),
            result_files=[self.result],
            total=5,
            passed=5,
            secret=SECRET,
            updated_at=updated_at,
        )
        self.gate_file.write_text(json.dumps(g, ensure_ascii=False), encoding="utf-8")
        return g

    def test_stale_after_11_minutes(self):
        """正常案例：落闸后模拟 11 分钟 → GATE_STALE。"""
        now = datetime.now()
        self._seal((now - timedelta(minutes=11)).isoformat(timespec="seconds"))
        opened, code = gate.gate_open(self.task, self.run_id, SECRET, now=now)
        self.assertFalse(opened)
        self.assertEqual(code, gate.RC_GATE_STALE)

    def test_reseal_refreshes_and_allows(self):
        """正常案例：GATE_STALE → re-seal → 同一操作放行。"""
        now = datetime.now()
        self._seal((now - timedelta(minutes=11)).isoformat(timespec="seconds"))
        # 过期时写日志被拦
        r = gate.decide(str(self.task / "任务1研发日志.md"), "", self.task, self.run_id, SECRET, now=now)
        self.assertTrue(r["blocked"])
        # re-seal（now 注入）
        g2 = seal.re_seal(self.task, self.run_id, SECRET, now=now)
        self.assertEqual(g2["updated_at"], now.isoformat(timespec="seconds"))
        # 同一操作放行
        r2 = gate.decide(str(self.task / "任务1研发日志.md"), "", self.task, self.run_id, SECRET, now=now)
        self.assertFalse(r2["blocked"])

    def test_reseal_keeps_fields_unchanged(self):
        """正常案例：re-seal 不改 run_id/result_files/total/passed/test_passed。"""
        now = datetime.now()
        g1 = self._seal((now - timedelta(minutes=2)).isoformat(timespec="seconds"))
        g2 = seal.re_seal(self.task, self.run_id, SECRET, now=now)
        for key in ("run_id", "result_files", "total", "passed", "test_passed", "written_by"):
            self.assertEqual(g2[key], g1[key], key)
        self.assertNotEqual(g2["updated_at"], g1["updated_at"])
        # 新 token 校验通过（重签）
        self.assertTrue(gate.verify_gate_token(g2, SECRET))

    def test_reseal_result_modified_rejected(self):
        """反案例：re-seal 前重读核对——result 被改（数字不符）→ 拒绝。"""
        now = datetime.now()
        self._seal((now - timedelta(minutes=2)).isoformat(timespec="seconds"))
        self.result.write_text("测试总数: 99\n成功: 99\n失败: 0\n错误: 0\n", encoding="utf-8")
        with self.assertRaises(seal.SealError) as ctx:
            seal.re_seal(self.task, self.run_id, SECRET, now=now)
        self.assertIn("数字不符", str(ctx.exception))

    def test_reseal_result_missing_rejected(self):
        """反案例：result 文件缺失 → 拒绝续签。"""
        now = datetime.now()
        self._seal((now - timedelta(minutes=2)).isoformat(timespec="seconds"))
        self.result.unlink()
        with self.assertRaises(seal.SealError) as ctx:
            seal.re_seal(self.task, self.run_id, SECRET, now=now)
        self.assertIn("缺失", str(ctx.exception))

    def test_reseal_no_gate_rejected(self):
        """反案例：无 .gate.json → 拒绝续签（无闸可续）。"""
        with self.assertRaises(seal.SealError) as ctx:
            seal.re_seal(self.task, self.run_id, SECRET)
        self.assertIn("无 .gate.json", str(ctx.exception))

    def test_reseal_wrong_run_id_rejected(self):
        """反案例：run_id 不一致（跨任务续签）→ 拒绝。"""
        now = datetime.now()
        self._seal((now - timedelta(minutes=2)).isoformat(timespec="seconds"))
        with self.assertRaises(seal.SealError) as ctx:
            seal.re_seal(self.task, "20260815任务OTHER", SECRET, now=now)
        self.assertIn("run_id 不一致", str(ctx.exception))

    def test_reseal_schema_v1_rejected(self):
        """反案例：schema_version=1 旧闸 → 拒绝续签。"""
        now = datetime.now()
        g = self._seal((now - timedelta(minutes=2)).isoformat(timespec="seconds"))
        g["schema_version"] = 1
        self.gate_file.write_text(json.dumps(g, ensure_ascii=False), encoding="utf-8")
        with self.assertRaises(seal.SealError) as ctx:
            seal.re_seal(self.task, self.run_id, SECRET, now=now)
        self.assertIn("schema_version", str(ctx.exception))

    def test_reseal_event_written_to_runlog(self):
        """正常案例：re_seal 审计事件落盘（runlog JSONL，event_type=re_seal）。"""
        now = datetime.now()
        self._seal((now - timedelta(minutes=2)).isoformat(timespec="seconds"))
        runlog = self.root / "runlog"
        seal.re_seal(self.task, self.run_id, SECRET, runlog_root=runlog, project="hetu-demo", now=now)
        events = recorder.events_for_run(runlog, self.run_id)
        reseal_events = [e for e in events if e.get("event_type") == "re_seal"]
        self.assertEqual(len(reseal_events), 1)
        self.assertEqual(reseal_events[0]["status"], "pass")
        self.assertEqual(reseal_events[0]["project"], "hetu-demo")
        self.assertIn("refreshed", reseal_events[0]["detail"])
        self.assertEqual(reseal_events[0]["detail"]["total"], 5)

    def test_write_locked_concurrent_detection(self):
        """反案例：锁内重读比对——updated_at 与期望不符 → 拒绝（并发检测单元）。"""
        now = datetime.now()
        g1 = self._seal((now - timedelta(minutes=2)).isoformat(timespec="seconds"))
        # 期望值与磁盘实际不符（模拟读取后被并发写者更新）
        with self.assertRaises(seal.SealError) as ctx:
            seal.write_gate_locked(
                self.gate_file, g1, expected_updated_at="2020-01-01T00:00:00"
            )
        self.assertIn("已被并发更新", str(ctx.exception))
        # 期望值与磁盘一致 → 正常写入
        seal.write_gate_locked(self.gate_file, g1, expected_updated_at=g1["updated_at"])
        self.assertTrue(gate.load_gate(self.gate_file)["updated_at"] == g1["updated_at"])


if __name__ == "__main__":
    unittest.main()
