# -*- coding: utf-8 -*-
"""
test_prompt_doc 单元测试
20260804任务3 河图Logo文生图提示词：提示词工程文档文本合规性单元测试

测试对象：design/河图Logo文生图提示词.md（markdown 文本内容断言，非 SVG/XML 断言）
覆盖范围（任务书第七节 + 实施计划 §3.2/§3.3，共 15 用例 = 正常 13 + 反例 1 + 边界 1）：
  - 正常案例 13 个：A1~A13 逐条落位（含 A11 敏感词零命中、A12 无 SVG/XML 产出、
                    A13 UTF-8 可读），见下方"A 类 → 用例名映射"；
  - 反案例    1 个：缺"负面提示词"章节 或 缺任一锚点词的临时 md 校验失败（A14，
                    验证测试逻辑自身有效性；锚点缺失原为边界用例，评审后并入反例）；
  - 边界案例  1 个：主提示词恰 100/500 字通过、99/501 字失败（四值四断言，A14/A15；
                    长度越界反例与边界合并，避免重复断言）。
反案例与边界案例均通过 tempfile 构造临时 md 验证（严格写临时目录、tearDown 清理），
严禁写入 design/ 目录，避免污染"无 SVG 产出"断言。

A 类 → 用例名映射（与任务书第七节 #1~15、实施计划 §3.3 表格一致）：
  A1  → test_doc_exists_not_empty       A9  → test_variants_3to5
  A2  → test_six_sections_present       A10 → test_usage_model_and_pitfalls
  A3  → test_four_element_anchors       A11 → test_no_sensitive_words
  A4  → test_main_prompt_length         A12 → test_no_svg_produced
  A5  → test_eight_segment_structure    A13 → test_utf8_readable
  A6  → test_negative_prompt_five_banned
  A7  → test_english_keywords
  A8  → test_params_ar_and_stylize
  A14 → test_reject_incomplete_doc（缺章节/缺锚点词两类断言）
  A14/A15 → test_length_boundary_100_500（99/501 失败、100/500 通过，四值四断言）

关键口径（任务书第七节 + 实施计划约定）：
  1. 章节提取：line.startswith("## ") 且 line[3:].startswith(标题前缀)；
     文内 ### 三级标题不会误切；
  2. 锚点/禁词匹配统一 re.IGNORECASE；K线/K 线/kline/k-line 多拼写兼容（代码内正则均用 raw 字符串）；
  3. 长度口径：去除全部空白字符后 len()，边界含；章节文本不含标题行（长度口径对应编码节点实测值）；
  4. 测试纯标准库（unittest/re/os/glob/tempfile/shutil），零外部依赖。
"""

import glob
import json
import os
import re
import shutil
import tempfile
import unittest

# ---------------------------------------------------------------------------
# 全局配置常量
# ---------------------------------------------------------------------------
# design/ 目录定位：本文件位于任务目录 unit_test/ 下，design 为其兄弟目录
DESIGN_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "design")
)
PROMPT_DOC = os.path.join(DESIGN_DIR, "河图Logo文生图提示词.md")

# 6 个必需章节标题前缀（A2，按前缀匹配，容忍"变体微调方向"等扩展命名）
REQUIRED_SECTIONS = (
    "主提示词", "英文提示词", "负面提示词", "参数建议", "变体", "使用说明",
)

# 主提示词 8 段结构段名（A5）
SEGMENT_NAMES = ("主体", "构图", "风格", "色彩", "质感", "光线", "细节", "质量词")

# 负面提示词 5 个指定禁词（A6）
BANNED_WORDS = ("text", "watermark", "3d", "photorealistic", "clutter")

# 使用说明模型适配关键词（A10，至少命中 2 项）
MODEL_KEYWORDS = ("Midjourney", "Stable Diffusion", "SD", "通义万相")
# 使用说明翻车规避关键词（A10，至少命中 1 项）
PITFALL_KEYWORDS = ("乱码", "拼贴", "风格不统一")

# 敏感词黑名单（A11，与正文用词零交集，见实施计划 §3.3）
SENSITIVE_BLACKLIST = (
    "色情", "淫秽", "暴力", "凶杀", "毒品", "军火", "赌博",
    "恐怖主义", "爆炸物", "枪支", "颠覆国家", "分裂国家",
)

# 主提示词长度边界（A4/A14/A15，去空白字符计，边界含）
MAIN_LEN_MIN = 100
MAIN_LEN_MAX = 500

# 变体数量区间（A9）
VARIANT_MIN = 3
VARIANT_MAX = 5


