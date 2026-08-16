# -*- coding: utf-8 -*-
"""
test_logo_svg 单元测试
20260804任务1 河图Logo设计：SVG 设计资产合规性单元测试

测试对象：design/ 目录下 5 个河图 Logo 备选 SVG 文件（hetu_logo_01.svg ~ hetu_logo_05.svg）
覆盖范围（任务书第七节，共 10 个用例）：
  - 正常案例 6 个：文件数量与命名 / XML 合法性 / viewBox 合规 / 自包含 / 卷轴分组 / 颜色受控
  - 反案例  2 个：非法 XML 抛 ParseError / 缺 viewBox 校验失败（验证测试自身有效性）
  - 边界案例 2 个：viewBox 500/1024 边界 / 颜色数 8/9 阈值边界
反案例与边界案例均通过 tempfile 构造临时 SVG 验证，不写入 design/ 目录，避免污染文件数量断言。
"""

import os
import re
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET

# ---------------------------------------------------------------------------
# 全局配置常量
# ---------------------------------------------------------------------------
# design/ 目录定位：本文件位于任务目录 unit_test/ 下，design 为其兄弟目录
DESIGN_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "design")
)

# 期望存在的 5 个 SVG 文件名（精确匹配，排除任何临时文件污染）
EXPECTED_SVG_FILES = {
    "hetu_logo_01.svg",
    "hetu_logo_02.svg",
    "hetu_logo_03.svg",
    "hetu_logo_04.svg",
    "hetu_logo_05.svg",
}

# 允许的 viewBox 画布尺寸（宽高相等，见任务书第四节）
ALLOWED_VIEWBOX_SIZES = {(500, 500), (1024, 1024)}

# 颜色数量硬上限（任务书 A6：去重颜色 ≤ 8 种）
MAX_COLOR_COUNT = 8

# 通用安全字体族（自包含约束：不得依赖外部字体文件）
SAFE_FONT_FAMILIES = {
    "serif", "sans-serif", "monospace",
    "SimSun", "KaiTi", "FangSong", "SimHei", "Microsoft YaHei",
    "宋体", "楷体", "仿宋", "黑体", "微软雅黑",
    "Arial", "Helvetica", "Times New Roman", "Georgia", "Verdana",
    "Courier New",
}

