# -*- coding: utf-8 -*-
"""
test_harness_topology.py - harness_topology 纯函数单元测试

覆盖范围（正常 / 反例 / 边界三大类）：
    1. 正常案例：宿主命中、目标项目发现（排除宿主）、extra 追加、aether/venv 解析、
                 .harness-env 生成与回读 roundtrip
    2. 反案例：缺 constitution/、缺 docs/资源地图.md、缺 .opencode/agents 时宿主判定抛错、
               extra 指定不存在项目被跳过、aether/venv 缺失返回 None
    3. 边界条件：多宿主取要件最完整者、空工作区无候选抛错、父目录含空格、
                 空行/注释/重复键/无等号行解析、hetu-* 前缀文件（非目录）跳过、
                 host_dir 异常输入不崩溃、aether/venv 缺失时生成空值+注释

测试隔离：使用 tempfile.mkdtemp() 构造临时拓扑，tearDown 清理；
         被测试模块不在 Python 路径中，使用 sys.path.insert 引入 scripts/。
"""

import os
import shutil
import sys
import tempfile
import unittest

# 引入被测试模块（scripts/harness_topology.py，位于宿主根同级）
sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"),
)
from harness_topology import (
    build_env_content,
    detect_host_dir,
    list_target_projects,
    parse_env_content,
    resolve_aether_dir,
    resolve_venv_bin,
)


class TestTopologyBase(unittest.TestCase):
    """拓扑测试基类：构造/清理临时工作区"""

    def setUp(self):
        """创建临时工作区，构造「宿主 + 业务项目 + 公共项目 + 共享环境」拓扑"""
        self.workspace = tempfile.mkdtemp(prefix="topo_ws_")
        self.host_dir = self._make_host("hetu-hammurabi")
        self._make_project("hetu-sybil")
        self._make_project("hetu-mercury")
        self._make_project("hetu-aether")
        venv_bin = os.path.join(self.workspace, "venv-hetu", "bin")
        os.makedirs(venv_bin)
        open(os.path.join(venv_bin, "python"), "w", encoding="utf-8").close()

    def tearDown(self):
        """清理临时工作区"""
        shutil.rmtree(self.workspace, ignore_errors=True)

    def _make_host(self, name: str) -> str:
        """构造满足三要件的宿主目录并返回其绝对路径"""
        proj = os.path.join(self.workspace, name)
        os.makedirs(os.path.join(proj, ".opencode", "agents"))
        os.makedirs(os.path.join(proj, "constitution"))
        os.makedirs(os.path.join(proj, "docs"))
        open(os.path.join(proj, "constitution", "constitution.md"), "w", encoding="utf-8").close()
        open(os.path.join(proj, "docs", "资源地图.md"), "w", encoding="utf-8").close()
        return proj

    def _make_project(self, name: str) -> str:
        """构造普通 hetu-* 业务项目目录并返回其绝对路径"""
        proj = os.path.join(self.workspace, name)
        os.makedirs(proj)
        return proj


