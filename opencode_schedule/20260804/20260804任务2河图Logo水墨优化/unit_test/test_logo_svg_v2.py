# -*- coding: utf-8 -*-
"""
test_logo_svg_v2 单元测试
20260804任务2 河图Logo水墨优化：二期 SVG 设计资产合规性单元测试

测试对象：design/ 目录下 5 个水墨优化 Logo SVG 文件（hetu_logo_06.svg ~ hetu_logo_10.svg）
覆盖范围（任务书第七节，共 15 个用例）：
  - 正常案例  9 个：文件数量与命名 / XML 合法性 / viewBox 合规 / 自包含 /
                    卷轴分组 / 颜色受控 / 二期低饱和色板 / 滚筒尺寸比例 / K 线手绘 path
  - 反案例    2 个：非法 XML 抛 ParseError / 缺 viewBox 校验失败（验证测试自身有效性）
  - 边界案例  4 个：viewBox 500/1024 边界 / 颜色数 8/9 阈值 / 色板恰 8 色与混入违禁色 /
                    滚筒比例 0.08/0.14 阈值两侧
反案例与边界案例均通过 tempfile 构造临时 SVG 验证（严格写临时目录、tearDown 清理），
严禁写入 design/ 目录，避免污染文件数量断言。

关键口径（编码节点约定）：
  1. glob 使用 hetu_logo_*.svg（hetu_logo_0*.svg 匹配不到 10 号文件）；
  2. A7 色板校验剔除 url(#...) 渐变引用 token（渐变安全由 stop-color ⊆ 色板保证），
     仅对 hex/rgb 与 stop-color 断言属于二期 8 色板；
  3. 滚筒轴向厚度 T 取 scroll-roll 内 rect 的 height（path 取纵向跨度），
     画幅宽 W 取 scroll-body 内主画幅 rect 的 width。
"""

import glob
import json
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

# 期望存在的 5 个 SVG 文件名（精确集合匹配，排除任何临时文件污染）
EXPECTED_SVG_FILES = {
    "hetu_logo_06.svg",
    "hetu_logo_07.svg",
    "hetu_logo_08.svg",
    "hetu_logo_09.svg",
    "hetu_logo_10.svg",
}

# 允许的 viewBox 画布尺寸（宽高相等，见任务书四 §4.5）
ALLOWED_VIEWBOX_SIZES = {(500, 500), (1024, 1024)}

# 颜色数量硬上限（任务书 A6：去重颜色 token ≤ 8 种）
MAX_COLOR_COUNT = 8

# 二期低饱和色板（任务书四 §4.1 固化 8 色，归一化为小写 hex）
PALETTE = {
    "#f3e9d6",  # 淡赭纸
    "#3b3733",  # 焦墨
    "#57504a",  # 重墨
    "#8d8578",  # 淡墨
    "#b7afa2",  # 清墨
    "#4e5d66",  # 黛青
    "#a96b5f",  # 淡朱砂
    "#a9976b",  # 哑金
}

# 任务1 高饱和色板违禁色（出现即失败）
FORBIDDEN_COLORS = {
    "#b33a2e",  # 朱砂（任务1）
    "#c0a062",  # 鎏金（任务1）
    "#264653",  # 玄青（任务1）
    "#1c1c22",  # 墨黑（任务1）
    "#f6f1e5",  # 宣纸米白（任务1）
    "#9aa0a6",  # 玄灰（任务1）
}

# 滚筒轴向厚度 T 与画幅宽 W 之比的下限 / 上限（任务书 A8）
ROLL_RATIO_MIN = 0.08
ROLL_RATIO_MAX = 0.14

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
_PATH_TOKEN_RE = re.compile(r"[MLCQSTAmlcqstaHVhvZz]|-?\d+(?:\.\d+)?")