# ---------------------------------------------------------------------------
# 模块级纯函数（供反案例 / 边界案例直接调用，验证测试逻辑自身有效性）
# ---------------------------------------------------------------------------
_HEX_RE = re.compile(r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?")
_URL_RE = re.compile(r"url\(\s*#([^)]+)\)")
_RGB_RE = re.compile(r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)")
_STYLE_DECL_RE = re.compile(r"([a-zA-Z-]+)\s*:\s*([^;]+)")


def _svg_files():
    """返回 design/ 目录下匹配 hetu_logo_0*.svg 的文件名列表（不含路径）"""
    pattern = os.path.join(DESIGN_DIR, "hetu_logo_0*.svg")
    return [os.path.basename(p) for p in sorted(__import__("glob").glob(pattern))]


def _parse_svg(path):
    """解析 SVG 文件为 Element；非法 XML 时抛 ET.ParseError"""
    with open(path, "r", encoding="utf-8") as f:
        return ET.fromstring(f.read())


def _viewbox_ok(root):
    """校验 viewBox 存在且为允许尺寸：0 0 500 500 或 0 0 1024 1024（宽高相等）"""
    vb = root.get("viewBox")
    if vb is None:
        return False
    parts = re.split(r"[ ,]+", vb.strip())
    if len(parts) != 4:
        return False
    try:
        x, y, w, h = (float(p) for p in parts)
    except ValueError:
        return False
    return (w, h) in ALLOWED_VIEWBOX_SIZES and w == h


def _dimension_ok(root):
    """校验 width/height 声明与 viewBox 比例一致（100% 或省略视为由 viewBox 控制）"""
    vb = root.get("viewBox")
    w_attr, h_attr = root.get("width"), root.get("height")
    if not vb or w_attr is None or h_attr is None:
        return True

    def to_num(v):
        s = v.strip()
        if s.endswith("%"):
            return None  # 百分比声明不校验数值
        try:
            return float(s)
        except ValueError:
            return None

    rw, rh = to_num(w_attr), to_num(h_attr)
    if rw is None or rh is None:
        return True
    return abs(rw - rh) < 1e-9


def _color_tokens_from_value(value):
    """从单个 fill/stroke 属性值提取颜色 token 集合（url(#x) 按渐变 id 归一，none 不计）"""
    tokens = set()
    v = value.strip()
    if v.lower() in ("none", "transparent", "inherit", "currentcolor"):
        return tokens
    for m in _URL_RE.finditer(v):
        tokens.add("url(#" + m.group(1).strip().lower() + ")")
    for m in _HEX_RE.finditer(v):
        tokens.add(m.group(0).lower())
    for m in _RGB_RE.finditer(v):
        tokens.add("rgb({},{},{})".format(m.group(1), m.group(2), m.group(3)))
    return tokens


def _collect_color_tokens(root):
    """收集全文件去重颜色 token：fill/stroke 属性（含 style 内联），url(#渐变) 计 1 种"""
    tokens = set()
    for elem in root.iter():
        # 直接属性声明
        for attr in ("fill", "stroke"):
            val = elem.get(attr)
            if val:
                tokens |= _color_tokens_from_value(val)
        # style 内联声明（如 style="fill:#B33A2E; stroke:none"）
        style = elem.get("style") or ""
        for m in _STYLE_DECL_RE.finditer(style):
            prop = m.group(1).strip().lower()
            if prop in ("fill", "stroke"):
                tokens |= _color_tokens_from_value(m.group(2).strip())
    return tokens


def _color_ok(root):
    """校验去重颜色数不超过上限（≤ 8 种）"""
    return len(_collect_color_tokens(root)) <= MAX_COLOR_COUNT


def _scroll_groups(root):
    """返回所有 id 以 scroll- 开头的 <g> 分组 id 列表"""
    ids = []
    for elem in root.iter():
        # 注意：带命名空间的 tag 形如 {http://www.w3.org/2000/svg}g，用 endswith 判断
        if elem.tag.endswith("g"):
            gid = elem.get("id") or ""
            if gid.startswith("scroll-"):
                ids.append(gid)
    return ids


def _self_contained_problems(root, text):
    """自包含检查：返回问题列表（空列表表示通过）"""
    problems = []
    for elem in root.iter():
        tag = elem.tag if isinstance(elem.tag, str) else ""
        local = tag.rsplit("}", 1)[-1]
        if local == "image":
            problems.append("存在 <image> 位图引用")
        if local == "link":
            problems.append("存在 <link> 外部样式表引用")
        # font-family 属性 / style 内联字体族校验
        ff = elem.get("font-family")
        if ff:
            fam = ff.split(",")[0].strip().strip('"').strip("'")
            if fam not in SAFE_FONT_FAMILIES:
                problems.append("外部字体族: " + fam)
        style = elem.get("style") or ""
        m = re.search(r"font-family\s*:\s*([^;]+)", style)
        if m:
            fam = m.group(1).split(",")[0].strip().strip('"').strip("'")
            if fam not in SAFE_FONT_FAMILIES:
                problems.append("外部字体族(style): " + fam)
    # 全文级检查
    if re.search(r"@import", text):
        problems.append("存在 @import 外部样式表引用")
    for m in re.finditer(r"url\(\s*(?!#)", text):
        problems.append("存在 url( 外链: " + m.group(0)[:40])
    return problems


# ---------------------------------------------------------------------------
# 正常案例
# ---------------------------------------------------------------------------
class TestLogoFiles(unittest.TestCase):
    """正常案例：对 design/ 下真实设计文件的合规性断言"""

    @classmethod
    def setUpClass(cls):
        """一次性加载 5 个真实设计文件，供全部正常用例共享"""
        cls.files = []
        cls.roots = {}
        for name in sorted(EXPECTED_SVG_FILES):
            path = os.path.join(DESIGN_DIR, name)
            cls.files.append(path)
            cls.roots[name] = _parse_svg(path)

    def test_five_svg_files_exist(self):
        """design/ 下恰好 5 个 hetu_logo_0N.svg，命名精确匹配，排除临时文件污染"""
        found = set(_svg_files())
        self.assertEqual(len(found), 5, "design/ 下 SVG 文件数量应为 5，实际: %s" % sorted(found))
        self.assertSetEqual(found, EXPECTED_SVG_FILES)

    def test_svg_xml_well_formed(self):
        """每个文件均可被 ET.fromstring 解析，根标签为 svg（兼容命名空间）"""
        for name, root in self.roots.items():
            self.assertIsNotNone(root, "%s 解析结果为空" % name)
            self.assertTrue(root.tag.endswith("svg"),
                            "%s 根标签应为 svg，实际: %s" % (name, root.tag))

    def test_viewbox_valid(self):
        """viewBox 为 0 0 500 500 或 0 0 1024 1024（宽高相等），width/height 比例一致"""
        for name, root in self.roots.items():
            self.assertTrue(_viewbox_ok(root), "%s viewBox 不合规: %s" % (name, root.get("viewBox")))
            self.assertTrue(_dimension_ok(root), "%s width/height 与 viewBox 比例不一致" % name)

    def test_self_contained(self):
        """无 image/link 元素、无 url( 外链（允许 url(#grad-...) 内联渐变）、无 @import、字体安全"""
        for name in sorted(EXPECTED_SVG_FILES):
            with open(os.path.join(DESIGN_DIR, name), "r", encoding="utf-8") as f:
                text = f.read()
            problems = _self_contained_problems(self.roots[name], text)
            self.assertEqual(problems, [], "%s 自包含检查未通过: %s" % (name, problems))

    def test_scroll_imagery_present(self):
        """每个文件至少存在一个 id 以 scroll- 开头的 <g> 卷轴分组"""
        for name, root in self.roots.items():
            ids = _scroll_groups(root)
            self.assertGreaterEqual(len(ids), 1, "%s 缺少 scroll- 卷轴分组" % name)

    def test_color_count_controlled(self):
        """每个文件去重颜色数（fill/stroke 的 #/rgb/url(#渐变) 引用）≤ 8"""
        for name, root in self.roots.items():
            tokens = _collect_color_tokens(root)
            self.assertLessEqual(
                len(tokens), MAX_COLOR_COUNT,
                "%s 颜色数 %d 超过上限 %d: %s" % (name, len(tokens), MAX_COLOR_COUNT, sorted(tokens)))


# ---------------------------------------------------------------------------
# 反案例
# ---------------------------------------------------------------------------
class TestLogoNegative(unittest.TestCase):
    """反案例：非法输入应被校验函数拒绝，验证测试逻辑自身有效性"""

    def setUp(self):
        """创建临时目录存放反案例 SVG 文件（严禁写入 design/ 目录）"""
        self.tmp_dir = tempfile.mkdtemp(prefix="logo_neg_", dir=tempfile.gettempdir())

    def tearDown(self):
        """清理临时目录"""
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _write_svg(self, name, content):
        """将内容写入临时目录并返回路径"""
        path = os.path.join(self.tmp_dir, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_reject_invalid_xml(self):
        """非 XML 文本（标签不闭合）解析应抛 ET.ParseError"""
        bad_svgs = [
            "<svg><g></svg>",            # 标签不闭合
            "<svg><rect></svg>",         # rect 未闭合
            "this is not xml at all",    # 纯文本
        ]
        for i, content in enumerate(bad_svgs):
            path = self._write_svg("bad_%d.svg" % i, content)
            with self.assertRaises(ET.ParseError, msg="内容应解析失败: %r" % content):
                _parse_svg(path)

    def test_reject_missing_viewbox(self):
        """缺 viewBox 或 viewBox 为非允许尺寸时，_viewbox_ok 应返回 False"""
        # 合法 XML 但缺 viewBox
        no_vb = self._write_svg("no_viewbox.svg",
                                '<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%"></svg>')
        self.assertFalse(_viewbox_ok(_parse_svg(no_vb)), "缺 viewBox 应校验失败")
        # viewBox 为非允许尺寸（300x300）
        wrong_vb = self._write_svg("wrong_viewbox.svg",
                                   '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 300"></svg>')
        self.assertFalse(_viewbox_ok(_parse_svg(wrong_vb)), "非允许尺寸 viewBox 应校验失败")
        # viewBox 格式非法（仅 2 个数）
        bad_vb = self._write_svg("bad_viewbox.svg",
                                 '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500"></svg>')
        self.assertFalse(_viewbox_ok(_parse_svg(bad_vb)), "格式非法的 viewBox 应校验失败")


# ---------------------------------------------------------------------------
# 边界案例
# ---------------------------------------------------------------------------
class TestLogoBoundary(unittest.TestCase):
    """边界案例：viewBox 尺寸边界与颜色数量阈值边界"""

    def setUp(self):
        """创建临时目录存放边界 SVG 文件"""
        self.tmp_dir = tempfile.mkdtemp(prefix="logo_bnd_", dir=tempfile.gettempdir())

    def tearDown(self):
        """清理临时目录"""
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _write_svg(self, name, content):
        """将内容写入临时目录并返回路径"""
        path = os.path.join(self.tmp_dir, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def _svg_with_viewbox(self, vb):
        """构造指定 viewBox 的合法 SVG 文本"""
        return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="%s"></svg>' % vb)

    def test_viewbox_boundary_sizes(self):
        """viewBox 恰为 500 与 1024 两个边界值时均通过，越界（501/1023）即失败"""
        # 两个允许尺寸下边界值应通过
        for vb in ("0 0 500 500", "0 0 1024 1024"):
            path = self._write_svg("vb_%s.svg" % vb.replace(" ", "_"), self._svg_with_viewbox(vb))
            self.assertTrue(_viewbox_ok(_parse_svg(path)), "允许尺寸 %s 应通过校验" % vb)
        # 越界（宽高不等）应失败
        for vb in ("0 0 500 501", "0 0 1024 1023"):
            path = self._write_svg("vb_%s.svg" % vb.replace(" ", "_"), self._svg_with_viewbox(vb))
            self.assertFalse(_viewbox_ok(_parse_svg(path)), "越界尺寸 %s 应校验失败" % vb)

    def _svg_with_n_colors(self, n):
        """构造恰好 n 种 fill 颜色的合法 SVG 文本（#000001 ~ #00000n）"""
        rects = "".join('<rect fill="#%06d"/>' % i for i in range(1, n + 1))
        return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 500">%s</svg>' % rects

    def test_color_count_boundary(self):
        """颜色数恰为上限 8 时通过、9 时失败（阈值边界两侧）"""
        ok8 = self._write_svg("colors_8.svg", self._svg_with_n_colors(8))
        self.assertTrue(_color_ok(_parse_svg(ok8)), "恰好 8 种颜色应通过（上限边界内）")
        self.assertEqual(len(_collect_color_tokens(_parse_svg(ok8))), 8, "8 种颜色应全部被统计")
        bad9 = self._write_svg("colors_9.svg", self._svg_with_n_colors(9))
        self.assertFalse(_color_ok(_parse_svg(bad9)), "9 种颜色应校验失败（超出上限）")


# ---------------------------------------------------------------------------
# 结果输出（unit_test.md 第八节）
# ---------------------------------------------------------------------------
def run_tests():
    """执行全部测试并将结果写入 unit_test/test/test_logo_svg_result.txt"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestLogoFiles))
    suite.addTests(loader.loadTestsFromTestCase(TestLogoNegative))
    suite.addTests(loader.loadTestsFromTestCase(TestLogoBoundary))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 确保输出目录存在
    test_result_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test")
    os.makedirs(test_result_dir, exist_ok=True)

    # 写入结果文件
    result_file = os.path.join(test_result_dir, "test_logo_svg_result.txt")
    with open(result_file, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("test_logo_svg 单元测试结果（河图Logo设计）\n")
        f.write("=" * 60 + "\n\n")
        f.write("测试总数: %d\n" % result.testsRun)
        f.write("成功: %d\n" % (result.testsRun - len(result.failures) - len(result.errors)))
        f.write("失败: %d\n" % len(result.failures))
        f.write("错误: %d\n\n" % len(result.errors))

        if result.failures:
            f.write("-" * 40 + "\n失败用例:\n" + "-" * 40 + "\n")
            for test, traceback in result.failures:
                f.write("\n%s:\n%s\n" % (test, traceback))

        if result.errors:
            f.write("-" * 40 + "\n错误用例:\n" + "-" * 40 + "\n")
            for test, traceback in result.errors:
                f.write("\n%s:\n%s\n" % (test, traceback))

        f.write("\n" + "=" * 60 + "\n")
        if result.wasSuccessful():
            f.write("测试结果: 全部通过\n")
        else:
            f.write("测试结果: 存在失败/错误\n")
        f.write("=" * 60 + "\n")

    print("\n测试结果已保存至: %s" % result_file)
    return result


if __name__ == "__main__":
    # 需要保存测试结果时用 run_tests()
    run_tests()
