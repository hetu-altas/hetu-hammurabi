# -*- coding: utf-8 -*-
"""D3/D4 回归测试：编排冲突澄清与绕过面覆盖

D3：研发流程状态.md 视为审计记录放行，仅拦研发日志。
D4：通知外呼（curl/requests 直连钉钉）拦截、唯一出口放行、
    危险命令任意位置匹配、日志文件变体识别、读操作不误伤。
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from harness.core import gate

SECRET = "test-secret-for-d4"


class TestGateLogRules(unittest.TestCase):
    """研发日志识别（D3/D4）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.task = self.root / "opencode_schedule" / "20260814" / "20260814任务Y"
        self.task.mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def test_standard_log_name_blocked(self):
        """标准研发日志命名 → 拦截。"""
        p = str(self.task / "任务1研发日志.md")
        self.assertTrue(gate.is_log_file_write(p))

    def test_variant_log_name_blocked(self):
        """重命名/变体日志命名（D4）→ 拦截。"""
        for name in ("重命名研发日志_v2.md", "研发日志20260814.md", "任务9研发日志终稿.md"):
            self.assertTrue(gate.is_log_file_write(str(self.task / name)))

    def test_status_file_allowed(self):
        """研发流程状态.md 为审计记录（D3）→ 放行。"""
        p = str(self.task / "研发流程状态.md")
        self.assertFalse(gate.is_log_file_write(p))

    def test_non_log_md_in_task_dir_allowed(self):
        """任务目录下非日志 md（实施计划/评审报告）→ 放行。"""
        for name in ("实施计划.md", "评审报告.md", "任务书说明.md"):
            self.assertFalse(gate.is_log_file_write(str(self.task / name)))

    def test_outside_task_dir_log_allowed(self):
        """任务目录之外的普通「日志」文件名 → 不误伤（如 docs 下的日志文档）。"""
        p = str(self.root / "docs" / "运行日志说明.md")
        self.assertFalse(gate.is_log_file_write(p))


class TestGateNotifyRules(unittest.TestCase):
    """通知外呼识别与唯一出口（D4）。"""

    def test_curl_direct_blocked(self):
        """curl 直发钉钉 webhook → 识别为通知外呼。"""
        cmd = 'curl -X POST "https://oapi.dingtalk.com/robot/send?access_token=xxx"'
        self.assertTrue(gate.is_notify_call(cmd))
        self.assertFalse(gate.is_allowed_notify(cmd))

    def test_requests_direct_blocked(self):
        """requests.post 直发钉钉 → 识别为通知外呼。"""
        cmd = "requests.post('https://oapi.dingtalk.com/robot/send', json={...})"
        self.assertTrue(gate.is_notify_call(cmd))
        self.assertFalse(gate.is_allowed_notify(cmd))

    def test_util_dingtalk_blocked(self):
        """直接调用 util_dingtalk.send_markdown → 拦截（须走唯一出口）。"""
        cmd = "python -c 'from utils import util_dingtalk; util_dingtalk.send_markdown(...)'"
        self.assertTrue(gate.is_notify_call(cmd))
        self.assertFalse(gate.is_allowed_notify(cmd))

    def test_unique_exit_allowed(self):
        """唯一出口 harness.core.notify / HARNESS_NOTIFY → 放行判定。"""
        cmd = "HARNESS_NOTIFY=1 python -m harness.core.notify --title x --text y"
        self.assertTrue(gate.is_notify_call(cmd))
        self.assertTrue(gate.is_allowed_notify(cmd))
        cmd2 = "python -m harness.core.notify --run-id 20260814任务Y"
        self.assertTrue(gate.is_allowed_notify(cmd2))


