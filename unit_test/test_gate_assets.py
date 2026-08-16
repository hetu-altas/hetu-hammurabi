# -*- coding: utf-8 -*-
"""H6 资产登记一致性检查回归测试

覆盖：
- docs/hetu-*/ 未登记 → 告警（ok=False）
- docs/hetu-*/ 已登记 → 静默（ok=True）
- 非 docs/hetu-*/ 路径不检查（跳过）
- .harness-env 缺失 → 回退当前项目资源地图
- HARNESS_DIR 字段缺失 → 回退当前项目资源地图
- 宿主资源地图不存在 → 回退当前项目资源地图
- 资源地图不存在 → 未登记告警
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from harness.core import assets_check


class TestResolveResourceMapPath(unittest.TestCase):
    """资源地图路径解析（宿主优先/回退）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project = Path(self._tmp.name) / "hetu-demo"
        self.project.mkdir(parents=True)
        (self.project / "docs").mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self._tmp.cleanup()

    def test_env_missing_fallback_to_project(self):
        """边界：.harness-env 缺失 → 回退当前项目 docs/资源地图.md。"""
        (self.project / "docs" / "资源地图.md").write_text("# 资源地图", encoding="utf-8")
        p = assets_check.resolve_resource_map_path(self.project)
        self.assertEqual(p, self.project / "docs" / "资源地图.md")

    def test_env_harness_dir_field_missing_fallback(self):
        """反案例：.harness-env 存在但无 HARNESS_DIR 字段 → 回退当前项目。"""
        env_dir = self.project / ".opencode"
        env_dir.mkdir(exist_ok=True)
        (env_dir / ".harness-env").write_text("VENV_BIN=/x\n", encoding="utf-8")
        (self.project / "docs" / "资源地图.md").write_text("# 资源地图", encoding="utf-8")
        p = assets_check.resolve_resource_map_path(self.project)
        self.assertEqual(p, self.project / "docs" / "资源地图.md")

    def test_host_map_used_when_present(self):
        """正常案例：HARNESS_DIR 指向宿主且宿主资源地图存在 → 用宿主地图。"""
        host = Path(self._tmp.name) / "hetu-harness"
        (host / "docs").mkdir(parents=True)
        (host / "docs" / "资源地图.md").write_text("# 宿主地图", encoding="utf-8")
        env_dir = self.project / ".opencode"
        env_dir.mkdir(exist_ok=True)
        (env_dir / ".harness-env").write_text(
            f'HARNESS_DIR="{host}"\nVENV_BIN=/x\n', encoding="utf-8"
        )
        p = assets_check.resolve_resource_map_path(self.project)
        self.assertEqual(p, host / "docs" / "资源地图.md")

    def test_host_map_missing_fallback(self):
        """反案例：HARNESS_DIR 指向宿主但宿主资源地图不存在 → 回退当前项目。"""
        host = Path(self._tmp.name) / "hetu-harness"
        host.mkdir(exist_ok=True)  # 无 docs/资源地图.md
        env_dir = self.project / ".opencode"
        env_dir.mkdir(exist_ok=True)
        (env_dir / ".harness-env").write_text(
            f"HARNESS_DIR={host}\n", encoding="utf-8"
        )
        (self.project / "docs" / "资源地图.md").write_text("# 资源地图", encoding="utf-8")
        p = assets_check.resolve_resource_map_path(self.project)
        self.assertEqual(p, self.project / "docs" / "资源地图.md")