def _svg_files():
    """返回 design/ 目录下匹配 hetu_logo_*.svg 的文件名列表（不含路径）

    口径提示：不得使用 hetu_logo_0*.svg（其第 11 字符固定为 0，匹配不到
    hetu_logo_10.svg），统一使用 hetu_logo_*.svg 或双模式匹配。
    """
    pattern = os.path.join(DESIGN_DIR, "hetu_logo_*.svg")
    return [os.path.basename(p) for p in sorted(glob.glob(pattern))]


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
    """A6 口径：收集全文件去重颜色 token（fill/stroke 属性含 style 内联），url(#渐变) 计 1 种"""
    tokens = set()
    for elem in root.iter():
        # 直接属性声明
        for attr in ("fill", "stroke"):
            val = elem.get(attr)
            if val:
                tokens |= _color_tokens_from_value(val)
        # style 内联声明（如 style="fill:#3B3733; stroke:none"）
        style = elem.get("style") or ""
        for m in _STYLE_DECL_RE.finditer(style):
            prop = m.group(1).strip().lower()
            if prop in ("fill", "stroke"):
                tokens |= _color_tokens_from_value(m.group(2).strip())
    return tokens


def _collect_palette_tokens(root):
    """A7 口径：收集色板校验全量颜色集合

    在 A6 收集基础上剔除 url(#...) 渐变引用 token（渐变安全由 stop-color ⊆ 色板保证），
    并追加遍历所有 <stop> 元素的 stop-color 属性。
    """
    tokens = set()
    for elem in root.iter():
        for attr in ("fill", "stroke"):
            val = elem.get(attr)
            if val:
                for t in _color_tokens_from_value(val):
                    if not t.startswith("url("):
                        tokens.add(t)
        style = elem.get("style") or ""
        for m in _STYLE_DECL_RE.finditer(style):
            prop = m.group(1).strip().lower()
            if prop in ("fill", "stroke"):
                for t in _color_tokens_from_value(m.group(2).strip()):
                    if not t.startswith("url("):
                        tokens.add(t)
        # 渐变 stop 的 stop-color 必须参与色板校验
        sc = elem.get("stop-color")
        if sc:
            tokens |= _color_tokens_from_value(sc)
    return tokens


def _color_ok(root):
    """校验去重颜色数不超过上限（A6：≤ 8 种）"""
    return len(_collect_color_tokens(root)) <= MAX_COLOR_COUNT


def _palette_ok(root):
    """校验 A7：全部颜色（fill/stroke 的 hex/rgb + stop-color）均属于二期 8 色板

    返回 (是否通过, 违规颜色列表)，出现任务1 违禁色或色板外颜色即失败。
    """
    tokens = _collect_palette_tokens(root)
    bad = sorted(t for t in tokens if t not in PALETTE)
    return len(bad) == 0, bad


def _scroll_groups(root):
    """返回所有 id 以 scroll- 开头的 <g> 分组 id 列表"""
    ids = []
    for elem in root.iter():
        # 带命名空间的 tag 形如 {http://www.w3.org/2000/svg}g，用 endswith 判断
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


def _path_y_span(d):
    """解析 path 数据中 M/L/C/Q/S/T/A 命令的全部 y 坐标，返回 max_y - min_y

    横向滚筒 path 的 y 跨度即其"平均厚度"口径；解析失败或无可解析坐标返回 0。
    """
    if not d:
        return 0.0
    tokens = _PATH_TOKEN_RE.findall(d)
    ys = []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t in "MLCQSTAm lcqsta":
            # 成对参数命令：x,y 依次成对，偶数下标为 y
            i += 1
            nums = []
            while i < len(tokens) and tokens[i] not in "MLCQSTAmlcqstaHVhvZz":
                nums.append(float(tokens[i]))
                i += 1
            ys.extend(nums[1::2])
        elif t in "HVhv":
            # 单参数命令（仅 x 或仅 y），坐标不成对，跳过不计
            i += 1
            if i < len(tokens) and tokens[i] not in "MLCQSTAmlcqstaHVhvZz":
                i += 1
        else:  # Zz 闭合命令
            i += 1
    if not ys:
        return 0.0
    return max(ys) - min(ys)


