# -*- coding: utf-8 -*-
"""
test_cc_command.py - opencode 入口命令更名（/dev → /cc）正确性单元测试

覆盖范围（正常 / 反案例 / 边界三大类）：
    1. 正常案例：宿主 cc.md 存在且内容含 cc 含义与 /cc 三模式用法；
                 4 业务项目经目录软链同步内容与宿主一致；dev.md 已消失；
                 constitution L128 已更新；README/快速上手指南含义说明到位
    2. 反案例：配置域 5 文件、文档域（宪法/docs/README 双版/quick_start/快速上手指南）
               grep 命令引用零命中（白名单放行：修订记录行、设备路径）
    3. 边界条件：检测函数能识别「/dev <」「commands/dev.md」「/dev`」「（/dev」模式
                 （自检测试器有效性），且不误伤清洁文本

宿主根定位：ROOT = 本文件上两级（unit_test/test_cc_command.py → unit_test/ → 宿主根）；
业务项目路径由 ROOT 上一级（WORKSPACE_DIR）+ 项目名拼出（hetu-aether 等 4 项目）。

测试结果落盘：unit_test/test/test_cc_command_result.txt（沿用 test_harness_topology.py
的 run_tests 输出模式：用例逐条 + 汇总 + 失败/错误明细）。
"""

import io
import os
import re
import tempfile
import unittest

# ---------------------------------------------------------------------------
# 常量与检测辅助（模块级，供各用例复用）
# ---------------------------------------------------------------------------

# 宿主根：本文件上两级（unit_test/test_cc_command.py → unit_test/ → 宿主根）
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 工作区父目录：宿主根上一级
WORKSPACE_DIR = os.path.dirname(ROOT)
# 4 个业务项目（.opencode/commands 为目录级软链指向宿主 commands）
BUSINESS_PROJECTS = ("hetu-aether", "hetu-mercury", "hetu-sybil", "hetu-thoth")

# 命令引用检测模式（统一模式，禁止裸 /dev 全局匹配——会误伤 /dev/urandom 等设备路径）
DEV_REF_PATTERNS = (
    "/dev <",       # 命令调用形态（/dev <任务书>）
    "commands/dev.md",  # 命令文件路径引用
    "/dev`",        # 反引号包裹的命令名形态
    "（/dev",       # 括号内命令名形态（（/dev，本文件）
)

# 白名单：修订记录行（历史事实，保留原文；文件名 -> 行号集合）
REVISION_WHITELIST = {
    "docs/hetu-sybil/架构与模块设计.md": {732},
    "docs/hetu-sybil/研发计划.md": {661},
}

# 文档域文件清单（相对 ROOT）
DOCS_DOMAIN_FILES = (
    "constitution/constitution.md",
    "docs/harness/agents-skills.md",
    "docs/harness/assets.md",
    "docs/harness/extend.md",
    "docs/harness/gates.md",
    "docs/harness/README.md",
    "docs/harness/topology.md",
    "docs/harness/workflow.md",
    "docs/hetu-hammurabi/dsh-migration.md",
    "docs/hetu-hammurabi/hard-gate-optimize.md",
    "docs/hetu-sybil/架构与模块设计.md",
    "docs/hetu-sybil/研发计划.md",
    "README.md",
    "README.en.md",
    "quick_start.md",
    "快速上手指南.md",
)

# 配置域文件清单（相对 ROOT）
CONFIG_DOMAIN_FILES = (
    ".opencode/agents/charter-orchestrator.md",
    "harness/agents/charter-orchestrator.md",
    ".opencode/plugin/charter-gate.ts",
    "scripts/install_harness.sh",
    "scripts/run_charter.sh",
)


def has_dev_ref(text: str) -> bool:
    """判断文本是否含遗留 /dev 命令引用（任一检测模式命中即 True）"""
    return any(p in text for p in DEV_REF_PATTERNS)


def read_text(rel_path: str) -> str:
    """读取 ROOT 下相对路径文件文本（文件缺失时抛 FileNotFoundError 由用例断言）"""
    with open(os.path.join(ROOT, rel_path), "r", encoding="utf-8") as f:
        return f.read()


