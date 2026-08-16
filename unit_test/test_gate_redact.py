# -*- coding: utf-8 -*-
"""H5 脱敏回归测试：redact_secrets 明文凭据扫描与替换

覆盖：
- sk-<16+ 位> 密钥脱敏
- Bearer <token> 脱敏
- password=xxx / api_key: xxx / secret / token 等键值对脱敏（≥4 类）
- 正常文本零误伤（URL/中文/普通句子）
- 多命中计数
- 自定义 patterns 覆盖默认
- yaml 配置 secret_patterns 生效（REVISE 第1轮修复：接线 gate_rules.yaml）
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

from harness.core import gate, redact


class TestRedactSecrets(unittest.TestCase):
    """脱敏纯函数（正常/反例/边界）。"""

    def test_sk_key_redacted(self):
        """正常案例：sk-<16+ 位字母数字> 密钥 → 替换为 [REDACTED]。"""
        text = "api_key=sk-abcdefghijklmnopqrstuvwxyz123456"
        out, hits = redact.redact_secrets(text)
        self.assertNotIn("sk-abcdefghijklmnopqrstuvwxyz123456", out)
        self.assertIn(redact.REDACTED, out)
        # 同一串同时命中 sk- 模式与 api_key 键值对模式（旧版累计语义）
        self.assertEqual(hits, 2)

    def test_bearer_token_redacted(self):
        """正常案例：Bearer <token> → 替换为 [REDACTED]。"""
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.abc.def"
        out, hits = redact.redact_secrets(text)
        self.assertNotIn("eyJhbGciOiJIUzI1NiJ9.abc.def", out)
        self.assertIn(redact.REDACTED, out)
        self.assertEqual(hits, 1)

    def test_password_kv_redacted(self):
        """正常案例：password=xxx / passwd / pwd → 脱敏（忽略大小写）。"""
        for sample in (
            "password=SuperSecret123",
            "PASSWORD: SuperSecret123",
            "passwd = SuperSecret123",
            "pwd='SuperSecret123'",
        ):
            out, hits = redact.redact_secrets(sample)
            self.assertNotIn("SuperSecret123", out)
            self.assertIn(redact.REDACTED, out)
            self.assertEqual(hits, 1, sample)

    def test_secret_token_key_redacted(self):
        """正常案例：secret / token / api_key / access_key / access_token → 脱敏。"""
        for sample in (
            "client_secret=abcdefgh12345678",
            "token: abcdefgh12345678",
            "api_key=abcdefgh12345678",
            "api-key=abcdefgh12345678",
            "access_key = abcdefgh12345678",
            "access_token=abcdefgh12345678",
        ):
            out, hits = redact.redact_secrets(sample)
            self.assertNotIn("abcdefgh12345678", out)
            self.assertIn(redact.REDACTED, out)
            self.assertEqual(hits, 1, sample)

    def test_multi_hits_counted(self):
        """边界：多条凭据 → hits 为全部命中之和。"""
        text = "sk-abcdefghijklmnopqrstuvwxyz123456 and Bearer tok12345 and password=Secret12345"
        out, hits = redact.redact_secrets(text)
        self.assertEqual(hits, 3)

    def test_normal_text_zero_hit(self):
        """反案例：正常文本零误伤（URL/中文/普通句子/短词）。"""
        for text in (
            "https://oapi.dingtalk.com/robot/send?access_token=1",
            "今日完成了测试与评审，全量 110/110 通过。",
            "echo hello world",
            "rm -rf /tmp/a --backup",
        ):
            out, hits = redact.redact_secrets(text)
            self.assertEqual(hits, 0, text)
            self.assertEqual(out, text)

    def test_custom_patterns_override_default(self):
        """边界：自定义 patterns 覆盖默认（仅脱敏自定义模式）。"""
        custom = redact.compile_patterns([r"SECRET\d+"])
        text = "SECRET12345 and sk-abcdefghijklmnopqrstuvwxyz123456"
        out, hits = redact.redact_secrets(text, custom)
        self.assertNotIn("SECRET12345", out)
        # 默认模式未启用 → sk- 密钥不脱敏
        self.assertIn("sk-abcdefghijklmnopqrstuvwxyz123456", out)
        self.assertEqual(hits, 1)

    def test_short_value_not_redacted(self):
        """边界：值 <8 位不脱敏（防误伤短文本）。"""
        text = "password=short"
        out, hits = redact.redact_secrets(text)
        self.assertEqual(hits, 0)
        self.assertEqual(out, text)


class TestRulesSecretPatterns(unittest.TestCase):
    """yaml 配置 secret_patterns 接线（REVISE 第1轮修复）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.rules_file = self.tmp / "gate_rules.yaml"
        self._saved_path = gate._default_rules_path
        self._saved_cache = gate._rules_cache

    def tearDown(self):
        gate._default_rules_path = self._saved_path
        gate._rules_cache = self._saved_cache
        self._tmp.cleanup()

    def _use_rules(self, data: dict):
        """写入规则文件并注入默认路径（等价 cli.cmd_redact 读取路径）。"""
        data.setdefault("schema_version", 1)
        self.rules_file.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
        gate._default_rules_path = self.rules_file
        gate.reset_rules_cache()

    def _full_rules(self) -> dict:
        """完整合法规则模板 + 自定义 secret_patterns。"""
        data = yaml.safe_load(open(Path(__file__).resolve().parent.parent / "harness" / "gate_rules.yaml", encoding="utf-8"))
        data["secret_patterns"] = [
            r"SKPROJ-[a-z0-9]{8,}",
            r"(?:client_secret|apikey)\s*[=:]\s*['\"]?[^\s'\"]{8,}",
        ]
        return data

    def test_rules_secret_patterns_effective(self):
        """正常案例：yaml 配置的 secret_patterns 生效（覆盖内置默认）。"""
        self._use_rules(self._full_rules())
        patterns = redact.compile_patterns(
            gate.get_effective_rules().get("secret_patterns") or []
        )
        # 自定义模式生效
        out, hits = redact.redact_secrets("key=SKPROJ-abcdef1234", patterns)
        self.assertIn(redact.REDACTED, out)
        self.assertEqual(hits, 1)
        # 内置默认 sk- 模式被覆盖（不再脱敏）
        out2, _ = redact.redact_secrets("sk-abcdefghijklmnopqrstuvwxyz123456", patterns)
        self.assertNotIn(redact.REDACTED, out2)

    def test_rules_kv_pattern_ignored_case(self):
        """正常案例：yaml 键值对类模式自动补 IGNORECASE（大写键名也脱敏）。"""
        self._use_rules(self._full_rules())
        patterns = redact.compile_patterns(
            gate.get_effective_rules().get("secret_patterns") or []
        )
        out, hits = redact.redact_secrets("CLIENT_SECRET=Abcdef1234", patterns)
        self.assertIn(redact.REDACTED, out)
        self.assertEqual(hits, 1)

    def test_rules_secret_patterns_absent_uses_default(self):
        """边界：yaml 无 secret_patterns 段 → 用内置默认（行为不变）。"""
        self._use_rules(self._full_rules())
        # 删掉 secret_patterns 后走默认路径（等价 cli cmd_redact else 分支）
        data = yaml.safe_load(open(self.rules_file, encoding="utf-8"))
        del data["secret_patterns"]
        self._use_rules(data)
        pattern_strings = gate.get_effective_rules().get("secret_patterns")
        self.assertIsNone(pattern_strings)
        out, hits = redact.redact_secrets("sk-abcdefghijklmnopqrstuvwxyz123456")
        self.assertIn(redact.REDACTED, out)
        self.assertEqual(hits, 1)