def _roll_thickness(root):
    """计算 scroll-roll 分组内滚筒轴向厚度 T（取最大值）

    口径：<rect> 取 height；<path> 取 _path_y_span 纵向跨度；
    轴头 circle / 高光 line 等装饰元素不参与统计。
    """
    thicknesses = []
    for grp in root.iter():
        if not grp.tag.endswith("g"):
            continue
        if (grp.get("id") or "").startswith("scroll-roll"):
            for child in grp.iter():
                if child is grp:
                    continue
                local = child.tag.rsplit("}", 1)[-1] if isinstance(child.tag, str) else ""
                if local == "rect":
                    h = child.get("height")
                    if h:
                        try:
                            thicknesses.append(float(h))
                        except ValueError:
                            pass
                elif local == "path":
                    thicknesses.append(_path_y_span(child.get("d") or ""))
    return max(thicknesses) if thicknesses else 0.0


def _body_width(root):
    """计算 scroll-body 分组内主画幅矩形宽度 W（取 width 最大值）"""
    widths = []
    for grp in root.iter():
        if not grp.tag.endswith("g"):
            continue
        if (grp.get("id") or "").startswith("scroll-body"):
            for child in grp.iter():
                if child is grp:
                    continue
                local = child.tag.rsplit("}", 1)[-1] if isinstance(child.tag, str) else ""
                if local == "rect":
                    w = child.get("width")
                    if w:
                        try:
                            widths.append(float(w))
                        except ValueError:
                            pass
    return max(widths) if widths else 0.0


def _roll_ratio_ok(root):
    """校验滚筒轴向厚度 T 与画幅宽 W 之比 ∈ [0.08, 0.14]（round 6 位防浮点抖动）"""
    t = _roll_thickness(root)
    w = _body_width(root)
    if w <= 0:
        return False
    ratio = round(t / w, 6)
    return ROLL_RATIO_MIN <= ratio <= ROLL_RATIO_MAX


def _kline_has_path(root):
    """校验 K 线量化分组（id 含 kline 或 quant- 前缀）内至少存在 1 个 <path> 元素

    对应任务书 A9：K 线不得全部由纯几何 rect+line 构成，手绘笔触以 path 为载体。
    """
    for grp in root.iter():
        if not grp.tag.endswith("g"):
            continue
        gid = grp.get("id") or ""
        if "kline" in gid or gid.startswith("quant-"):
            for child in grp.iter():
                if child is grp:
                    continue
                local = child.tag.rsplit("}", 1)[-1] if isinstance(child.tag, str) else ""
                if local == "path":
                    return True
    return False