# ---------------------------------------------------------------------------
# 模块级纯函数（供正常 / 反案例 / 边界案例直接调用，验证测试逻辑自身有效性）
# ---------------------------------------------------------------------------
def _read_doc(path: str) -> str:
    """UTF-8 读取文档全文；文件不存在或解码失败时抛异常"""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _extract_section(text: str, title: str) -> str:
    """按 '## 标题前缀' 切出章节正文（至下一个 '## ' 前，不含标题行）

    口径：仅匹配 line.startswith("## ") 的二级标题；### 三级标题不会误切；
    标题支持前缀匹配（如 title="变体" 匹配"变体微调方向"）；
    返回正文不含标题行，保证长度用例可用纯字符精确控长（标题行字符不混入统计）。
    """
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.startswith("## ") and line[3:].startswith(title):
            start = i
            break
    if start is None:
        return ""
    out = []
    for line in lines[start + 1:]:
        if line.startswith("## "):
            break
        out.append(line)
    return "\n".join(out)


def _check_sections(text: str) -> bool:
    """校验 6 个必需章节标题（## 前缀匹配）是否全部出现"""
    found = set()
    for line in text.splitlines():
        if line.startswith("## "):
            for title in REQUIRED_SECTIONS:
                if line[3:].startswith(title):
                    found.add(title)
    return found == set(REQUIRED_SECTIONS)


def _check_anchors(main_text: str) -> bool:
    """校验 6 组必需要素锚点全部命中（实施计划 §3.2，统一 re.IGNORECASE）

    AND 关系：横向+卷轴/画卷/横卷；(曲折|蜿蜒|折返)+(向上|上行|上扬|攀升)；
             红色+箭头。OR 关系：K线|K 线|kline|k-line；水墨；极简。
    """
    def hit_any(patterns):
        """任一正则命中即返回 True"""
        return any(re.search(p, main_text, re.IGNORECASE) for p in patterns)

    # 1 横向卷轴画卷：横向 AND (卷轴|画卷|横卷)
    if not (hit_any(["横向"]) and hit_any(["卷轴", "画卷", "横卷"])):
        return False
    # 2 K 线图：K线|K\s*线|kline|k-line
    if not hit_any([r"K线", r"K\s*线", "kline", "k-line"]):
        return False
    # 3 曲折向上：(曲折|蜿蜒|折返) AND (向上|上行|上扬|攀升)
    if not (hit_any(["曲折", "蜿蜒", "折返"])
            and hit_any(["向上", "上行", "上扬", "攀升"])):
        return False
    # 4 红色箭头：红色 AND 箭头
    if not (hit_any(["红色"]) and hit_any(["箭头"])):
        return False
    # 5 水墨：必须命中
    if not hit_any(["水墨"]):
        return False
    # 6 极简：必须命中
    if not hit_any(["极简"]):
        return False
    return True


def _main_length_ok(main_text: str) -> bool:
    """校验主提示词章节去空白后长度 ∈ [100, 500]（中文按字符计，边界含）"""
    stripped = re.sub(r"\s", "", main_text)
    return MAIN_LEN_MIN <= len(stripped) <= MAIN_LEN_MAX


def _check_8segments(main_text: str) -> bool:
    """校验主提示词章节内 8 个段名（主体/构图/风格/色彩/质感/光线/细节/质量词）全部出现"""
    return all(seg in main_text for seg in SEGMENT_NAMES)


def _check_negative(neg_text: str) -> bool:
    """校验负面提示词小写化后同时含 5 个指定禁词"""
    low = neg_text.lower()
    return all(word in low for word in BANNED_WORDS)


def _check_english(en_text: str) -> bool:
    """校验英文提示词：scroll 与 arrow 必含；k-line/kline/candlestick、ink、minimalist 至少 1 项"""
    if not en_text:
        return False
    if not re.search("scroll", en_text, re.IGNORECASE):
        return False
    if not re.search("arrow", en_text, re.IGNORECASE):
        return False
    extras = ("k-line", "kline", "candlestick", "ink", "minimalist")
    if not any(re.search(w, en_text, re.IGNORECASE) for w in extras):
        return False
    return True


def _check_params(param_text: str) -> bool:
    """校验参数章节：宽高比（--ar 或 1:1/2:3/16:9 任一）且风格权重（--stylize 或 stylize）"""
    if not re.search(r"--ar|1:1|2:3|16:9", param_text):
        return False
    if not re.search(r"--stylize|stylize", param_text, re.IGNORECASE):
        return False
    return True


