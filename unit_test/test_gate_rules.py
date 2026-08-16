# -*- coding: utf-8 -*-
"""H1 规则外置回归测试：gate_rules.yaml 加载/回退/重载/判定行为

覆盖：
- yaml 正常加载（schema 合法）
- rules 文件缺失 → 回退内置默认（fail-closed）
- 非法 yaml → 回退内置默认（fail-closed）
- schema 缺字段/类型错 → 拒绝（回退默认）
- 非法正则 → 拒绝（fail-closed）
- mtime 变更重载（改配置即变判定结果，不重启）
- 默认 rules 判定行为与内置默认一致（复现现状判定）
- 放行名单（H8）：配置 allowlist 后不误伤
"""

import os
import tempfile
import unittest
from pathlib import Path

import yaml

from harness.core import gate

# 合法规则样例：直接读取真实默认规则文件（同时守护「默认文件 schema 合法」）
_DEFAULT_RULES_FILE = (
    Path(__file__).resolve().parent.parent / "harness" / "gate_rules.yaml"
)


def _read_default_rules_yaml() -> str:
    """读取真实默认规则文件内容（合法 yaml 样例）。"""
    return _DEFAULT_RULES_FILE.read_text(encoding="utf-8")


class TestLoadRules(unittest.TestCase):
    """规则加载（正常/缺失/非法 fail-closed）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_load_valid_yaml(self):
        """正常案例：合法 yaml 正常加载，字段完整。"""
        f = self.tmp / "gate_rules.yaml"
        f.write_text(_read_default_rules_yaml(), encoding="utf-8")
        rules = gate.load_rules(f)
        self.assertEqual(rules["schema_version"], 1)
        self.assertEqual(rules["freshness_seconds"], 600)
        self.assertEqual(rules["log_file"]["main_pattern"], "研发日志")
        self.assertIn("数据日志说明.md", rules["log_file"]["allowlist"])
        self.assertIn("研发流程状态.md", rules["audit_files"])
        self.assertIn("rm_recursive", rules["dangerous_commands"])
        self.assertEqual(rules["backup"]["semantic"], "enforce")

    def test_missing_rules_file_fallback(self):
        """反案例：规则文件缺失 → 回退内置默认（fail-closed）。"""
        missing = self.tmp / "not_exist.yaml"
        rules = gate.load_rules(missing)
        self.assertIsNotNone(gate._rules_load_warning)
        self.assertEqual(rules["freshness_seconds"], 600)
        self.assertIn("rm_recursive", rules["dangerous_commands"])

    def test_invalid_yaml_fallback(self):
        """反案例：非法 yaml → 回退内置默认并告警（fail-closed）。"""
        f = self.tmp / "gate_rules.yaml"
        f.write_text("schema_version: [unclosed", encoding="utf-8")
        rules = gate.load_rules(f)
        self.assertIn("解析失败", gate._rules_load_warning)
        self.assertEqual(rules["freshness_seconds"], 600)

    def test_schema_missing_field_rejected(self):
        """反案例：schema 缺必需字段（dangerous_commands）→ 回退默认。"""
        f = self.tmp / "gate_rules.yaml"
        data = yaml.safe_load(_read_default_rules_yaml())
        del data["dangerous_commands"]
        f.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
        rules = gate.load_rules(f)
        self.assertIn("schema 非法", gate._rules_load_warning)
        self.assertEqual(rules["freshness_seconds"], 600)

    def test_schema_wrong_type_rejected(self):
        """反案例：schema 类型错（freshness_seconds 为字符串）→ 回退默认。"""
        f = self.tmp / "gate_rules.yaml"
        data = yaml.safe_load(_read_default_rules_yaml())
        data["freshness_seconds"] = "600"  # 类型错误
        f.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
        rules = gate.load_rules(f)
        self.assertIn("schema 非法", gate._rules_load_warning)
        self.assertEqual(rules["freshness_seconds"], 600)

    def test_invalid_regex_rejected(self):
        """反案例：非法正则 → 拒绝（fail-closed，防崩溃）。"""
        f = self.tmp / "gate_rules.yaml"
        data = yaml.safe_load(_read_default_rules_yaml())
        data["dangerous_commands"]["shred"] = "([unclosed"  # 非法正则
        f.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
        rules = gate.load_rules(f)
        self.assertIn("schema 非法", gate._rules_load_warning)
        self.assertEqual(rules["freshness_seconds"], 600)

    def test_root_not_mapping_rejected(self):
        """反案例：根节点非 mapping（list）→ 回退默认。"""
        f = self.tmp / "gate_rules.yaml"
        f.write_text("- a\n- b\n", encoding="utf-8")
        rules = gate.load_rules(f)
        self.assertIn("根节点", gate._rules_load_warning)
        self.assertEqual(rules["freshness_seconds"], 600)

    def test_backup_section_missing_rejected(self):
        """反案例（REVISE 修复）：缺 backup 段 → 回退默认，不抛 KeyError。"""
        f = self.tmp / "gate_rules.yaml"
        data = yaml.safe_load(_read_default_rules_yaml())
        del data["backup"]
        f.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
        # 不得逃逸 KeyError：必须回退内置默认并告警
        rules = gate.load_rules(f)
        self.assertIn("schema 非法", gate._rules_load_warning)
        self.assertIn("backup", gate._rules_load_warning)
        self.assertEqual(rules["freshness_seconds"], 600)
        # 判定链路不崩溃
        self.assertTrue(gate.is_destructive("rm -rf /tmp/a"))

    def test_backup_pattern_missing_rejected(self):
        """反案例（REVISE 修复）：缺 backup.pattern → 回退默认，不抛 KeyError。"""
        f = self.tmp / "gate_rules.yaml"
        data = yaml.safe_load(_read_default_rules_yaml())
        del data["backup"]["pattern"]
        f.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
        rules = gate.load_rules(f)
        self.assertIn("backup.pattern", gate._rules_load_warning)
        self.assertEqual(rules["freshness_seconds"], 600)
        self.assertFalse(gate.has_backup_declaration("rm -rf /tmp/a # 假声明"))


class TestRulesReload(unittest.TestCase):
    """mtime 变更重载：改配置即变判定结果（不重启）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.rules_file = self.tmp / "gate_rules.yaml"
        self._saved_path = gate._default_rules_path
        self._saved_cache = gate._rules_cache
        gate._rules_cache = None

    def tearDown(self):
        gate._default_rules_path = self._saved_path
        gate._rules_cache = self._saved_cache
        self._tmp.cleanup()

    def _use_rules(self, yaml_text: str):
        """写入规则文件并注入默认路径。"""
        self.rules_file.write_text(yaml_text, encoding="utf-8")
        gate._default_rules_path = self.rules_file
        gate.reset_rules_cache()

    def test_change_main_pattern_takes_effect(self):
        """正常案例：修改 main_pattern 后判定立即变化（mtime 重载）。"""
        self._use_rules(_read_default_rules_yaml())
        self.assertFalse(gate.is_log_file_write(str(self.tmp / "运行说明.md")))
        # 修改 ext_pattern 使任务目录外也拦截「说明」类？改用 main_pattern
        modified = yaml.safe_load(_read_default_rules_yaml())
        modified["log_file"]["main_pattern"] = "运行说明"
        self.rules_file.write_text(
            yaml.safe_dump(modified, allow_unicode=True), encoding="utf-8"
        )
        # mtime 变更（写入时间戳可能同秒，显式 touch 纳秒）
        gate.reset_rules_cache()  # 强制重载（与 mtime 缓存同语义）
        self.assertTrue(gate.is_log_file_write(str(self.tmp / "运行说明.md")))

    def test_change_freshness_takes_effect(self):
        """正常案例：修改 freshness_seconds 后 decide 生效新窗口。"""
        self._use_rules(_read_default_rules_yaml())
        # 无 .gate.json → 拦截（GATE_MISSING），与窗口无关；改窗口后行为不变
        rules = gate.get_effective_rules()
        self.assertEqual(rules["freshness_seconds"], 600)
        modified = yaml.safe_load(_read_default_rules_yaml())
        modified["freshness_seconds"] = 900
        self.rules_file.write_text(
            yaml.safe_dump(modified, allow_unicode=True), encoding="utf-8"
        )
        gate.reset_rules_cache()
        self.assertEqual(gate.get_effective_rules()["freshness_seconds"], 900)

    def test_real_mtime_reload_without_reset(self):
        """正常案例（REVISE 修复）：改文件 mtime 后不调 reset，get_effective_rules 直接重载。"""
        self._use_rules(_read_default_rules_yaml())
        self.assertEqual(gate.get_effective_rules()["freshness_seconds"], 600)
        # 改文件内容并显式刷新 mtime（真实重载路径，不调 reset_rules_cache）
        modified = yaml.safe_load(_read_default_rules_yaml())
        modified["freshness_seconds"] = 1200
        self.rules_file.write_text(
            yaml.safe_dump(modified, allow_unicode=True), encoding="utf-8"
        )
        os.utime(self.rules_file, None)  # 刷新 mtime 到当前（纳秒）
        self.assertEqual(gate.get_effective_rules()["freshness_seconds"], 1200)

    def test_corrupted_rules_fallback_default(self):
        """反案例：运行期规则文件被写坏 → 回退内置默认（判定不崩溃）。"""
        self._use_rules(_read_default_rules_yaml())
        self.rules_file.write_text("not: [valid", encoding="utf-8")
        gate.reset_rules_cache()
        self.assertEqual(gate.get_effective_rules()["freshness_seconds"], 600)
        # 判定仍可用（fail-closed 语义下 rm -rf 仍拦）
        self.assertTrue(gate.is_destructive("rm -rf /tmp/a"))