# ---------------------------------------------------------------------------
# 正常案例
# ---------------------------------------------------------------------------
class TestLogoV2Files(unittest.TestCase):
    """正常案例：对 design/ 下真实二期设计文件的合规性断言"""

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
        """design/ 下恰好 5 个 hetu_logo_06~10.svg，命名精确匹配，排除临时文件污染"""
        found = set(_svg_files())
        self.assertEqual(
            len(found), 5,
            "design/ 下 SVG 文件数量应为 5，实际: %s" % sorted(found))
        self.assertSetEqual(found, EXPECTED_SVG_FILES)

    def test_svg_xml_well_formed(self):
        """每个文件均可被 ET.fromstring 解析，根标签为 svg（兼容命名空间）"""
        for name, root in self.roots.items():
            self.assertIsNotNone(root, "%s 解析结果为空" % name)
            self.assertTrue(
                root.tag.endswith("svg"),
                "%s 根标签应为 svg，实际: %s" % (name, root.tag))

    def test_viewbox_valid(self):
        """viewBox 为 0 0 500 500 或 0 0 1024 1024（宽高相等），width/height 比例一致"""
        for name, root in self.roots.items():
            self.assertTrue(
                _viewbox_ok(root),
                "%s viewBox 不合规: %s" % (name, root.get("viewBox")))
            self.assertTrue(
                _dimension_ok(root),
                "%s width/height 与 viewBox 比例不一致" % name)

    def test_self_contained(self):
        """无 image/link 元素、无 url( 外链（允许 url(#grad-...) 内联渐变）、无 @import、字体安全"""
        for name in sorted(EXPECTED_SVG_FILES):
            with open(os.path.join(DESIGN_DIR, name), "r", encoding="utf-8") as f:
                text = f.read()
            problems = _self_contained_problems(self.roots[name], text)
            self.assertEqual(
                problems, [],
                "%s 自包含检查未通过: %s" % (name, problems))

    def test_scroll_imagery_present(self):
        """每个文件存在 scroll- 开头的 <g> 卷轴分组（scroll-roll/body/ribbon 三组必含）"""
        for name, root in self.roots.items():
            ids = _scroll_groups(root)
            self.assertGreaterEqual(
                len(ids), 3,
                "%s scroll- 卷轴分组应 ≥3（roll/body/ribbon），实际: %s" % (name, ids))

    def test_color_count_controlled(self):
        """每个文件去重颜色数（fill/stroke 的 #/rgb/url(#渐变) 引用）≤ 8"""
        for name, root in self.roots.items():
            tokens = _collect_color_tokens(root)
            self.assertLessEqual(
                len(tokens), MAX_COLOR_COUNT,
                "%s 颜色数 %d 超过上限 %d: %s"
                % (name, len(tokens), MAX_COLOR_COUNT, sorted(tokens)))

    def test_palette_low_saturation(self):
        """每个文件全部颜色（fill/stroke hex/rgb + stop-color）∈ 二期 8 色板，任务1 色出现即失败"""
        for name, root in self.roots.items():
            ok, bad = _palette_ok(root)
            self.assertTrue(
                ok, "%s 存在色板外颜色: %s" % (name, bad))
            palette_tokens = _collect_palette_tokens(root)
            for color in FORBIDDEN_COLORS:
                self.assertNotIn(
                    color, palette_tokens,
                    "%s 出现任务1 高饱和违禁色 %s" % (name, color))

    def test_roll_size_ratio(self):
        """滚筒轴向厚度 T 与画幅宽 W 之比 ∈ [0.08, 0.14]（天/地杆 rect 高度 / 画幅主矩形宽度）"""
        for name, root in self.roots.items():
            t = _roll_thickness(root)
            w = _body_width(root)
            ratio = round(t / w, 6) if w > 0 else 0.0
            self.assertTrue(
                _roll_ratio_ok(root),
                "%s 滚筒比例 T/W=%.4f（T=%s, W=%s）不在 [0.08, 0.14]"
                % (name, ratio, t, w))
            # 打印供评审参考
            print("  [%s] T=%s W=%s T/W=%.4f" % (name, t, w, ratio))

    def test_kline_handdrawn_path(self):
        """K 线量化分组（id 含 kline 或 quant- 前缀）内至少存在 1 个 <path> 元素"""
        for name, root in self.roots.items():
            self.assertTrue(
                _kline_has_path(root),
                "%s K 线分组内缺少 <path> 手绘笔触元素（A9 不满足）" % name)


