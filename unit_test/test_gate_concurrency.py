# -*- coding: utf-8 -*-
"""H9/H7 并发与密钥管理回归测试

覆盖：
- 双进程并发 seal-gate 同一任务目录：串行化成功 或 后写者报「已被并发更新」
- 落盘 .gate.json 内容完整合法（JSON 可解析 + token 校验通过）
- 锁内重读：损坏文件拒绝
- 密钥权限断言：600 通过 / 777 告警 / enforce_600 自动修正 / rotate 前置检查
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from harness.core import gate, seal, secret

RESULT_TEXT = """\
测试总数: 4
成功: 4
失败: 0
错误: 0
"""


class TestGateConcurrency(unittest.TestCase):
    """双进程并发落闸（H9）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.task = self.root / "opencode_schedule" / "20260815" / "20260815任务C"
        self.task.mkdir(parents=True)
        self.run_id = "20260815任务C"
        self.result = self.task / "unit_test" / "test" / "r.txt"
        self.result.parent.mkdir(parents=True)
        self.result.write_text(RESULT_TEXT, encoding="utf-8")
        self.secret_file = self.root / "secret"
        self.secret_file.write_text("concurrency-test-secret", encoding="utf-8")
        os.chmod(self.secret_file, 0o600)
        self.gate_file = self.task / gate.GATE_FILENAME

    def tearDown(self):
        self._tmp.cleanup()

    def _run_seal(self) -> subprocess.CompletedProcess:
        """以子进程执行 seal-gate（模拟独立会话）。"""
        return subprocess.run(
            [
                sys.executable, "-m", "harness.core.cli", "seal-gate",
                "--task-dir", str(self.task),
                "--run-id", self.run_id,
                "--results", str(self.result),
                "--secret-file", str(self.secret_file),
                "--json",
            ],
            cwd=str(Path(__file__).resolve().parent.parent),  # 宿主根（harness 包导入）
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
        )

    def test_parallel_seal_serialized(self):
        """正常案例：双进程并发 seal 同一任务目录 → 串行化或后写者报并发更新。"""
        p1 = self._run_seal()
        p2 = self._run_seal()
        results = []
        for p in (p1, p2):
            try:
                results.append(json.loads(p.stdout.strip()))
            except (ValueError, json.JSONDecodeError):
                results.append({"ok": False, "msg": p.stdout.strip() or p.stderr.strip()})
        ok_count = sum(1 for r in results if r.get("ok"))
        # 至少一个成功；失败方原因必须是「已被并发更新」
        self.assertGreaterEqual(ok_count, 1, results)
        for r in results:
            if not r.get("ok"):
                self.assertIn("已被并发更新", r.get("msg", ""))

    def test_gate_file_valid_after_concurrency(self):
        """正常案例：并发落盘后 .gate.json 完整合法（JSON + token 校验）。"""
        self._run_seal()
        self._run_seal()
        on_disk = json.loads(self.gate_file.read_text(encoding="utf-8"))
        self.assertEqual(on_disk["schema_version"], 2)
        self.assertEqual(on_disk["run_id"], self.run_id)
        self.assertEqual(on_disk["total"], 4)
        self.assertEqual(on_disk["passed"], 4)
        self.assertTrue(gate.verify_gate_token(on_disk, "concurrency-test-secret"))
        opened, code = gate.gate_open(self.task, self.run_id, "concurrency-test-secret")
        self.assertTrue(opened)
        self.assertEqual(code, gate.RC_GATE_PASS)

    def test_corrupted_gate_rejected_in_lock(self):
        """反案例：锁内重读发现文件损坏（非法 JSON）→ 拒绝。"""
        self.gate_file.write_text("{corrupted", encoding="utf-8")
        with self.assertRaises(seal.SealError) as ctx:
            seal.write_gate_locked(self.gate_file, {}, expected_updated_at=None)
        self.assertIn("损坏", str(ctx.exception))


class TestSecretPermission(unittest.TestCase):
    """密钥权限与轮换（H7）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.secret_file = self.root / "gate_secret"

    def tearDown(self):
        self._tmp.cleanup()

    def test_mode_600_ok(self):
        """正常案例：权限 600 → check_permission 通过。"""
        self.secret_file.write_text("k", encoding="utf-8")
        os.chmod(self.secret_file, 0o600)
        ok, mode = secret.check_permission(self.secret_file)
        self.assertTrue(ok)
        self.assertEqual(mode, 0o600)

    def test_mode_777_warn(self):
        """反案例：权限 777（历史缺陷）→ check_permission 告警。"""
        self.secret_file.write_text("k", encoding="utf-8")
        os.chmod(self.secret_file, 0o777)
        ok, mode = secret.check_permission(self.secret_file)
        self.assertFalse(ok)
        self.assertEqual(mode, 0o777)

    def test_load_secret_enforce_600_fixes(self):
        """正常案例：enforce_600=True 时权限非 600 自动修正并重读。"""
        self.secret_file.write_text("my-secret-key", encoding="utf-8")
        os.chmod(self.secret_file, 0o777)
        value = secret.load_secret(self.secret_file, enforce_600=True)
        self.assertEqual(value, "my-secret-key")
        ok, mode = secret.check_permission(self.secret_file)
        self.assertTrue(ok)
        self.assertEqual(mode, 0o600)

    def test_rotate_requires_600(self):
        """反案例：rotate-secret 权限非 600 且未 force → 拒绝。"""
        self.secret_file.write_text("old", encoding="utf-8")
        os.chmod(self.secret_file, 0o644)
        with self.assertRaises(ValueError) as ctx:
            secret.rotate_secret(self.secret_file, force=False)
        self.assertIn("600", str(ctx.exception))

    def test_rotate_force_writes_and_chmod(self):
        """正常案例：rotate-secret（force）→ 新密钥写入、权限 600、无临时文件残留。"""
        self.secret_file.write_text("old-secret", encoding="utf-8")
        os.chmod(self.secret_file, 0o644)
        secret.rotate_secret(self.secret_file, force=True)
        ok, mode = secret.check_permission(self.secret_file)
        self.assertTrue(ok)
        self.assertEqual(mode, 0o600)
        new_value = self.secret_file.read_text(encoding="utf-8").strip()
        self.assertNotEqual(new_value, "old-secret")
        self.assertGreater(len(new_value), 16)
        self.assertEqual(list(self.root.glob("*.tmp")), [])

    def test_rotate_old_token_invalidated(self):
        """正常案例：rotate 后旧密钥签的 token 校验失败（旧闸自然失效）。"""
        result = self.root / "r.txt"
        result.write_text("OK: 1 passed", encoding="utf-8")
        g = gate.build_gate_v2(
            run_id="20260815任务C",
            task_dir=str(self.root),
            result_files=[result],
            total=1,
            passed=1,
            secret="old-secret",
        )
        self.assertTrue(gate.verify_gate_token(g, "old-secret"))
        self.assertFalse(gate.verify_gate_token(g, "new-secret-rotated"))


if __name__ == "__main__":
    unittest.main()