def scan_dev_ref(rel_path: str, whitelist: set) -> list:
    """扫描单文件命令引用，返回命中行号列表（白名单行号放行）

    参数:
        rel_path: 相对 ROOT 的文件路径
        whitelist: 白名单行号集合（1 起始），命中行跳过不报
    返回:
        命中行号列表（0 = 无命中）
    """
    hits = []
    with open(os.path.join(ROOT, rel_path), "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            if lineno in whitelist:
                continue
            if has_dev_ref(line):
                hits.append(lineno)
    return hits


class TestHostCcExistsAndContent(unittest.TestCase):
    """正常案例：宿主 cc.md 存在、含 cc 含义与 /cc 三模式用法、无 /dev 残留"""

    def test_host_cc_exists_and_content(self):
        """正常案例：cc.md 存在；含 constitution coding 含义；含 /cc 用法（$ARGUMENTS 三模式）；无遗留 /dev 引用"""
        cc_path = os.path.join(ROOT, ".opencode", "commands", "cc.md")
        self.assertTrue(
            os.path.isfile(cc_path), f"宿主 .opencode/commands/cc.md 应存在: {cc_path}"
        )
        content = read_text(".opencode/commands/cc.md")
        # 含义说明（验收 4）
        self.assertIn("constitution coding", content, "cc.md 应含 cc = constitution coding 含义说明")
        # /cc 用法：$ARGUMENTS 三模式判别
        self.assertIn("/cc", content, "cc.md 正文应含 /cc 命令名")
        self.assertIn("$ARGUMENTS", content, "cc.md 应含 $ARGUMENTS 用法说明")
        self.assertIn("输入判别（三种模式）", content, "cc.md 应保留三模式判别结构")
        for keyword in ("任务书路径", "一句话需求", "空输入"):
            self.assertIn(keyword, content, f"cc.md 三模式判别应含「{keyword}」")
        # 无遗留 /dev 命令引用（逐行检查）
        for lineno, line in enumerate(content.splitlines(), start=1):
            self.assertFalse(
                has_dev_ref(line),
                f"cc.md L{lineno} 含遗留 /dev 命令引用: {line.strip()}",
            )


class TestBusinessProjectsCcConsistent(unittest.TestCase):
    """正常案例：4 业务项目经目录软链同步，cc.md 内容与宿主完全一致"""

    def test_business_projects_cc_consistent(self):
        """正常案例：4 项目 .opencode/commands/cc.md 内容与宿主完全一致（软链同步）"""
        host_content = read_text(".opencode/commands/cc.md")
        for proj in BUSINESS_PROJECTS:
            proj_cc = os.path.join(
                WORKSPACE_DIR, proj, ".opencode", "commands", "cc.md"
            )
            self.assertTrue(
                os.path.isfile(proj_cc), f"{proj} 路径下 cc.md 应存在（软链同步）: {proj_cc}"
            )
            with open(proj_cc, "r", encoding="utf-8") as f:
                self.assertEqual(
                    f.read(),
                    host_content,
                    f"{proj}/.opencode/commands/cc.md 内容应与宿主完全一致",
                )


class TestDevMdRemoved(unittest.TestCase):
    """正常案例：宿主与 4 业务项目路径下 dev.md 均不存在"""

    def test_dev_md_removed(self):
        """正常案例：5 路径下 .opencode/commands/dev.md 均不存在"""
        paths = [ROOT] + [os.path.join(WORKSPACE_DIR, p) for p in BUSINESS_PROJECTS]
        for base in paths:
            dev_path = os.path.join(base, ".opencode", "commands", "dev.md")
            self.assertFalse(
                os.path.exists(dev_path),
                f"{dev_path} 应不存在（更名后 dev.md 已移除）",
            )


class TestNoDevRefInConfigDomain(unittest.TestCase):
    """反案例：配置域 5 文件命令引用零命中"""

    def test_no_dev_ref_in_config_domain(self):
        """反案例：配置域文件 grep「/dev <」「/dev`」「（/dev」零命中（>/dev/null 设备语义不在断言范围）"""
        for rel in CONFIG_DOMAIN_FILES:
            hits = scan_dev_ref(rel, whitelist=set())
            self.assertEqual(
                hits, [], f"配置域 {rel} 不应含 /dev 命令引用，命中行: {hits}"
            )


class TestNoDevRefInDocsDomain(unittest.TestCase):
    """反案例：文档域命令引用零命中（白名单放行修订记录与设备路径）"""

    def test_no_dev_ref_in_docs_domain(self):
        """反案例：文档域 grep 零命中；白名单放行：架构 L732、研发计划 L661、设备路径行"""
        for rel in DOCS_DOMAIN_FILES:
            whitelist = REVISION_WHITELIST.get(rel, set())
            hits = scan_dev_ref(rel, whitelist=whitelist)
            self.assertEqual(
                hits,
                [],
                f"文档域 {rel} 不应含 /dev 命令引用（白名单放行 {sorted(whitelist)}），命中行: {hits}",
            )


class TestConstitutionUpdated(unittest.TestCase):
    """正常案例：constitution.md L128 已更新为 /cc 且含 cc 含义，其余行无命令引用变更"""

    def test_constitution_updated(self):
        """正常案例：L128 含「/cc <任务书路径」与 constitution coding；全文无 /dev 残留；其余行无命令引用"""
        lines = read_text("constitution/constitution.md").splitlines()
        self.assertGreaterEqual(len(lines), 128, "constitution.md 应有至少 128 行")
        l128 = lines[127]
        self.assertIn("/cc <任务书路径>", l128, "constitution.md L128 应含 /cc <任务书路径>")
        self.assertIn("constitution coding", l128, "constitution.md L128 应含 cc = constitution coding 含义说明")
        self.assertNotIn("/dev <任务书路径", l128, "constitution.md L128 不应含 /dev <任务书路径")
        # 其余行（除 L128 外）无 /dev / /cc 命令引用
        for lineno, line in enumerate(lines, start=1):
            if lineno == 128:
                continue
            self.assertFalse(
                has_dev_ref(line),
                f"constitution.md L{lineno} 含 /dev 命令引用: {line.strip()}",
            )
            self.assertNotIn(
                "/cc", line, f"constitution.md L{lineno} 除 L128 外不应含 /cc 命令引用"
            )


class TestCcUsageDocumented(unittest.TestCase):
    """正常案例：README.md / 快速上手指南.md 含 /cc 引用与 cc = constitution coding 含义说明"""

    def test_cc_usage_documented(self):
        """正常案例：README.md、快速上手指南.md 含 /cc 引用与「constitution coding」含义说明"""
        for rel in ("README.md", "快速上手指南.md"):
            content = read_text(rel)
            self.assertIn("/cc", content, f"{rel} 应含 /cc 命令引用")
            self.assertIn(
                "constitution coding",
                content,
                f"{rel} 应含 cc = constitution coding 含义说明（验收 4）",
            )


class TestDetectorPositive(unittest.TestCase):
    """边界条件：检测函数能识别各类 /dev 命令引用模式（自检测试器有效性）"""

    def test_detector_positive(self):
        """边界条件：构造含「/dev <」「commands/dev.md」「/dev`」「（/dev」的模拟文件，检测函数能识别"""
        with tempfile.TemporaryDirectory(prefix="cc_detect_") as tmp:
            mock_file = os.path.join(tmp, "mock.md")
            with open(mock_file, "w", encoding="utf-8") as f:
                f.write("使用 /dev <任务书路径> 触发\n")
                f.write("引用 .opencode/commands/dev.md 文件\n")
                f.write("验证 `/dev` 命令可用\n")
                f.write("opencode 入口（/dev，本文件）\n")
            with open(mock_file, "r", encoding="utf-8") as f:
                for lineno, line in enumerate(f, start=1):
                    self.assertTrue(
                        has_dev_ref(line),
                        f"检测函数应识别模拟文件 L{lineno} 的命令引用: {line.strip()}",
                    )
            # 清洁文本不误报（设备路径/修订记录语境）
            clean_lines = (
                ">/dev/null 2>&1",
                "head -c 64 /dev/urandom",
                "与 /dev 一任务一流水线同构（2026-08-12 历史修订记录）",
                "dsh --profile hetu-hammurabi <任务书|一句话需求>",
            )
            for line in clean_lines:
                self.assertFalse(
                    has_dev_ref(line), f"检测函数不应误伤清洁文本: {line}"
                )


class TestDshPluginCommandNameLowercase(unittest.TestCase):
    """正常案例：DSH 命令插件 charter-command.ts 命令名小写 cc 且匹配 DSH 校验正则"""

    DSH_COMMAND_PLUGIN = "harness/dsh/plugins/charter-command.ts"

    def test_plugin_command_name_lowercase(self):
        """正常案例：命令名定义为小写 cc 且匹配 /^[a-z][a-z0-9_-]*$/u，无大写 CC 命令名形态（20260815 任务4）"""
        content = read_text(self.DSH_COMMAND_PLUGIN)
        # 定义处与注册处均为小写 cc
        self.assertIn(
            'const name = "cc";',
            content,
            'charter-command.ts 应含 const name = "cc";（命令名小写定义）',
        )
        self.assertIn(
            'name: "cc",',
            content,
            'charter-command.ts 注册处应含 name: "cc",',
        )
        # 提取命令名常量并校验 DSH 校验正则（Python 侧等价 /^[a-z][a-z0-9_-]*$/u）
        m = re.search(r'const name = "([a-z][a-z0-9_-]*)";', content)
        self.assertIsNotNone(m, "应能提取命令名常量定义")
        self.assertEqual(m.group(1), "cc", "命令名常量应恰为 cc")
        self.assertIsNotNone(
            re.fullmatch(r"[a-z][a-z0-9_-]*", m.group(1)),
            "命令名应匹配 DSH 命令名校验正则 /^[a-z][a-z0-9_-]*$/u",
        )
        # 反案例：大写 CC 命令名形态不存在
        self.assertNotIn(
            'name = "CC"', content, '不应存在 name = "CC" 大写命令名形态'
        )
        self.assertNotIn(
            'name: "CC"', content, '不应存在 name: "CC" 大写命令名形态'
        )


class TestNoCcRefInDshAndDocsDomain(unittest.TestCase):
    """反案例：harness/dsh/ 与 docs/ 域大写 /CC 命令引用零命中（白名单=空集，20260815 任务4）"""

    DSH_CC_DOMAIN_FILES = (
        "harness/dsh/plugins/charter-command.ts",
        "harness/dsh/hetu-dashboard/client.js",
        "harness/dsh/hetu-dashboard/test/command.test.mjs",
        "docs/hetu-hammurabi/dsh-migration.md",
    )

    CC_REF_PATTERNS = ("/CC", '"CC"', "命令名：CC")

    def test_no_cc_ref_in_dsh_and_docs_domain(self):
        """反案例：4 文件扫描「/CC」「"CC"」「命令名：CC」零命中（本次无历史修订记录行，白名单为空集）"""
        for rel in self.DSH_CC_DOMAIN_FILES:
            hits = []
            with open(os.path.join(ROOT, rel), "r", encoding="utf-8") as f:
                for lineno, line in enumerate(f, start=1):
                    if any(p in line for p in self.CC_REF_PATTERNS):
                        hits.append(lineno)
            self.assertEqual(
                hits,
                [],
                f"{rel} 不应含大写 /CC 命令引用（白名单=空集），命中行: {hits}",
            )


def run_tests():
    """执行所有测试并输出结果（unit_test.md「八、测试结果输出」模式）"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for case_cls in (
        TestHostCcExistsAndContent,
        TestBusinessProjectsCcConsistent,
        TestDevMdRemoved,
        TestNoDevRefInConfigDomain,
        TestNoDevRefInDocsDomain,
        TestConstitutionUpdated,
        TestCcUsageDocumented,
        TestDetectorPositive,
        TestDshPluginCommandNameLowercase,
        TestNoCcRefInDshAndDocsDomain,
    ):
        suite.addTests(loader.loadTestsFromTestCase(case_cls))

    runner = unittest.TextTestRunner(stream=io.StringIO(), verbosity=2)
    result = runner.run(suite)
    stream_text = runner.stream.getvalue()

    # 确保输出目录存在
    test_result_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test")
    os.makedirs(test_result_dir, exist_ok=True)

    # 写入结果文件（逐行用例结果 + 汇总，与 test_harness_topology_result.txt 同构）
    result_file = os.path.join(test_result_dir, "test_cc_command_result.txt")
    with open(result_file, "w", encoding="utf-8") as f:
        f.write(stream_text)
        f.write("\n")
        f.write("=" * 60 + "\n")
        f.write("cc 命令更名（/dev → /cc）单元测试结果\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"测试总数: {result.testsRun}\n")
        f.write(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}\n")
        f.write(f"失败: {len(result.failures)}\n")
        f.write(f"错误: {len(result.errors)}\n\n")

        if result.failures:
            f.write("-" * 40 + "\n失败用例:\n" + "-" * 40 + "\n")
            for test, traceback in result.failures:
                f.write(f"\n{test}:\n{traceback}\n")

        if result.errors:
            f.write("-" * 40 + "\n错误用例:\n" + "-" * 40 + "\n")
            for test, traceback in result.errors:
                f.write(f"\n{test}:\n{traceback}\n")

        f.write("\n" + "=" * 60 + "\n")
        if result.wasSuccessful():
            f.write("测试结果: 全部通过\n")
        else:
            f.write("测试结果: 存在失败/错误\n")
        f.write("=" * 60 + "\n")

    print(f"\n测试结果已保存至: {result_file}")
    return result


if __name__ == "__main__":
    run_tests()