class TestCliRedact(unittest.TestCase):
    """redact CLI 契约测试（20260815 任务2 新增：旧插件 chat.message 委托路径）。

    子进程调用风格沿用 test_gate_concurrency.py（sys.executable -m harness.core.cli，
    cwd=宿主根），覆盖旧插件 redact 调用路径的出参契约与 --json 纯净输出。
    """

    HOST_ROOT = str(Path(__file__).resolve().parent.parent)

    def _redact(self, text):
        """以子进程执行 redact（模拟旧插件 execFileSync 调用）。"""
        return subprocess.run(
            [
                sys.executable, "-m", "harness.core.cli", "redact",
                "--text", text,
                "--json",
            ],
            cwd=self.HOST_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
        )

    def test_output_structure_and_redaction(self):
        """正常案例：sk-/Bearer/password 三类样本 → stdout 纯 JSON {text,hits}，
        hits≥1，原文凭据被替换为 [REDACTED]。"""
        text = (
            "key=sk-abcdefghijklmnopqrstuvwxyz123456 "
            "Bearer eyJhbGciOiJIUzI1NiJ9.abc.def "
            "password=SuperSecret123"
        )
        p = self._redact(text)
        data = json.loads(p.stdout.strip())
        self.assertIn("text", data)
        self.assertIn("hits", data)
        self.assertGreaterEqual(data["hits"], 3)
        for raw in (
            "sk-abcdefghijklmnopqrstuvwxyz123456",
            "eyJhbGciOiJIUzI1NiJ9.abc.def",
            "SuperSecret123",
        ):
            self.assertNotIn(raw, data["text"])
        self.assertIn(redact.REDACTED, data["text"])
        self.assertEqual(p.returncode, 0)

    def test_normal_text_zero_hit(self):
        """反案例：正常文本（URL/中文）→ hits=0，text 原样返回。"""
        text = "https://oapi.dingtalk.com/robot/send?access_token=1 今日全量 201/201 通过。"
        p = self._redact(text)
        data = json.loads(p.stdout.strip())
        self.assertEqual(data["hits"], 0)
        self.assertEqual(data["text"], text)

    def test_json_stdout_pure(self):
        """边界：--json 模式 stdout 仅一行 JSON（无 stderr 混杂）。"""
        p = self._redact("password=SuperSecret123")
        lines = p.stdout.strip().splitlines()
        self.assertEqual(len(lines), 1)
        data = json.loads(lines[0])
        self.assertGreaterEqual(data["hits"], 1)


if __name__ == "__main__":
    unittest.main()