class TestGateDestructiveRules(unittest.TestCase):
    """数据销毁拦截（D4：任意位置匹配 + 备份放行）。"""

    def test_rm_rf_leading_blocked(self):
        """行首 rm -rf → 拦截。"""
        self.assertTrue(gate.is_destructive("rm -rf /tmp/a"))

    def test_rm_rf_mid_command_blocked(self):
        """拼接命令中间位置 rm -rf（旧版绕过）→ 拦截。"""
        self.assertTrue(gate.is_destructive("echo x && rm -rf /tmp/a"))

    def test_drop_delete_truncate_blocked(self):
        """DROP/DELETE FROM/TRUNCATE/drop_collection → 拦截。"""
        for cmd in (
            "taos -s 'DROP TABLE IF EXISTS t'",
            "mysql -e 'DELETE FROM users'",
            "taos -s 'TRUNCATE TABLE d_000001_sz'",
            "milvus.drop_collection('coll')",
        ):
            self.assertTrue(gate.is_destructive(cmd), cmd)

    def test_backup_declaration_allows(self):
        """显式 backup/备份 声明（真实备份动作，非注释/echo 文本）→ 放行。"""
        for cmd in (
            "rm -rf /tmp/a --backup",
            "cp -r /tmp/a /backup/a && rm -rf /tmp/a",
            "taos -s 'DROP TABLE IF EXISTS t' --backup",
            "cp -r /data /backup/data && DELETE FROM users WHERE id=1",
        ):
            self.assertTrue(gate.has_backup_declaration(cmd), cmd)
            self.assertFalse(
                gate.decide("", cmd, None, "", SECRET)["blocked"], cmd
            )

    def test_fake_backup_comment_blocked(self):
        """注释中的 backup 字样不再是备份声明（H2d 语义校验）→ 拦截。"""
        for cmd in (
            "rm -rf /tmp/a # 已备份 /backup/a",
            "DELETE FROM users WHERE id=1 # 备份完成",
            "rm -rf /data && echo backup",
            'echo "backup" && rm -rf /data',
        ):
            self.assertFalse(gate.has_backup_declaration(cmd), cmd)
            r = gate.decide("", cmd, None, "", SECRET)
            self.assertTrue(r["blocked"], cmd)
            self.assertEqual(r["code"], gate.RC_DATA_SAFETY, cmd)

    def test_grep_containing_ddl_is_blocked(self):
        """含 DDL 字样的命令按 fail-closed 口径拦截（固化决策，防绕过）。"""
        self.assertTrue(gate.is_destructive("grep -r 'DELETE FROM' /data/sql"))

    def test_safe_command_allowed(self):
        """普通命令 → 放行。"""
        for cmd in ("cat a.txt", "ls -la", "git status", "python -m unittest"):
            self.assertFalse(gate.is_destructive(cmd), cmd)