class TestCheckRegistered(unittest.TestCase):
    """登记校验（未登记告警/已登记静默/路径过滤）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.map_file = self.root / "资源地图.md"
        self.map_file.write_text(
            "# 资源地图\n| 文档 |\n|------|\n| demo-design.md |\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self._tmp.cleanup()

    def test_unregistered_warns(self):
        """反案例：docs/hetu-*/ 下未登记 → 告警（ok=False）。"""
        target = str(self.root / "docs" / "hetu-demo" / "new-design.md")
        ok, reason = assets_check.check_registered(target, self.map_file)
        self.assertFalse(ok)
        self.assertIn("未登记", reason)

    def test_registered_silent(self):
        """正常案例：docs/hetu-*/ 下已登记 → 静默（ok=True）。"""
        target = str(self.root / "docs" / "hetu-demo" / "demo-design.md")
        ok, reason = assets_check.check_registered(target, self.map_file)
        self.assertTrue(ok)
        self.assertIn("已登记", reason)

    def test_non_hetu_docs_skipped(self):
        """边界：非 docs/hetu-*/ 路径 → 跳过检查（ok=True）。"""
        for target in (
            str(self.root / "docs" / "harness" / "gates.md"),
            str(self.root / "src" / "main.py"),
            str(self.root / "README.md"),
        ):
            ok, reason = assets_check.check_registered(target, self.map_file)
            self.assertTrue(ok, target)
            self.assertIn("跳过", reason)

    def test_map_missing_warns(self):
        """反案例：资源地图不存在 → 未登记告警。"""
        target = str(self.root / "docs" / "hetu-demo" / "a.md")
        ok, reason = assets_check.check_registered(target, self.root / "ghost" / "地图.md")
        self.assertFalse(ok)
        self.assertIn("不存在", reason)

    def test_basename_match_only(self):
        """边界：同名文件不同目录已登记 → 通过（旧版 includes(basename) 语义）。"""
        self.map_file.write_text("other-design.md\n", encoding="utf-8")
        target = str(self.root / "docs" / "hetu-demo" / "other-design.md")
        ok, _ = assets_check.check_registered(target, self.map_file)
        self.assertTrue(ok)


class TestCliAssetsCheck(unittest.TestCase):
    """assets-check CLI 契约测试（20260815 任务2 新增：旧插件 tool.execute.after 委托路径）。

    子进程调用风格沿用 test_gate_concurrency.py（sys.executable -m harness.core.cli，
    cwd=宿主根），覆盖旧插件 assets-check 调用路径的出参契约与回退行为。
    """

    HOST_ROOT = str(Path(__file__).resolve().parent.parent)

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project = Path(self._tmp.name) / "hetu-demo"
        (self.project / "docs" / "hetu-demo").mkdir(parents=True)
        (self.project / "docs" / "资源地图.md").write_text("# 资源地图\n", encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def _check(self, file_path):
        """以子进程执行 assets-check（模拟旧插件 execFileSync 调用）。"""
        return subprocess.run(
            [
                sys.executable, "-m", "harness.core.cli", "assets-check",
                "--project-dir", str(self.project),
                "--file", file_path,
                "--json",
            ],
            cwd=self.HOST_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
        )

    def test_unregistered_warns(self):
        """反案例：docs/hetu-*/ 未登记 → stdout JSON {ok,reason,map_path}，
        ok=false、reason 含「未登记」、退出码 1。"""
        target = str(self.project / "docs" / "hetu-demo" / "未登记.md")
        p = self._check(target)
        data = json.loads(p.stdout.strip())
        for key in ("ok", "reason", "map_path"):
            self.assertIn(key, data)
        self.assertFalse(data["ok"])
        self.assertIn("未登记", data["reason"])
        self.assertEqual(p.returncode, 1)

    def test_registered_silent(self):
        """正常案例：资源地图已含 basename → ok=true、退出码 0。"""
        (self.project / "docs" / "资源地图.md").write_text(
            "# 资源地图\n| demo.md |\n", encoding="utf-8"
        )
        target = str(self.project / "docs" / "hetu-demo" / "demo.md")
        p = self._check(target)
        data = json.loads(p.stdout.strip())
        self.assertTrue(data["ok"])
        self.assertEqual(p.returncode, 0)

    def test_host_map_missing_fallback(self):
        """边界：HARNESS_DIR 指向无资源地图的宿主 → map_path 回退当前项目资源地图。"""
        host = Path(self._tmp.name) / "hetu-harness"
        host.mkdir(exist_ok=True)  # 无 docs/资源地图.md
        env_dir = self.project / ".opencode"
        env_dir.mkdir(exist_ok=True)
        (env_dir / ".harness-env").write_text(f"HARNESS_DIR={host}\n", encoding="utf-8")
        target = str(self.project / "docs" / "hetu-demo" / "未登记.md")
        p = self._check(target)
        data = json.loads(p.stdout.strip())
        self.assertFalse(data["ok"])
        self.assertEqual(data["map_path"], str(self.project / "docs" / "资源地图.md"))


if __name__ == "__main__":
    unittest.main()
