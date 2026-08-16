# -*- coding: utf-8 -*-
"""D2 回归测试：.gate.json v2 token 信任模型（防伪造）

覆盖：写/验分离；篡改关键字段、伪造 token、错误 run_id、
陈旧时间戳、旧版本 schema 一律拒绝；tester 自写无 token 不被信任。
"""

import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from harness.core import gate

SECRET = "test-secret-for-d2"


class TestGateToken(unittest.TestCase):
    """token 信任模型回归（D2）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.task = self.root / "opencode_schedule" / "20260814" / "20260814任务X"
        self.task.mkdir(parents=True)
        self.result = self.task / "unit_test" / "test" / "test_xxx_result.txt"
        self.result.parent.mkdir(parents=True)
        self.result.write_text("OK: 3 passed", encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def _write_gate(self, gate_dict: dict):
        (self.task / gate.GATE_FILENAME).write_text(
            json.dumps(gate_dict, ensure_ascii=False), encoding="utf-8"
        )

    def _legit_gate(self, **overrides) -> dict:
        g = gate.build_gate_v2(
            run_id="20260814任务X",
            task_dir=str(self.task),
            result_files=[self.result],
            total=3,
            passed=3,
            secret=SECRET,
        )
        g.update(overrides)
        return g

    def test_legit_gate_opens(self):
        """合法落闸（编排器 build_gate_v2）→ 开闸。"""
        self._write_gate(self._legit_gate())
        opened, code = gate.gate_open(self.task, "20260814任务X", SECRET)
        self.assertTrue(opened)
        self.assertEqual(code, gate.RC_GATE_PASS)

    def test_tamper_test_passed_fake_pass_rejected(self):
        """伪造通过：合法失败落闸改 test_passed=false→true → token 校验失败。"""
        g = gate.build_gate_v2(
            run_id="20260814任务X",
            task_dir=str(self.task),
            result_files=[self.result],
            total=3,
            passed=1,  # 失败落闸（test_passed=false，带合法 token）
            secret=SECRET,
        )
        g["test_passed"] = True  # 攻击：改成通过
        self._write_gate(g)
        opened, code = gate.gate_open(self.task, "20260814任务X", SECRET)
        self.assertFalse(opened)
        self.assertEqual(code, gate.RC_GATE_TOKEN_INVALID)

    def test_failed_gate_legit_rejected(self):
        """合法失败落闸（test_passed=false）→ GATE_NOT_PASSED。"""
        g = gate.build_gate_v2(
            run_id="20260814任务X",
            task_dir=str(self.task),
            result_files=[self.result],
            total=3,
            passed=1,
            secret=SECRET,
        )
        self._write_gate(g)
        opened, code = gate.gate_open(self.task, "20260814任务X", SECRET)
        self.assertFalse(opened)
        self.assertEqual(code, gate.RC_GATE_NOT_PASSED)

    def test_tamper_passed_count_rejected(self):
        """篡改 passed 计数 → token 校验失败。"""
        g = self._legit_gate()
        g["passed"] = 99
        self._write_gate(g)
        opened, code = gate.gate_open(self.task, "20260814任务X", SECRET)
        self.assertFalse(opened)
        self.assertEqual(code, gate.RC_GATE_TOKEN_INVALID)

    def test_forged_token_rejected(self):
        """伪造 token（无密钥）→ 校验失败。"""
        g = self._legit_gate()
        g["gate_token"] = "deadbeef" * 8
        self._write_gate(g)
        opened, code = gate.gate_open(self.task, "20260814任务X", SECRET)
        self.assertFalse(opened)
        self.assertEqual(code, gate.RC_GATE_TOKEN_INVALID)

    def test_wrong_secret_rejected(self):
        """使用错误宿主密钥校验 → 失败。"""
        self._write_gate(self._legit_gate())
        opened, code = gate.gate_open(self.task, "20260814任务X", "wrong-secret")
        self.assertFalse(opened)
        self.assertEqual(code, gate.RC_GATE_TOKEN_INVALID)

    def test_tester_self_written_no_token_rejected(self):
        """tester 自写（无 token 或 token 空）不被信任。"""
        g = self._legit_gate()
        g["written_by"] = "charter-tester"
        g.pop("gate_token")
        self._write_gate(g)
        opened, code = gate.gate_open(self.task, "20260814任务X", SECRET)
        self.assertFalse(opened)
        self.assertEqual(code, gate.RC_GATE_TOKEN_INVALID)

    def test_stale_gate_rejected(self):
        """陈旧时间戳（超过新鲜度窗口）→ 拒绝。
        合法构造：落闸时就用陈旧时间戳（token 与陈旧时间匹配）。"""
        stale_ts = (datetime.now() - timedelta(minutes=30)).isoformat(timespec="seconds")
        g = gate.build_gate_v2(
            run_id="20260814任务X",
            task_dir=str(self.task),
            result_files=[self.result],
            total=3,
            passed=3,
            secret=SECRET,
            updated_at=stale_ts,
        )
        self._write_gate(g)
        opened, code = gate.gate_open(self.task, "20260814任务X", SECRET)
        self.assertFalse(opened)
        self.assertEqual(code, gate.RC_GATE_STALE)

    def test_result_file_modified_after_gate_invalidates(self):
        """落闸后篡改 result 文件内容 → 摘要变化 → token 校验失败。"""
        self._write_gate(self._legit_gate())
        self.result.write_text("OK: 999 passed", encoding="utf-8")
        opened, code = gate.gate_open(self.task, "20260814任务X", SECRET)
        self.assertFalse(opened)
        self.assertEqual(code, gate.RC_GATE_TOKEN_INVALID)

    def test_tamper_total_rejected(self):
        """篡改 total 计数（独立评审补测）→ token 校验失败。"""
        g = self._legit_gate()
        g["total"] = 999
        self._write_gate(g)
        opened, code = gate.gate_open(self.task, "20260814任务X", SECRET)
        self.assertFalse(opened)
        self.assertEqual(code, gate.RC_GATE_TOKEN_INVALID)

    def test_tamper_updated_at_rejected(self):
        """篡改 updated_at 续命（独立评审漏洞：陈旧门禁改时间戳绕过新鲜度）
        → updated_at 已纳入签名 → 篡改后 token 校验失败。
        攻击构造：合法落闸（5 小时前，token 匹配旧时间）→ 攻击者把
        updated_at 改成当前时间，不重签 token。"""
        old_ts = (datetime.now() - timedelta(hours=5)).isoformat(timespec="seconds")
        g = gate.build_gate_v2(
            run_id="20260814任务X",
            task_dir=str(self.task),
            result_files=[self.result],
            total=3,
            passed=3,
            secret=SECRET,
            updated_at=old_ts,
        )
        self._write_gate(g)
        # 攻击：改 updated_at 为当前时间（token 不变）
        g2 = json.loads((self.task / gate.GATE_FILENAME).read_text(encoding="utf-8"))
        g2["updated_at"] = datetime.now().isoformat(timespec="seconds")
        self._write_gate(g2)
        opened, code = gate.gate_open(self.task, "20260814任务X", SECRET)
        self.assertFalse(opened)
        self.assertEqual(code, gate.RC_GATE_TOKEN_INVALID)

    def test_future_timestamp_rejected(self):
        """未来时间戳（独立评审补测）→ 拒绝（GATE_STALE）。"""
        future_ts = (datetime.now() + timedelta(hours=1)).isoformat(timespec="seconds")
        g = self._legit_gate(updated_at=future_ts)
        # 重签 token（updated_at 已入签名，未来时间戳需编排器配合才可能产生）
        g["gate_token"] = gate.compute_gate_token(g, SECRET)
        self._write_gate(g)
        opened, code = gate.gate_open(self.task, "20260814任务X", SECRET)
        self.assertFalse(opened)
        self.assertEqual(code, gate.RC_GATE_STALE)

    def test_empty_result_files_rejected(self):
        """空 result_files（独立评审补测：零证据放行）→ 拒绝。"""
        g = self._legit_gate()
        g["result_files"] = []
        g["gate_token"] = gate.compute_gate_token(g, SECRET)
        self._write_gate(g)
        opened, code = gate.gate_open(self.task, "20260814任务X", SECRET)
        self.assertFalse(opened)
        self.assertEqual(code, gate.RC_GATE_NO_RESULTS)

    def test_build_gate_v2_empty_results_raises(self):
        """编排器零证据落闸 → build_gate_v2 直接拒绝。"""
        with self.assertRaises(ValueError):
            gate.build_gate_v2(
                run_id="20260814任务X",
                task_dir=str(self.task),
                result_files=[],
                total=0,
                passed=0,
                secret=SECRET,
            )

    def test_schema_v1_rejected(self):
        """schema_version=1 的旧文件 → 拒绝。"""
        g = self._legit_gate(schema_version=1)
        self._write_gate(g)
        opened, code = gate.gate_open(self.task, "20260814任务X", SECRET)
        self.assertFalse(opened)
        self.assertEqual(code, gate.RC_GATE_SCHEMA)

    def test_not_passed_rejected(self):
        """test_passed=false（测试失败落闸）→ 拒绝。"""
        g = gate.build_gate_v2(
            run_id="20260814任务X",
            task_dir=str(self.task),
            result_files=[self.result],
            total=3,
            passed=1,
            secret=SECRET,
        )
        self._write_gate(g)
        opened, code = gate.gate_open(self.task, "20260814任务X", SECRET)
        self.assertFalse(opened)
        self.assertEqual(code, gate.RC_GATE_NOT_PASSED)


if __name__ == "__main__":
    unittest.main()
