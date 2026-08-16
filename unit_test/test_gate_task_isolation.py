# -*- coding: utf-8 -*-
"""D1 回归测试：门禁跨任务串门隔离

覆盖：gate_open 只认当前任务目录自身的 .gate.json；
任意其他任务/历史任务的开闸文件不得影响当前任务判定。
"""

import json
import tempfile
import unittest
from pathlib import Path

from harness.core import gate

SECRET = "test-secret-for-d1"


def _make_gate_file(task_dir: Path, run_id: str, secret: str) -> Path:
    """在任务目录写入合法 .gate.json v2（含真实 result 文件）。"""
    result = task_dir / "unit_test" / "test" / "result.txt"
    result.parent.mkdir(parents=True)
    result.write_text("OK: 2 passed", encoding="utf-8")
    g = gate.build_gate_v2(
        run_id=run_id,
        task_dir=str(task_dir),
        result_files=[result],
        total=2,
        passed=2,
        secret=secret,
    )
    p = task_dir / gate.GATE_FILENAME
    p.write_text(json.dumps(g, ensure_ascii=False), encoding="utf-8")
    return p


class TestGateTaskIsolation(unittest.TestCase):
    """门禁串门回归（D1）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.task_a = self.root / "opencode_schedule" / "20260814" / "20260814任务A"
        self.task_b = self.root / "opencode_schedule" / "20260814" / "20260814任务B"
        self.task_a.mkdir(parents=True)
        self.task_b.mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def test_find_gate_only_scans_own_task_dir(self):
        """find_gate_file 只查任务目录自身，不递归、不跨任务。"""
        _make_gate_file(self.task_a, "20260814任务A", SECRET)
        self.assertIsNone(gate.find_gate_file(self.task_b))
        self.assertIsNotNone(gate.find_gate_file(self.task_a))

    def test_task_b_fail_closed_while_task_a_open(self):
        """旧版 bug 回归：A 已开闸，B 无 .gate.json 仍 fail-closed。"""
        _make_gate_file(self.task_a, "20260814任务A", SECRET)
        opened, code = gate.gate_open(self.task_b, "20260814任务B", SECRET)
        self.assertFalse(opened)
        self.assertEqual(code, gate.RC_GATE_MISSING)

    def test_task_b_open_requires_own_gate(self):
        """B 必须有自己的合法 .gate.json 才能开闸。"""
        _make_gate_file(self.task_a, "20260814任务A", SECRET)
        _make_gate_file(self.task_b, "20260814任务B", SECRET)
        opened_b, code_b = gate.gate_open(self.task_b, "20260814任务B", SECRET)
        opened_a, code_a = gate.gate_open(self.task_a, "20260814任务A", SECRET)
        self.assertTrue(opened_a)
        self.assertEqual(code_a, gate.RC_GATE_PASS)
        self.assertTrue(opened_b)
        self.assertEqual(code_b, gate.RC_GATE_PASS)

    def test_run_id_mismatch_rejected(self):
        """run_id 与任务目录不一致（串用他人 gate 文件）→ 拒绝。"""
        _make_gate_file(self.task_b, "20260814任务B", SECRET)
        opened, code = gate.gate_open(self.task_b, "20260814任务A", SECRET)
        self.assertFalse(opened)
        self.assertEqual(code, gate.RC_GATE_RUN_ID_MISMATCH)

    def test_legacy_v1_gate_ignored(self):
        """旧版 .gate.json v1（无 schema_version/token）不再被信任。"""
        legacy = {
            "test_passed": True,
            "total": 41,
            "passed": 41,
            "updated_at": "2026-08-01 10:00:00",
        }
        (self.task_b / gate.GATE_FILENAME).write_text(
            json.dumps(legacy), encoding="utf-8"
        )
        opened, code = gate.gate_open(self.task_b, "20260814任务B", SECRET)
        self.assertFalse(opened)
        self.assertEqual(code, gate.RC_GATE_SCHEMA)

    def test_missing_gate_fail_closed(self):
        """无任何 gate 文件 → fail-closed。"""
        opened, code = gate.gate_open(self.task_b, "20260814任务B", SECRET)
        self.assertFalse(opened)
        self.assertEqual(code, gate.RC_GATE_MISSING)


if __name__ == "__main__":
    unittest.main()