def _check_variants(var_text: str) -> bool:
    """校验变体：变体标记数量 ∈ [3,5]，且每个变体小节含片段引导词（片段/提示词/追加 至少其一）"""
    markers = set(re.findall(r"变体[1-5]|①|②|③|④|⑤", var_text))
    if not (VARIANT_MIN <= len(markers) <= VARIANT_MAX):
        return False
    blocks = re.split(r"###\s*", var_text)
    variant_blocks = [b for b in blocks if re.match(r"变体[1-5]", b.strip())]
    if len(variant_blocks) != len(markers):
        return False
    for block in variant_blocks:
        if not re.search(r"片段|提示词|追加", block):
            return False
    return True


def _check_usage(use_text: str) -> bool:
    """校验使用说明：模型适配关键词 ≥2 项，且翻车规避关键词 ≥1 项"""
    model_hits = sum(
        1 for m in MODEL_KEYWORDS if re.search(re.escape(m), use_text, re.IGNORECASE))
    if model_hits < 2:
        return False
    if not re.search("|".join(PITFALL_KEYWORDS), use_text):
        return False
    return True


def _check_sensitive(text: str, blacklist) -> bool:
    """校验全文黑名单敏感词零命中（小写化后子串扫描）"""
    low = text.lower()
    return not any(word in low for word in blacklist)


def _no_svg_files(design_dir: str) -> bool:
    """校验 design/ 目录（含子目录递归）下无任何 .svg / .xml 文件"""
    svg_files = glob.glob(os.path.join(design_dir, "**", "*.svg"), recursive=True)
    xml_files = glob.glob(os.path.join(design_dir, "**", "*.xml"), recursive=True)
    return len(svg_files) == 0 and len(xml_files) == 0