# ---------------------------------------------------------------------------
# 反案例
# ---------------------------------------------------------------------------
class TestLogoV2Negative(unittest.TestCase):
    """反案例：非法输入应被校验函数拒绝，验证测试逻辑自身有效性"""

    def setUp(self):
        """创建临时目录存放反案例 SVG 文件（严禁写入 design/ 目录）"""
        self.tmp_dir = tempfile.mkdtemp(prefix="logo_v2_neg_", dir=tempfile.gettempdir())

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
        """非 XML 文本（标签不闭合 / 纯文本）解析应抛 ET.ParseError"""
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
        """缺 viewBox 或 viewBox 为非允许尺寸/非法格式时，_viewbox_ok 应返回 False"""
        # 合法 XML 但缺 viewBox
        no_vb = self._write_svg(
            "no_viewbox.svg",
            '<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%"></svg>')
        self.assertFalse(_viewbox_ok(_parse_svg(no_vb)), "缺 viewBox 应校验失败")
        # viewBox 为非允许尺寸（300x300）
        wrong_vb = self._write_svg(
            "wrong_viewbox.svg",
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 300"></svg>')
        self.assertFalse(_viewbox_ok(_parse_svg(wrong_vb)), "非允许尺寸 viewBox 应校验失败")
        # viewBox 格式非法（仅 2 个数）
        bad_vb = self._write_svg(
            "bad_viewbox.svg",
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500"></svg>')
        self.assertFalse(_viewbox_ok(_parse_svg(bad_vb)), "格式非法的 viewBox 应校验失败")


# ---------------------------------------------------------------------------
# 边界案例
# ---------------------------------------------------------------------------
class TestLogoV2Boundary(unittest.TestCase):
    """边界案例：viewBox 尺寸 / 颜色数 / 色板 / 滚筒比例 阈值边界"""

    def setUp(self):
        """创建临时目录存放边界 SVG 文件（严禁写入 design/ 目录）"""
        self.tmp_dir = tempfile.mkdtemp(prefix="logo_v2_bnd_", dir=tempfile.gettempdir())

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
        return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="%s"></svg>' % vb

    def test_viewbox_boundary_sizes(self):
        """viewBox 恰为 500 与 1024 两个边界值时均通过，越界（501/1023）即失败"""
        # 两个允许尺寸下边界值应通过
        for vb in ("0 0 500 500", "0 0 1024 1024"):
            path = self._write_svg(
                "vb_%s.svg" % vb.replace(" ", "_"), self._svg_with_viewbox(vb))
            self.assertTrue(_viewbox_ok(_parse_svg(path)), "允许尺寸 %s 应通过校验" % vb)
        # 越界（宽高不等）应失败
        for vb in ("0 0 500 501", "0 0 1024 1023"):
            path = self._write_svg(
                "vb_%s.svg" % vb.replace(" ", "_"), self._svg_with_viewbox(vb))
            self.assertFalse(_viewbox_ok(_parse_svg(path)), "越界尺寸 %s 应校验失败" % vb)

    def _svg_with_n_colors(self, n):
        """构造恰好 n 种 fill 颜色的合法 SVG 文本（#000001 ~ #00000n）"""
        rects = "".join('<rect fill="#%06d"/>' % i for i in range(1, n + 1))
        return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 500">%s</svg>'
                % rects)

    def test_color_count_boundary(self):
        """颜色数恰为上限 8 时通过、9 时失败（阈值边界两侧）"""
        ok8 = self._write_svg("colors_8.svg", self._svg_with_n_colors(8))
        self.assertTrue(_color_ok(_parse_svg(ok8)), "恰好 8 种颜色应通过（上限边界内）")
        self.assertEqual(
            len(_collect_color_tokens(_parse_svg(ok8))), 8,
            "8 种颜色应全部被统计")
        bad9 = self._write_svg("colors_9.svg", self._svg_with_n_colors(9))
        self.assertFalse(_color_ok(_parse_svg(bad9)), "9 种颜色应校验失败（超出上限）")

    def test_palette_boundary(self):
        """色板恰 8 色板色通过；混入 1 个任务1 色（#B33A2E）失败；stop-color 越界亦失败"""
        # 恰用二期 8 色板的 8 个 rect → 应通过
        palette_rects = "".join(
            '<rect fill="%s"/>' % c for c in sorted(PALETTE))
        ok_svg = self._write_svg(
            "palette_ok.svg",
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 500">%s</svg>'
            % palette_rects)
        ok, bad = _palette_ok(_parse_svg(ok_svg))
        self.assertTrue(ok, "恰为二期 8 色板色应通过，实际违规: %s" % bad)
        self.assertEqual(len(_collect_palette_tokens(_parse_svg(ok_svg))), 8,
                         "8 色板色应全部被统计")
        # 混入 1 个任务1 高饱和色 #B33A2E → 应失败
        bad_colors = sorted(PALETTE)[:7] + ["#B33A2E"]
        bad_rects = "".join('<rect fill="%s"/>' % c for c in bad_colors)
        bad_svg = self._write_svg(
            "palette_bad.svg",
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 500">%s</svg>'
            % bad_rects)
        ok, bad = _palette_ok(_parse_svg(bad_svg))
        self.assertFalse(ok, "混入任务1 色 #B33A2E 应校验失败，实际违规: %s" % bad)
        self.assertIn("#b33a2e", bad)
        # 渐变 stop-color 越界（#264653 任务1 玄青）→ 必须被 A7 拦截
        grad_svg = self._write_svg(
            "palette_grad_bad.svg",
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 500">'
            '<defs><linearGradient id="g"><stop offset="0%%" stop-color="#264653"/>'
            '<stop offset="100%%" stop-color="#3B3733"/></linearGradient></defs>'
            '<rect fill="url(#g)"/></svg>')
        ok, bad = _palette_ok(_parse_svg(grad_svg))
        self.assertFalse(ok, "stop-color 越界（#264653）应校验失败，实际违规: %s" % bad)
        self.assertIn("#264653", bad)

    def _svg_with_roll(self, h, w=150):
        """构造 scroll-roll 滚筒 rect（height=h）+ scroll-body 画幅 rect（width=w）的 SVG"""
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 500">'
            '<g id="scroll-roll"><rect id="rod" width="160" height="%s"/></g>'
            '<g id="scroll-body"><rect id="panel" width="%s"/></g></svg>'
            % (h, w))

    def test_roll_ratio_boundary(self):
        """T/W 恰为 0.08 与 0.14 时通过、0.079/0.141 失败（阈值两侧）；path 口径亦正确"""
        # 下边界：H=12，12/150=0.08 → 通过；上边界：H=21，21/150=0.14 → 通过
        for h in (12, 21):
            path = self._write_svg("roll_%s.svg" % h, self._svg_with_roll(h))
            root = _parse_svg(path)
            self.assertEqual(_roll_thickness(root), float(h), "T 应取 rect 高度")
            self.assertEqual(_body_width(root), 150.0, "W 应取画幅 rect 宽度")
            self.assertTrue(_roll_ratio_ok(root),
                            "T/W=%.3f 恰为边界值应通过" % (float(h) / 150.0))
        # 阈值外侧：H=11.85（0.079）与 H=21.15（0.141）→ 失败
        for h in (11.85, 21.15):
            path = self._write_svg("roll_%s.svg" % h, self._svg_with_roll(h))
            self.assertFalse(
                _roll_ratio_ok(_parse_svg(path)),
                "T/W=%.3f 越界应校验失败" % (float(h) / 150.0))
        # path 滚筒口径：y 跨度 18 → 18/150=0.12 → 通过
        path_roll = self._write_svg(
            "roll_path.svg",
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 500">'
            '<g id="scroll-roll"><path d="M10,0 L160,0 L160,18 L10,18 Z"/></g>'
            '<g id="scroll-body"><rect id="panel" width="150"/></g></svg>')
        root = _parse_svg(path_roll)
        self.assertEqual(_path_y_span("M10,0 L160,0 L160,18 L10,18 Z"), 18.0,
                         "path 纵向跨度应解析为 18")
        self.assertEqual(_roll_thickness(root), 18.0, "path 滚筒 T 应取 y 跨度")
        self.assertTrue(_roll_ratio_ok(root), "path 口径 T/W=0.12 应通过")