class TestDetectHost(TestTopologyBase):
    """detect_host_dir 宿主判定测试"""

    def test_detect_host_hit(self):
        """正常案例：三要件齐全的宿主目录被命中"""
        result = detect_host_dir(self.workspace)
        self.assertEqual(result, self.host_dir)

    def test_detect_host_no_constitution(self):
        """反案例：缺少 constitution/ 的目录不能作为宿主，抛出 ValueError"""
        os.remove(os.path.join(self.host_dir, "docs", "资源地图.md"))  # 先使 base 宿主要件不全
        host = self._make_host("hetu-fake")
        os.remove(os.path.join(host, "constitution", "constitution.md"))
        os.rmdir(os.path.join(host, "constitution"))  # 目录已空，可安全删除
        with self.assertRaises(ValueError) as ctx:
            detect_host_dir(self.workspace)
        self.assertIn("hetu-fake", str(ctx.exception))

    def test_detect_host_no_resource_map(self):
        """反案例：缺少 docs/资源地图.md 的目录不能作为宿主，抛出 ValueError"""
        os.remove(os.path.join(self.host_dir, "docs", "资源地图.md"))  # 先使 base 宿主要件不全
        host = self._make_host("hetu-fake")
        os.remove(os.path.join(host, "docs", "资源地图.md"))
        with self.assertRaises(ValueError) as ctx:
            detect_host_dir(self.workspace)
        self.assertIn("hetu-fake", str(ctx.exception))

    def test_detect_host_no_agents_dir(self):
        """反案例：缺少 .opencode/agents 目录的候选不能作为宿主，抛出 ValueError"""
        os.remove(os.path.join(self.host_dir, "docs", "资源地图.md"))  # 先使 base 宿主要件不全
        host = self._make_host("hetu-fake")
        shutil.rmtree(os.path.join(host, ".opencode", "agents"))
        with self.assertRaises(ValueError) as ctx:
            detect_host_dir(self.workspace)
        self.assertIn("hetu-fake", str(ctx.exception))

    def test_detect_host_empty_workspace(self):
        """边界条件：工作区无任何 hetu-* 候选 → 抛出 ValueError 且消息含「候选目录: 无」"""
        empty_ws = tempfile.mkdtemp(prefix="topo_empty_")
        try:
            with self.assertRaises(ValueError) as ctx:
                detect_host_dir(empty_ws)
            self.assertIn("候选目录: 无", str(ctx.exception))
        finally:
            shutil.rmtree(empty_ws, ignore_errors=True)

    def test_detect_host_multi_candidates(self):
        """边界条件：多候选时取要件更完整者；要件同级按目录名升序取第一个"""
        self._make_host("hetu-alpha")   # 三要件齐全
        self._make_host("hetu-zeta")    # 三要件齐全
        partial = self._make_host("hetu-mid")
        os.remove(os.path.join(partial, "docs", "资源地图.md"))  # 仅 2 要件
        result = detect_host_dir(self.workspace)
        # 齐全者优先；两个齐全者按名称升序取 hetu-alpha
        self.assertEqual(os.path.basename(result), "hetu-alpha")


class TestListTargetProjects(TestTopologyBase):
    """list_target_projects 目标项目发现测试"""

    def test_list_target_projects_excludes_host(self):
        """正常案例：返回除宿主外的全部 hetu-* 目录，按名称排序"""
        targets, skipped = list_target_projects(self.workspace, self.host_dir)
        self.assertEqual(
            [os.path.basename(p) for p in targets],
            ["hetu-aether", "hetu-mercury", "hetu-sybil"],
        )
        self.assertEqual(skipped, [])

    def test_list_target_projects_extra(self):
        """正常案例：extra 追加非 hetu-* 前缀项目（目录存在）"""
        extra_dir = os.path.join(self.workspace, "backup-tools")
        os.makedirs(extra_dir)
        targets, skipped = list_target_projects(
            self.workspace, self.host_dir, extra="backup-tools"
        )
        self.assertIn(extra_dir, targets)
        self.assertEqual(skipped, [])

    def test_extra_nonexistent_skipped(self):
        """反案例：extra 指定不存在的项目 → 不进 targets、记入 skipped"""
        targets, skipped = list_target_projects(
            self.workspace, self.host_dir, extra="hetu-ghost"
        )
        names = [os.path.basename(p) for p in targets]
        self.assertNotIn("hetu-ghost", names)
        self.assertIn("hetu-ghost", skipped)

    def test_hetu_prefix_file_not_dir_skipped(self):
        """边界条件：hetu-* 命中但为文件（非目录）→ 跳过"""
        file_path = os.path.join(self.workspace, "hetu-notes.md")
        open(file_path, "w", encoding="utf-8").close()
        targets, _ = list_target_projects(self.workspace, self.host_dir)
        names = [os.path.basename(p) for p in targets]
        self.assertNotIn("hetu-notes.md", names)
        # hetu-* 目录全部保留
        self.assertEqual(
            names, ["hetu-aether", "hetu-mercury", "hetu-sybil"]
        )

    def test_host_not_dir_skipped(self):
        """边界条件：host_dir 传入文件路径等异常输入 → 不崩溃，正常返回目标列表"""
        file_path = os.path.join(self.workspace, "hetu-file")
        open(file_path, "w", encoding="utf-8").close()
        targets, _ = list_target_projects(self.workspace, file_path)
        names = [os.path.basename(p) for p in targets]
        # 文件不作为 host 参与比较，也不进入目标列表
        self.assertNotIn("hetu-file", names)
        self.assertEqual(
            names, ["hetu-aether", "hetu-hammurabi", "hetu-mercury", "hetu-sybil"]
        )