def _utf8_readable(path: str) -> bool:
    """校验文档 UTF-8 解码无异常且不含 \ufffd 替换字符"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except (OSError, UnicodeDecodeError):
        return False
    return "\ufffd" not in text


def _make_temp_doc(main_body: str) -> str:
    """构造最小文档模板：'## 主提示词' + 主提示词正文（供反例/边界长度用例）"""
    return "## 主提示词\n\n%s\n" % main_body


# ---------------------------------------------------------------------------
# 正常案例
# ---------------------------------------------------------------------------
class TestPromptDocNormal(unittest.TestCase):
    """正常案例：对 design/ 下真实提示词交付物的文本合规性断言"""

    @classmethod
    def setUpClass(cls):
        """一次性读取交付物文档全文，供全部正常用例共享（不存在时为 None）"""
        cls.full_text = None
        if os.path.exists(PROMPT_DOC):
            cls.full_text = _read_doc(PROMPT_DOC)

    def test_doc_exists_not_empty(self):
        """交付物存在且非空：文件存在、可读、内容长度 > 0（A1）"""
        self.assertTrue(os.path.exists(PROMPT_DOC), "交付物不存在: %s" % PROMPT_DOC)
        self.assertTrue(os.path.isfile(PROMPT_DOC), "交付物路径不是文件: %s" % PROMPT_DOC)
        self.assertIsNotNone(self.full_text, "交付物无法读取")
        self.assertGreater(len(self.full_text), 0, "交付物内容为空")

    def test_six_sections_present(self):
        """6 个必需章节齐全：主提示词/英文提示词/负面提示词/参数建议/变体/使用说明（A2）"""
        self.assertIsNotNone(self.full_text, "交付物无法读取")
        self.assertTrue(_check_sections(self.full_text), "6 个必需章节标题未全部出现")

    def test_four_element_anchors(self):
        """中文主提示词 6 组锚点全部命中：横向卷轴画卷/K线/曲折向上/红色箭头/水墨/极简（A3）"""
        self.assertIsNotNone(self.full_text, "交付物无法读取")
        main_text = _extract_section(self.full_text, "主提示词")
        self.assertTrue(main_text, "主提示词章节提取为空")
        self.assertTrue(_check_anchors(main_text), "6 组必需要素锚点未全部命中")

    def test_main_prompt_length(self):
        """主提示词章节去空白后长度 ∈ [100, 500]（A4）"""
        self.assertIsNotNone(self.full_text, "交付物无法读取")
        main_text = _extract_section(self.full_text, "主提示词")
        self.assertTrue(_main_length_ok(main_text),
                        "主提示词去空白长度不在 [100, 500] 区间")
        print("  [主提示词] 去空白长度: %d" % len(re.sub(r"\s", "", main_text)))

    def test_eight_segment_structure(self):
        """主提示词 8 段结构齐全：主体/构图/风格/色彩/质感/光线/细节/质量词（A5）"""
        self.assertIsNotNone(self.full_text, "交付物无法读取")
        main_text = _extract_section(self.full_text, "主提示词")
        self.assertTrue(_check_8segments(main_text), "8 个段名未全部出现")

    def test_negative_prompt_five_banned(self):
        """负面提示词章节小写化后同时含 5 个禁词：text/watermark/3d/photorealistic/clutter（A6）"""
        self.assertIsNotNone(self.full_text, "交付物无法读取")
        neg_text = _extract_section(self.full_text, "负面提示词")
        self.assertTrue(neg_text, "负面提示词章节提取为空")
        self.assertTrue(_check_negative(neg_text), "5 个指定禁词未全部命中")

    def test_english_keywords(self):
        """英文提示词章节含 scroll 与 arrow；k-line/kline/candlestick、ink、minimalist 至少 1 项（A7）"""
        self.assertIsNotNone(self.full_text, "交付物无法读取")
        en_text = _extract_section(self.full_text, "英文提示词")
        self.assertTrue(_check_english(en_text), "英文关键词校验未通过")

    def test_params_ar_and_stylize(self):
        """参数建议章节含宽高比（--ar 或 1:1/2:3/16:9 任一）与风格权重（--stylize 或 stylize）（A8）"""
        self.assertIsNotNone(self.full_text, "交付物无法读取")
        param_text = _extract_section(self.full_text, "参数建议")
        self.assertTrue(param_text, "参数建议章节提取为空")
        self.assertTrue(_check_params(param_text), "参数建议（宽高比/风格权重）校验未通过")

    def test_variants_3to5(self):
        """变体方向数量 ∈ [3,5]，且每个变体小节含替换/追加片段引导词（A9）"""
        self.assertIsNotNone(self.full_text, "交付物无法读取")
        var_text = _extract_section(self.full_text, "变体")
        self.assertTrue(var_text, "变体章节提取为空")
        markers = set(re.findall(r"变体[1-5]|①|②|③|④|⑤", var_text))
        print("  [变体] 标记数: %d" % len(markers))
        self.assertTrue(_check_variants(var_text), "变体数量或片段引导词校验未通过")

    def test_usage_model_and_pitfalls(self):
        """使用说明章节含模型适配（≥2 模型）与翻车规避（乱码/拼贴/风格不统一 ≥1）（A10）"""
        self.assertIsNotNone(self.full_text, "交付物无法读取")
        use_text = _extract_section(self.full_text, "使用说明")
        self.assertTrue(use_text, "使用说明章节提取为空")
        self.assertTrue(_check_usage(use_text), "使用说明（模型适配/翻车规避）校验未通过")

    def test_no_sensitive_words(self):
        """全文敏感词黑名单零命中：暴力/色情/政治敏感等黑名单词零出现（A11）"""
        self.assertIsNotNone(self.full_text, "交付物无法读取")
        self.assertTrue(_check_sensitive(self.full_text, SENSITIVE_BLACKLIST),
                        "全文出现黑名单敏感词（色情/暴力/政治敏感等）")

    def test_no_svg_produced(self):
        """design/ 下无任何 .svg/.xml 文件（glob 递归校验；本任务为纯文档任务，A12）"""
        self.assertTrue(os.path.isdir(DESIGN_DIR), "design/ 目录不存在: %s" % DESIGN_DIR)
        self.assertTrue(_no_svg_files(DESIGN_DIR),
                        "design/ 下不应存在 SVG/XML 文件")

    def test_utf8_readable(self):
        """文档 UTF-8 解码无异常且不含 \ufffd 替换字符（A13）"""
        self.assertTrue(_utf8_readable(PROMPT_DOC),
                        "文档含乱码（\\ufffd 替换字符）或无法按 UTF-8 解码")


# ---------------------------------------------------------------------------
# 反案例
# ---------------------------------------------------------------------------
class TestPromptDocNegative(unittest.TestCase):
    """反案例：非法文档应被校验函数拒绝，验证测试逻辑自身有效性"""

    def setUp(self):
        """创建临时目录存放反案例 md 文件（严禁写入 design/ 目录）"""
        self.tmp_dir = tempfile.mkdtemp(prefix="prompt_doc_neg_", dir=tempfile.gettempdir())

    def tearDown(self):
        """清理临时目录"""
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _write_temp(self, name, content):
        """将内容写入临时目录并返回路径"""
        path = os.path.join(self.tmp_dir, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_reject_incomplete_doc(self):
        """缺必需要素的临时 md → 校验函数返回 False（A14，验证测试逻辑自身有效性）

        两类子断言：
        1) 缺"负面提示词"章节 → _check_sections 返回 False；
        2) 缺任一锚点词（横向/卷轴/K线/曲折/向上/红色/箭头/水墨/极简）→
           _check_anchors 返回 False（6 锚点全覆盖逻辑的缺失边界，原独立边界用例，
           评审后并入反例以保持任务书 15 用例口径）。
        对照：锚点完整的临时文档应通过（锚点逻辑不依赖真实文档其他特性）。
        """
        # 1) 缺"负面提示词"章节
        full = _read_doc(PROMPT_DOC)
        broken = re.sub(r"## 负面提示词.*?(?=## )", "## （负面章节已删除）\n", full, flags=re.S)
        text = _read_doc(self._write_temp("missing_neg.md", broken))
        self.assertFalse(_check_sections(text), "缺'负面提示词'章节应校验失败")
        # 2) 缺任一锚点词
        real_main = _extract_section(_read_doc(PROMPT_DOC), "主提示词")
        self.assertTrue(real_main, "真实主提示词章节提取为空")
        cases = (
            ("横向", r"横向"),
            ("卷轴|画卷|横卷", r"卷轴|画卷|横卷"),
            ("K线/K 线/kline/k-line", r"K\s*线|kline|k-line"),
            ("曲折|蜿蜒|折返", r"曲折|蜿蜒|折返"),
            ("向上|上行|上扬|攀升", r"向上|上行|上扬|攀升"),
            ("红色", r"红色"),
            ("箭头", r"箭头"),
            ("水墨", r"水墨"),
            ("极简", r"极简"),
        )
        for name, pattern in cases:
            broken_main = re.sub(pattern, "", real_main, flags=re.IGNORECASE)
            doc = _make_temp_doc(broken_main)
            main_text = _extract_section(doc, "主提示词")
            self.assertFalse(_check_anchors(main_text),
                             "缺失锚点词 %s 后校验应失败" % name)
        # 对照：未删任何锚点的临时文档应通过
        ok_doc = _make_temp_doc(real_main)
        self.assertTrue(_check_anchors(_extract_section(ok_doc, "主提示词")),
                        "锚点完整的临时文档应通过校验")


# ---------------------------------------------------------------------------
# 边界案例
# ---------------------------------------------------------------------------
class TestPromptDocBoundary(unittest.TestCase):
    """边界案例：主提示词长度阈值两侧（100/500 含边界通过，99/501 越界失败）

    锚点缺失边界已并入反例类 test_reject_incomplete_doc（A14），保持 15 用例口径。
    """

    def setUp(self):
        """创建临时目录存放边界 md 文件（严禁写入 design/ 目录）"""
        self.tmp_dir = tempfile.mkdtemp(prefix="prompt_doc_bnd_", dir=tempfile.gettempdir())

    def tearDown(self):
        """清理临时目录"""
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _write_temp(self, name, content):
        """将内容写入临时目录并返回路径"""
        path = os.path.join(self.tmp_dir, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_length_boundary_100_500(self):
        """主提示词恰 100 字 / 恰 500 字均通过，99 / 501 字失败（边界含，四值四断言，A14/A15）"""
        for n in (100, 500):
            path = self._write_temp("len_ok_%d.md" % n, _make_temp_doc("墨" * n))
            main_text = _extract_section(_read_doc(path), "主提示词")
            self.assertTrue(_main_length_ok(main_text),
                            "恰 %d 字主提示词应通过长度校验" % n)
        for n in (99, 501):
            path = self._write_temp("len_bad_%d.md" % n, _make_temp_doc("墨" * n))
            main_text = _extract_section(_read_doc(path), "主提示词")
            self.assertFalse(_main_length_ok(main_text),
                             "%d 字主提示词应失败（越界）" % n)


# ---------------------------------------------------------------------------
# 结果输出（unit_test.md 第八节）
# ---------------------------------------------------------------------------
def run_tests():
    """执行全部测试，结果写入 unit_test/test/test_prompt_doc_result.txt 并生成 .gate.json"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestPromptDocNormal))
    suite.addTests(loader.loadTestsFromTestCase(TestPromptDocNegative))
    suite.addTests(loader.loadTestsFromTestCase(TestPromptDocBoundary))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 确保输出目录存在
    test_result_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test")
    os.makedirs(test_result_dir, exist_ok=True)

    # 写入结果文件
    result_file = os.path.join(test_result_dir, "test_prompt_doc_result.txt")
    with open(result_file, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("test_prompt_doc 单元测试结果（河图Logo文生图提示词）\n")
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
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    gate = {
        "test_passed": result.wasSuccessful(),
        "test_file": "unit_test/test_prompt_doc.py",
        "result_file": "unit_test/test/test_prompt_doc_result.txt",
        "passed": passed,
        "failed": failed,
        "total": total,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "updated_at": now,
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