class TestGateDecide(unittest.TestCase):
    """统一判定入口集成场景（D3/D4）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.task = self.root / "opencode_schedule" / "20260814" / "20260814任务Z"
        self.task.mkdir(parents=True)
        self.run_id = "20260814任务Z"

    def tearDown(self):
        self._tmp.cleanup()

    def _open_gate(self):
        result = self.task / "unit_test" / "test" / "result.txt"
        result.parent.mkdir(parents=True)
        result.write_text("OK: 1 passed", encoding="utf-8")
        g = gate.build_gate_v2(
            run_id=self.run_id,
            task_dir=str(self.task),
            result_files=[result],
            total=1,
            passed=1,
            secret=SECRET,
        )
        (self.task / gate.GATE_FILENAME).write_text(
            json.dumps(g, ensure_ascii=False), encoding="utf-8"
        )

    def test_log_write_blocked_before_gate(self):
        """门禁未开：写研发日志 → 拦截。"""
        r = gate.decide(str(self.task / "任务1研发日志.md"), "", self.task, self.run_id, SECRET)
        self.assertTrue(r["blocked"])
        self.assertEqual(r["code"], gate.RC_LOG_BLOCKED)
        self.assertEqual(r["event_type"], "gate_block")

    def test_status_file_writable_before_gate(self):
        """门禁未开：写研发流程状态.md（D3 审计记录）→ 放行。"""
        r = gate.decide(str(self.task / "研发流程状态.md"), "", self.task, self.run_id, SECRET)
        self.assertFalse(r["blocked"])
        self.assertEqual(r["code"], gate.RC_OK)

    def test_log_write_allowed_after_gate(self):
        """门禁开启：写研发日志 → 放行。"""
        self._open_gate()
        r = gate.decide(str(self.task / "任务1研发日志.md"), "", self.task, self.run_id, SECRET)
        self.assertFalse(r["blocked"])

    def test_direct_notify_blocked_even_with_gate(self):
        """门禁开启但绕过唯一出口：curl 直发钉钉 → 拦截（D4）。"""
        self._open_gate()
        cmd = 'curl "https://oapi.dingtalk.com/robot/send?access_token=x"'
        r = gate.decide("", cmd, self.task, self.run_id, SECRET)
        self.assertTrue(r["blocked"])
        self.assertEqual(r["code"], gate.RC_NOTIFY_BLOCKED)

    def test_unique_exit_notify_requires_gate(self):
        """唯一出口通知：门禁未开 → 拦截；开闸 → 放行。"""
        cmd = "HARNESS_NOTIFY=1 python -m harness.core.notify --title t --text x"
        r = gate.decide("", cmd, self.task, self.run_id, SECRET)
        self.assertTrue(r["blocked"])
        self.assertEqual(r["code"], gate.RC_NOTIFY_BLOCKED)
        self._open_gate()
        r = gate.decide("", cmd, self.task, self.run_id, SECRET)
        self.assertFalse(r["blocked"])

    def test_read_operations_never_blocked(self):
        """读取操作不误伤（门禁关闭时 cat/grep 放行）。"""
        for cmd in ("cat 任务1研发日志.md", "grep 测试 unit_test/test/a.txt"):
            r = gate.decide("", cmd, self.task, self.run_id, SECRET)
            self.assertFalse(r["blocked"], cmd)


class TestGateBypassVariants(unittest.TestCase):
    """绕过面收窄（20260815任务1 · H2）：rm 变体/销毁类命令/URL 混淆全拦。"""

    def test_rm_variants_all_blocked(self):
        """rm 递归删除变体 5 种全拦（H2a）。"""
        for cmd in (
            "rm -fr /tmp/a",
            "rm -r -f /tmp/a",
            "rm --recursive --force /tmp/a",
            "/bin/rm -rf /tmp/a",
            "\\rm -rf /tmp/a",
            "rm -rf /tmp/a",
        ):
            self.assertTrue(gate.is_destructive(cmd), cmd)
            self.assertTrue(
                gate.decide("", cmd, None, "", SECRET)["blocked"], cmd
            )

    def test_shred_unlink_rmdir_trash_blocked(self):
        """销毁类命令（shred/unlink/rmdir -r/mv 回收站）全拦（H2b）。"""
        for cmd in (
            "shred -u /tmp/a",
            "unlink /tmp/a",
            "rmdir -r /tmp/a",
            "rmdir -rv /tmp/a",
            "mv /tmp/a ~/.local/share/Trash/",
            "mv /tmp/a /data/回收站/",
        ):
            self.assertTrue(gate.is_destructive(cmd), cmd)
            self.assertTrue(
                gate.decide("", cmd, None, "", SECRET)["blocked"], cmd
            )

    def test_url_char_class_obfuscation_blocked(self):
        """URL 字符类点混淆 oapi[.]dingtalk[.]com → 识别为通知外呼（H2c）。"""
        for cmd in (
            "curl 'https://oapi[.]dingtalk[.]com/robot/send?access_token=x'",
            "requests.post('https://oapi[.]dingtalk[.]com/robot/send')",
        ):
            self.assertTrue(gate.is_notify_call(cmd), cmd)
            self.assertFalse(gate.is_allowed_notify(cmd), cmd)

    def test_url_string_concat_obfuscation_blocked(self):
        """变量拼接混淆 "oapi."+"dingtalk.com" → 识别为通知外呼（H2c）。"""
        for cmd in (
            'url = "oapi."+"dingtalk.com" + "/robot/send"',
            'requests.post("https://oapi" + "." + "dingtalk.com/robot/send")',
            "curl https://oapi[.]dingtalk[.]com/robot/send",
        ):
            self.assertTrue(gate.is_notify_call(cmd), cmd)
            self.assertFalse(gate.is_allowed_notify(cmd), cmd)

    def test_destructive_in_echo_text_still_blocked(self):
        """把 rm 写进 echo 文本 → 销毁判定仍用原始 cmd 命中（H2d 防绕过）。"""
        cmd = 'echo "rm -rf /data" && echo ok'
        self.assertTrue(gate.is_destructive(cmd), cmd)
        r = gate.decide("", cmd, None, "", SECRET)
        self.assertTrue(r["blocked"], cmd)
        self.assertEqual(r["code"], gate.RC_DATA_SAFETY, cmd)


class TestGateLogAllowlist(unittest.TestCase):
    """日志误伤消除（20260815任务1 · H8）：放行名单不误伤、日志仍拦。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.task = self.root / "opencode_schedule" / "20260815" / "20260815任务Y"
        self.task.mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def test_data_log_doc_not_blocked(self):
        """配置放行名单后「数据日志说明.md」（正常文档）不误伤（H8）。"""
        p = str(self.task / "数据日志说明.md")
        self.assertFalse(gate.is_log_file_write(p))

    def test_research_log_still_blocked(self):
        """「研发日志*.md」仍拦（放行名单只放行精确文件名）。"""
        for name in ("研发日志.md", "任务1研发日志.md", "研发日志20260815.md"):
            self.assertTrue(gate.is_log_file_write(str(self.task / name)), name)

    def test_status_file_still_allowed(self):
        """「研发流程状态.md」仍放行（审计记录，D3）。"""
        p = str(self.task / "研发流程状态.md")
        self.assertFalse(gate.is_log_file_write(p))

    def test_outside_task_dir_log_doc_allowed(self):
        """任务目录之外的「日志」文档不误伤（非任务目录模式）。"""
        p = str(self.root / "docs" / "数据日志说明.md")
        self.assertFalse(gate.is_log_file_write(p))