class TestResolvePaths(TestTopologyBase):
    """aether / venv 路径解析测试"""

    def test_resolve_aether_and_venv(self):
        """正常案例：resolve_aether_dir 与 resolve_venv_bin 返回正确绝对路径"""
        self.assertEqual(
            resolve_aether_dir(self.workspace),
            os.path.join(self.workspace, "hetu-aether"),
        )
        self.assertEqual(
            resolve_venv_bin(self.workspace),
            os.path.join(self.workspace, "venv-hetu", "bin", "python"),
        )

    def test_aether_missing_returns_none(self):
        """反案例：workspace 无 hetu-aether → 返回 None（触发调用方回退）"""
        shutil.rmtree(os.path.join(self.workspace, "hetu-aether"))
        self.assertIsNone(resolve_aether_dir(self.workspace))

    def test_venv_missing_returns_none(self):
        """反案例：workspace 无 venv-hetu → 返回 None（触发调用方回退）"""
        shutil.rmtree(os.path.join(self.workspace, "venv-hetu"))
        self.assertIsNone(resolve_venv_bin(self.workspace))


class TestBuildAndParseEnv(TestTopologyBase):
    """.harness-env 生成与解析测试"""

    def test_build_env_content_full(self):
        """正常案例：生成文本含六字段、绝对路径、PROJECT_NAME=basename、头注释"""
        content = build_env_content(
            os.path.join(self.workspace, "hetu-sybil"),
            self.workspace,
            self.host_dir,
        )
        env = parse_env_content(content)
        self.assertEqual(env["PROJECT_NAME"], "hetu-sybil")
        self.assertEqual(
            env["PROJECT_DIR"], os.path.join(self.workspace, "hetu-sybil")
        )
        self.assertEqual(env["WORKSPACE_DIR"], self.workspace)
        self.assertEqual(env["HARNESS_DIR"], self.host_dir)
        self.assertEqual(env["AETHER_DIR"], os.path.join(self.workspace, "hetu-aether"))
        self.assertEqual(
            env["VENV_BIN"], os.path.join(self.workspace, "venv-hetu", "bin", "python")
        )
        # 全部为绝对路径
        for key in ("PROJECT_DIR", "WORKSPACE_DIR", "HARNESS_DIR", "AETHER_DIR", "VENV_BIN"):
            self.assertTrue(os.path.isabs(env[key]), f"{key} 应为绝对路径")
        self.assertTrue(content.startswith("# 由 install_harness.sh 自动生成，勿手改"))

    def test_parse_env_content_roundtrip(self):
        """正常案例：build_env_content 输出 → parse_env_content 回读，六字段值一致"""
        content = build_env_content(
            os.path.join(self.workspace, "hetu-mercury"),
            self.workspace,
            self.host_dir,
        )
        env = parse_env_content(content)
        self.assertEqual(
            set(env.keys()),
            {"PROJECT_NAME", "PROJECT_DIR", "WORKSPACE_DIR", "HARNESS_DIR", "AETHER_DIR", "VENV_BIN"},
        )
        # 再序列化后回读仍一致（roundtrip 稳定）
        rebuilt = "\n".join(f"{k}={v}" for k, v in env.items())
        self.assertEqual(parse_env_content(rebuilt), env)

    def test_workspace_dir_with_space(self):
        """边界条件：父目录含空格 → 值带引号包裹，解析后路径正确（引号剥离）"""
        spaced_ws = tempfile.mkdtemp(prefix="topo ws ")
        try:
            host = os.path.join(spaced_ws, "hetu-hammurabi")
            os.makedirs(os.path.join(host, ".opencode", "agents"))
            os.makedirs(os.path.join(host, "constitution"))
            os.makedirs(os.path.join(host, "docs"))
            open(os.path.join(host, "constitution", "constitution.md"), "w", encoding="utf-8").close()
            open(os.path.join(host, "docs", "资源地图.md"), "w", encoding="utf-8").close()
            content = build_env_content(
                os.path.join(spaced_ws, "hetu-sybil"), spaced_ws, host
            )
            self.assertIn('PROJECT_DIR="', content)
            env = parse_env_content(content)
            self.assertEqual(env["PROJECT_DIR"], os.path.join(spaced_ws, "hetu-sybil"))
            self.assertEqual(env["WORKSPACE_DIR"], spaced_ws)
            self.assertEqual(env["HARNESS_DIR"], host)
        finally:
            shutil.rmtree(spaced_ws, ignore_errors=True)

    def test_parse_env_comments_blank_duplicate(self):
        """边界条件：空行/# 注释/重复键 → 空行注释跳过、重复键后者覆盖"""
        text = (
            "# 由 install_harness.sh 自动生成，勿手改\n"
            "\n"
            "PROJECT_NAME=hetu-sybil\n"
            "# 注释行应被跳过\n"
            'AETHER_DIR="/path with space/aether"\n'
            "AETHER_DIR=/path/without/space/aether\n"
            "VENV_BIN=\n"
        )
        env = parse_env_content(text)
        self.assertEqual(env["PROJECT_NAME"], "hetu-sybil")
        self.assertEqual(env["AETHER_DIR"], "/path/without/space/aether")
        self.assertEqual(env["VENV_BIN"], "")

    def test_parse_env_line_without_equal_skipped(self):
        """边界条件：无等号的行（非注释非空）被跳过，不影响其他字段解析"""
        text = "PROJECT_NAME=hetu-sybil\n孤零零一行没有等号\nVENV_BIN=/x/y\n"
        env = parse_env_content(text)
        self.assertEqual(
            env, {"PROJECT_NAME": "hetu-sybil", "VENV_BIN": "/x/y"}
        )

    def test_build_env_missing_aether_venv(self):
        """边界条件：工作区无 hetu-aether / venv-hetu → 对应字段写空值并附缺失注释"""
        bare_ws = tempfile.mkdtemp(prefix="topo_bare_")
        try:
            content = build_env_content(
                os.path.join(bare_ws, "proj"), bare_ws, os.path.join(bare_ws, "host")
            )
            self.assertIn("# AETHER_DIR 缺失", content)
            self.assertIn("AETHER_DIR=\n", content)
            self.assertIn("# VENV_BIN 缺失", content)
            self.assertIn("VENV_BIN=\n", content)
            env = parse_env_content(content)
            self.assertEqual(env["AETHER_DIR"], "")
            self.assertEqual(env["VENV_BIN"], "")
        finally:
            shutil.rmtree(bare_ws, ignore_errors=True)


def run_tests():
    """执行所有测试并输出结果（unit_test.md「八、测试结果输出」模式）"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for case_cls in (TestDetectHost, TestListTargetProjects, TestResolvePaths, TestBuildAndParseEnv):
        suite.addTests(loader.loadTestsFromTestCase(case_cls))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 确保输出目录存在
    test_result_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test")
    os.makedirs(test_result_dir, exist_ok=True)

    # 写入结果文件
    result_file = os.path.join(test_result_dir, "test_harness_topology_result.txt")
    with open(result_file, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("harness_topology 单元测试结果\n")
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