class TestDefaultRulesBehavior(unittest.TestCase):
    """默认 rules 判定行为与内置默认一致（复现现状）。"""

    def test_defaults_match_legacy_behavior(self):
        """正常案例：默认文件加载后的判定与内置默认一致（复现现状判定）。"""
        default = gate._build_default_rules()
        from_file = gate.load_rules()  # 真实默认文件
        # 非正则字段逐一相等
        self.assertEqual(from_file["schema_version"], default["schema_version"])
        self.assertEqual(from_file["freshness_seconds"], default["freshness_seconds"])
        self.assertEqual(from_file["log_file"]["main_pattern"], default["log_file"]["main_pattern"])
        self.assertEqual(from_file["log_file"]["ext_pattern"], default["log_file"]["ext_pattern"])
        self.assertEqual(from_file["log_file"]["allowlist"], default["log_file"]["allowlist"])
        self.assertEqual(from_file["audit_files"], default["audit_files"])
        self.assertEqual(from_file["backup"]["pattern"], default["backup"]["pattern"])
        self.assertEqual(from_file["backup"]["semantic"], default["backup"]["semantic"])
        # 正则字段存在（yaml 转义与 raw 字符串可能字面不同，比较编译后行为）
        self.assertEqual(
            list(from_file["dangerous_commands"].keys()),
            list(default["dangerous_commands"].keys()),
        )
        c_from_file = gate._compile_rules(from_file)
        c_default = gate._compile_rules(default)
        for sample in (
            "rm -rf /tmp/a", "rm -fr /tmp/a", "shred -u /tmp/a", "unlink /tmp/a",
            "DROP TABLE IF EXISTS t", "DELETE FROM users", "TRUNCATE TABLE t",
            "drop_collection('coll')",
        ):
            self.assertEqual(
                any(p.search(sample) for p in c_from_file["dangerous"]),
                any(p.search(sample) for p in c_default["dangerous"]),
                sample,
            )
        for sample in (
            "curl https://oapi.dingtalk.com/robot/send",
            "oapi[.]dingtalk[.]com",
            'url = "oapi."+"dingtalk.com"',
            "HARNESS_NOTIFY=1 python -m harness.core.notify",
        ):
            self.assertEqual(
                any(p.search(sample) for p in c_from_file["notify"]),
                any(p.search(sample) for p in c_default["notify"]),
                sample,
            )

    def test_destructive_legacy_samples(self):
        """正常案例：复现现状判定——rm -rf / DROP / DELETE / TRUNCATE 全拦。"""
        for cmd in (
            "rm -rf /tmp/a",
            "taos -s 'DROP TABLE IF EXISTS t'",
            "mysql -e 'DELETE FROM users'",
            "TRUNCATE TABLE t",
            "milvus.drop_collection('coll')",
        ):
            self.assertTrue(gate.is_destructive(cmd), cmd)

    def test_notify_legacy_samples(self):
        """正常案例：复现现状判定——oapi.dingtalk.com 直发被识别为通知。"""
        self.assertTrue(gate.is_notify_call("curl https://oapi.dingtalk.com/robot/send"))
        self.assertFalse(gate.is_allowed_notify("curl https://oapi.dingtalk.com/robot/send"))
        self.assertTrue(gate.is_allowed_notify("HARNESS_NOTIFY=1 python -m harness.core.notify"))

    def test_log_legacy_samples(self):
        """正常案例：复现现状判定——研发日志拦、研发流程状态.md 放行。"""
        self.assertTrue(gate.is_log_file_write("opencode_schedule/20260814/任务X/任务1研发日志.md"))
        self.assertFalse(gate.is_log_file_write("opencode_schedule/20260814/任务X/研发流程状态.md"))

    def test_allowlist_lets_data_log_through(self):
        """正常案例（H8）：配置 allowlist 后「数据日志说明.md」不再误伤。"""
        # 默认文件已预置 allowlist（E 阶段定稿）
        self.assertFalse(
            gate.is_log_file_write("opencode_schedule/20260815/任务1/数据日志说明.md")
        )
        # 「研发日志」变体仍拦
        self.assertTrue(
            gate.is_log_file_write("opencode_schedule/20260815/任务1/研发日志.md")
        )

    def test_allowlist_custom_reload(self):
        """边界：自定义 allowlist 清空后「数据日志说明.md」恢复拦截。"""
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        rules_file = self.tmp / "gate_rules.yaml"
        data = yaml.safe_load(_read_default_rules_yaml())
        data["log_file"]["allowlist"] = []
        rules_file.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
        saved = gate._default_rules_path
        gate._default_rules_path = rules_file
        gate.reset_rules_cache()
        try:
            self.assertTrue(
                gate.is_log_file_write("opencode_schedule/20260815/任务1/数据日志说明.md")
            )
        finally:
            gate._default_rules_path = saved
            gate.reset_rules_cache()
            self._tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