class TestCliDecide(unittest.TestCase):
    """decide CLI 契约测试（20260815 任务2 新增：旧插件 tool.execute.before 委托路径）。

    子进程调用风格沿用 test_gate_concurrency.py：sys.executable -m harness.core.cli，
    cwd=宿主根（harness 包导入），覆盖旧插件全部调用路径的入参出参契约。
    """

    HOST_ROOT = str(Path(__file__).resolve().parent.parent)

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.task = self.root / "opencode_schedule" / "20260815" / "20260815任务D"
        self.task.mkdir(parents=True)
        self.run_id = "20260815任务D"
        self.secret_file = self.root / "secret"
        self.secret_file.write_text(SECRET, encoding="utf-8")
        os.chmod(self.secret_file, 0o600)
        self.log_file = str(self.task / "任务1研发日志.md")

    def tearDown(self):
        self._tmp.cleanup()

    def _decide(self, task_dir, run_id, file_path="", cmd="", secret_file=None):
        """以子进程执行 decide（模拟旧插件 execFileSync 调用）。"""
        return subprocess.run(
            [
                sys.executable, "-m", "harness.core.cli", "decide",
                "--task-dir", str(task_dir),
                "--run-id", run_id,
                "--file", file_path,
                "--cmd", cmd,
                "--secret-file", str(secret_file or self.secret_file),
                "--json",
            ],
            cwd=self.HOST_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
        )

    def _seal_v2(self):
        """在任务目录落合法 v2 闸（编排器侧签名，写/验分离）。"""
        result = self.task / "unit_test" / "test" / "result.txt"
        result.parent.mkdir(parents=True)
        result.write_text("测试总数: 1\n成功: 1\n失败: 0\n错误: 0\n", encoding="utf-8")
        g = gate.build_gate_v2(
            run_id=self.run_id,
            task_dir=str(self.task),
            result_files=[result],
            total=1,
            passed=1,
            secret=SECRET,
        )
        (self.task / gate.GATE_FILENAME).write_text(
            json.dumps(g, ensure_ascii=False), encoding="utf-8"
        )

    def test_gate_missing_blocked_four_fields(self):
        """正常案例（未落闸）：写研发日志 → stdout 纯 JSON 四字段齐全、blocked=true、退出码 1。"""
        p = self._decide(self.task, self.run_id, file_path=self.log_file)
        data = json.loads(p.stdout.strip())
        for key in ("blocked", "code", "reason", "event_type"):
            self.assertIn(key, data)
        self.assertTrue(data["blocked"])
        self.assertEqual(data["code"], gate.RC_LOG_BLOCKED)
        self.assertIn(gate.RC_GATE_MISSING, data["reason"])
        self.assertEqual(p.returncode, 1)

    def test_gate_open_allowed_exit_zero(self):
        """正常案例（已落闸）：合法 v2 闸 + 写研发日志 → blocked=false、退出码 0。"""
        self._seal_v2()
        p = self._decide(self.task, self.run_id, file_path=self.log_file)
        data = json.loads(p.stdout.strip())
        self.assertFalse(data["blocked"])
        self.assertEqual(data["code"], gate.RC_OK)
        self.assertEqual(p.returncode, 0)

    def test_curl_direct_blocked(self):
        """反案例：curl 直发钉钉（无 HARNESS_NOTIFY 出口标记）→ 拦截（D4）。"""
        cmd = 'curl -s "https://oapi.dingtalk.com/robot/send?access_token=xxx"'
        p = self._decide(self.task, self.run_id, cmd=cmd)
        data = json.loads(p.stdout.strip())
        self.assertTrue(data["blocked"])
        self.assertEqual(data["code"], gate.RC_NOTIFY_BLOCKED)
        self.assertEqual(p.returncode, 1)

    def test_forged_gate_token_invalid(self):
        """反案例：伪造 .gate.json（token 被篡改）→ 不开闸（D2）。"""
        self._seal_v2()
        on_disk = json.loads((self.task / gate.GATE_FILENAME).read_text(encoding="utf-8"))
        on_disk["gate_token"] = "forged-token"
        (self.task / gate.GATE_FILENAME).write_text(
            json.dumps(on_disk, ensure_ascii=False), encoding="utf-8"
        )
        p = self._decide(self.task, self.run_id, file_path=self.log_file)
        data = json.loads(p.stdout.strip())
        self.assertTrue(data["blocked"])
        self.assertEqual(data["code"], gate.RC_LOG_BLOCKED)
        self.assertIn(gate.RC_GATE_TOKEN_INVALID, data["reason"])

    def test_run_id_mismatch_blocked(self):
        """反案例：合法闸 + run-id 与任务目录不一致 → 拦截（D1）。"""
        self._seal_v2()
        p = self._decide(self.task, "20260815任务E", file_path=self.log_file)
        data = json.loads(p.stdout.strip())
        self.assertTrue(data["blocked"])
        self.assertEqual(data["code"], gate.RC_LOG_BLOCKED)
        self.assertIn(gate.RC_GATE_RUN_ID_MISMATCH, data["reason"])


if __name__ == "__main__":
    unittest.main()