# ---------------------------------------------------------------------------
# 结果输出（unit_test.md 第八节）
# ---------------------------------------------------------------------------
def run_tests():
    """执行全部测试，结果写入 unit_test/test/test_logo_svg_v2_result.txt 并生成 .gate.json"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestLogoV2Files))
    suite.addTests(loader.loadTestsFromTestCase(TestLogoV2Negative))
    suite.addTests(loader.loadTestsFromTestCase(TestLogoV2Boundary))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 确保输出目录存在
    test_result_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test")
    os.makedirs(test_result_dir, exist_ok=True)

    # 写入结果文件
    result_file = os.path.join(test_result_dir, "test_logo_svg_v2_result.txt")
    with open(result_file, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("test_logo_svg_v2 单元测试结果（河图Logo水墨优化）\n")
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

    # 写入 .gate.json（charter-gate 硬门禁文件，位于任务目录根）
    from datetime import datetime
    total = result.testsRun
    failed = len(result.failures) + len(result.errors)
    passed = total - failed
    gate = {
        "test_passed": result.wasSuccessful(),
        "test_file": "unit_test/test_logo_svg_v2.py",
        "result_file": "unit_test/test/test_logo_svg_v2_result.txt",
        "passed": passed,
        "failed": failed,
        "total": total,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }
    task_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    gate_path = os.path.join(task_dir, ".gate.json")
    with open(gate_path, "w", encoding="utf-8") as f:
        json.dump(gate, f, ensure_ascii=False, indent=2)
    print("门禁文件已生成: %s" % gate_path)
    print("门禁内容: %s" % json.dumps(gate, ensure_ascii=False))
    return result


if __name__ == "__main__":
    # 需要保存测试结果时用 run_tests()
    run_tests()
