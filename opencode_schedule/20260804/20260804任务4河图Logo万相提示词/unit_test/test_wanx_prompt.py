# -*- coding: utf-8 -*-
"""
test_wanx_prompt 单元测试
20260804任务4 河图Logo万相提示词：万相专属提示词文档文本合规性单元测试

测试对象：design/河图Logo万相提示词.md（markdown 文本内容断言，非 SVG/XML 断言）
覆盖范围（任务书第七节 + 实施计划 §四，共 15 用例 = 正常 13 + 反例 1 + 边界 1）：
  - 正常案例 13 个：A1~A13 逐条落位（含 A12 敏感词零命中 + UTF-8 无 \ufffd、
                    A13 无 SVG/XML 产出），见下方"A 类 → 用例名映射"；
  - 反案例    1 个：缺 color_palette hex / ratio 求和≠100 / 删任一锚点词的
                    临时文档校验失败（A14，验证测试逻辑自身有效性），含完整对照；
  - 边界案例  1 个：主提示词恰 200/800 字通过、199/801 字失败（四值四断言，A15）。
反案例与边界案例均通过 tempfile 构造临时 md 验证（严格写临时目录、tearDown 清理），
严禁写入 design/ 目录，避免污染"无 SVG 产出"断言。

A 类 → 用例名映射（与任务书第七节 #1~15 一致）：
  A1  → test_doc_exists_not_empty       A9  → test_negative_handling
  A2  → test_six_sections_present       A10 → test_variants_3_with_size
  A3  → test_anchors_covered            A11 → test_feeding_dual_channel
  A4  → test_main_prompt_length         A12 → test_no_sensitive_utf8
  A5  → test_model_wanx                 A13 → test_no_svg_produced
  A6  → test_size_format                A14 → test_reject_invalid_palette
  A7  → test_thinking_and_extend        A15 → test_length_boundary
  A8  → test_color_palette_8colors_ratio100

关键口径（任务书第七节 + 实施计划 §四约定，复用任务3 test_prompt_doc.py 口径）：
  1. 章节提取：line.startswith("## ") 且 line[3:].startswith(标题前缀)；
     文内 ### 三级标题不会误切；标题支持前缀匹配（"万相参数"匹配"万相参数配置"）；
  2. 锚点/参数词匹配统一 re.IGNORECASE；K线/K 线/kline/k-line 多拼写兼容
     （6 组锚点正则完全复用任务3 口径）；
  3. 长度口径：去除全部空白字符后 len()，边界含 [200,800]；章节文本不含标题行
     （编码节点实测主提示词章节 552 字、正文 450 字，均在安全区）；
  4. color_palette：8 个二期低饱和 hex 全含（大小写不敏感）且真实解析 ratio
     数值求和 == 100（正则 re.findall(r'ratio["\']?\\s*[:：]\\s*(\\d+)')），
     而非仅匹配"100%"字样，保证反例②（ratio≠100）能够失效；
  5. 测试纯标准库（unittest/re/os/glob/tempfile/shutil），零外部依赖。
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
WANX_DOC = os.path.join(DESIGN_DIR, "河图Logo万相提示词.md")

# 6 个必需章节标题前缀（A2，按前缀匹配，容忍"万相参数配置"等扩展命名）
REQUIRED_SECTIONS = (
    "主提示词", "万相参数", "负面", "变体", "投喂", "翻车",
)

# 二期低饱和 8 色板 hex（A8，直接映射万相 color_palette，大小写不敏感）
COLOR_PALETTE_HEX = (
    "#F3E9D6", "#3B3733", "#57504A", "#8D8578",
    "#B7AFA2", "#4E5D66", "#A96B5F", "#A9976B",
)

# 敏感词黑名单（A12，与正文用词零交集，沿用任务3 口径）
SENSITIVE_BLACKLIST = (
    "色情", "淫秽", "暴力", "凶杀", "毒品", "军火", "赌博",
    "恐怖主义", "爆炸物", "枪支", "颠覆国家", "分裂国家",
)

# 主提示词长度边界（A4/A14/A15，去空白字符计，边界含）
MAIN_LEN_MIN = 200
MAIN_LEN_MAX = 800

# 变体数量区间（A10）
VARIANT_MIN = 2
VARIANT_MAX = 3


# ---------------------------------------------------------------------------
# 模块级纯函数（供正常 / 反案例 / 边界案例直接调用，验证测试逻辑自身有效性）
# ---------------------------------------------------------------------------
def _read_doc(path: str) -> str:
    """UTF-8 读取文档全文；文件不存在或解码失败时抛异常"""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _extract_section(text: str, title: str) -> str:
    """按 '## 标题前缀' 切出章节正文（至下一个 '## ' 前，不含标题行）

    口径（复用任务3）：仅匹配 line.startswith("## ") 的二级标题；### 三级标题
    不会误切；标题支持前缀匹配（如 title="万相参数" 匹配"## 万相参数配置"）；
    返回正文不含标题行，保证长度用例可用纯字符精确控长。
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
    """校验 6 个必需章节标题（## 前缀匹配）是否全部出现（A2）"""
    found = set()
    for line in text.splitlines():
        if line.startswith("## "):
            for title in REQUIRED_SECTIONS:
                if line[3:].startswith(title):
                    found.add(title)
    return found == set(REQUIRED_SECTIONS)


def _check_anchors(main_text: str) -> bool:
    """校验 6 组必需要素锚点全部命中（复用任务3 口径，统一 re.IGNORECASE）

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
    """校验主提示词章节去空白后长度 ∈ [200, 800]（中文按字符计，边界含，A4/A15）"""
    stripped = re.sub(r"\s", "", main_text)
    return MAIN_LEN_MIN <= len(stripped) <= MAIN_LEN_MAX


def _check_model(param_text: str) -> bool:
    """校验模型选型：参数章节含 wan2.7-image-pro（主推）与 wan2.6-t2i（备选），
    且 wan2.7-image-pro 所在行含"主推/旗舰"主推语义（A5）"""
    low = param_text.lower()
    if "wan2.7-image-pro" not in low:
        return False
    if "wan2.6-t2i" not in low:
        return False
    for line in param_text.splitlines():
        if "wan2.7-image-pro" in line.lower() and re.search(r"主推|旗舰", line):
            return True
    return False


def _check_size(param_text: str) -> bool:
    """校验 size 参数合规：含"宽*高"星号格式说明，且给出 16:9/1:1 任一建议值（A6）"""
    if not re.search(r"2688\*1536|2048\*2048|4096\*2304", param_text):
        return False
    # "宽*高" / "宽×高" 格式说明（星号或乘号分隔）
    if not re.search(r"宽\s*[＊*×]\s*高", param_text):
        return False
    return True


def _check_thinking(param_text: str) -> bool:
    """校验 thinking_mode / prompt_extend 描述正确（A7）：
    - thinking_mode 与 wan2.7、true 同段（默认 true，仅 wan2.7 系列）；
    - prompt_extend 与"不支持"同段（wan2.7 系列不支持 → 显式 false 或不传）。
    """
    low = param_text.lower()
    if "thinking_mode" not in low:
        return False
    if "prompt_extend" not in low:
        return False
    lines = param_text.splitlines()
    # thinking_mode 表述：wan2.7 与 true 同段（同行/同 markdown 段落）
    if not any("wan2.7" in ln.lower() and "true" in ln.lower() for ln in lines):
        return False
    # prompt_extend 表述：与"不支持"同段
    if not any("prompt_extend" in ln.lower() and "不支持" in ln for ln in lines):
        return False
    return True


def _check_color_palette(param_text: str) -> bool:
    """校验 color_palette 合规（A8）：
    1) 8 个二期低饱和 hex 全含（大小写不敏感）；
    2) 真实解析 ratio 数值求和 == 100——re.findall(r'ratio["\']?\\s*[:：]\\s*(\\d+)')
       提取文档中所有 ratio 数值列表求和，必须数值校验而非仅匹配"100%"字样
       （否则反例② ratio≠100 无法失效）。
    """
    low = param_text.lower()
    if not all(h.lower() in low for h in COLOR_PALETTE_HEX):
        return False
    ratios = [int(v) for v in re.findall(r'ratio["\']?\s*[:：]\s*(\d+)', param_text)]
    return sum(ratios) == 100


def _check_negative_handling(neg_text: str) -> bool:
    """校验负面要素处理正确（A9）：negative_prompt 与"不支持"同段出现，
    且给出正向写法"不要出现"句式"""
    if "不要出现" not in neg_text:
        return False
    if "negative_prompt" not in neg_text.lower():
        return False
    for line in neg_text.splitlines():
        if "negative_prompt" in line.lower() and "不支持" in line:
            return True
    return False


def _check_variants_wanx(var_text: str) -> bool:
    """校验变体章节（A10）：变体标记（变体[A-C]|变体[1-3]）数量 ∈ [2,3]，
    各变体小节含片段/追加引导词，且章节内含 size 配套值（2688*1536|2048*2048 至少一处）"""
    markers = set(re.findall(r"变体[1-3]|变体[A-C]|①|②|③", var_text))
    if not (VARIANT_MIN <= len(markers) <= VARIANT_MAX):
        return False
    blocks = re.split(r"###\s*", var_text)
    variant_blocks = [b for b in blocks if re.match(r"变体[1-3]|变体[A-C]", b.strip())]
    if len(variant_blocks) != len(markers):
        return False
    for block in variant_blocks:
        if not re.search(r"片段|提示词|追加", block):
            return False
    if not re.search(r"2688\*1536|2048\*2048", var_text):
        return False
    return True


def _check_feeding(feed_text: str) -> bool:
    """校验投喂步骤双通道（A11）：API 方式（messages 或 input.prompt 任一）
    与百炼控制台方式（控制台 或 百炼 任一）"""
    low = feed_text.lower()
    api_ok = ("messages" in low) or ("input.prompt" in low)
    console_ok = ("控制台" in feed_text) or ("百炼" in feed_text)
    return api_ok and console_ok


def _check_sensitive(text: str, blacklist) -> bool:
    """校验全文黑名单敏感词零命中（小写化后子串扫描，复用任务3 口径）"""
    low = text.lower()
    return not any(word in low for word in blacklist)


def _no_svg_files(design_dir: str) -> bool:
    """校验 design/ 目录（含子目录递归）下无任何 .svg / .xml 文件（复用任务3 口径）"""
    svg_files = glob.glob(os.path.join(design_dir, "**", "*.svg"), recursive=True)
    xml_files = glob.glob(os.path.join(design_dir, "**", "*.xml"), recursive=True)
    return len(svg_files) == 0 and len(xml_files) == 0


def _utf8_readable(path: str) -> bool:
    """校验文档 UTF-8 解码无异常且不含 \ufffd 替换字符（复用任务3 口径）"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except (OSError, UnicodeDecodeError):
        return False
    return "\ufffd" not in text


def _make_temp_doc(main_body: str) -> str:
    """构造最小文档模板：'## 主提示词' + 主提示词正文（供反例/边界长度用例）"""
    return "## 主提示词\n\n%s\n" % main_body


def _make_temp_param_doc(param_body: str) -> str:
    """构造最小参数文档模板：'## 万相参数配置' + 参数正文（供色板反例用例）"""
    return "## 万相参数配置\n\n%s\n" % param_body


# ---------------------------------------------------------------------------
# 正常案例
# ---------------------------------------------------------------------------
class TestWanxPromptNormal(unittest.TestCase):
    """正常案例：对 design/ 下真实万相提示词交付物的文本合规性断言（A1~A13）"""

    @classmethod
    def setUpClass(cls):
        """一次性读取交付物文档全文，供全部正常用例共享（不存在时为 None）"""
        cls.full_text = None
        if os.path.exists(WANX_DOC):
            cls.full_text = _read_doc(WANX_DOC)

    def test_doc_exists_not_empty(self):
        """交付物存在且非空：文件存在、可读、内容长度 > 0（A1）"""
        self.assertTrue(os.path.exists(WANX_DOC), "交付物不存在: %s" % WANX_DOC)
        self.assertTrue(os.path.isfile(WANX_DOC), "交付物路径不是文件: %s" % WANX_DOC)
        self.assertIsNotNone(self.full_text, "交付物无法读取")
        self.assertGreater(len(self.full_text), 0, "交付物内容为空")

    def test_six_sections_present(self):
        """6 个必需章节齐全：主提示词/万相参数/负面/变体/投喂/翻车（A2）"""
        self.assertIsNotNone(self.full_text, "交付物无法读取")
        self.assertTrue(_check_sections(self.full_text), "6 个必需章节标题未全部出现")

    def test_anchors_covered(self):
        """中文主提示词 6 组锚点全部命中：横向卷轴画卷/K线/曲折向上/红色箭头/水墨/极简（A3）"""
        self.assertIsNotNone(self.full_text, "交付物无法读取")
        main_text = _extract_section(self.full_text, "主提示词")
        self.assertTrue(main_text, "主提示词章节提取为空")
        self.assertTrue(_check_anchors(main_text), "6 组必需要素锚点未全部命中")

    def test_main_prompt_length(self):
        """主提示词章节去空白后长度 ∈ [200, 800]（边界含，A4）"""
        self.assertIsNotNone(self.full_text, "交付物无法读取")
        main_text = _extract_section(self.full_text, "主提示词")
        self.assertTrue(_main_length_ok(main_text),
                        "主提示词去空白长度不在 [200, 800] 区间")
        print("  [主提示词] 去空白长度: %d" % len(re.sub(r"\s", "", main_text)))

    def test_model_wanx(self):
        """模型选型准确：参数章节含 wan2.7-image-pro（主推语义）与 wan2.6-t2i（备选）（A5）"""
        self.assertIsNotNone(self.full_text, "交付物无法读取")
        param_text = _extract_section(self.full_text, "万相参数")
        self.assertTrue(param_text, "万相参数章节提取为空")
        self.assertTrue(_check_model(param_text), "模型选型（主推 wan2.7-image-pro / 备选 wan2.6-t2i）校验未通过")

    def test_size_format(self):
        """size 参数合规：含"宽*高"星号格式说明与建议值（2688*1536/2048*2048/4096*2304 任一）（A6）"""
        self.assertIsNotNone(self.full_text, "交付物无法读取")
        param_text = _extract_section(self.full_text, "万相参数")
        self.assertTrue(param_text, "万相参数章节提取为空")
        self.assertTrue(_check_size(param_text), "size 参数（宽*高格式/建议值）校验未通过")

    def test_thinking_and_extend(self):
        """thinking_mode/prompt_extend 语义正确：thinking_mode 默认 true 仅 wan2.7；
        prompt_extend 标注 wan2.7 不支持（A7）"""
        self.assertIsNotNone(self.full_text, "交付物无法读取")
        param_text = _extract_section(self.full_text, "万相参数")
        self.assertTrue(param_text, "万相参数章节提取为空")
        self.assertTrue(_check_thinking(param_text), "thinking_mode/prompt_extend 语义校验未通过")

    def test_color_palette_8colors_ratio100(self):
        """color_palette 8 个二期 hex 全含（大小写不敏感）且真实解析 ratio 求和 == 100（A8）"""
        self.assertIsNotNone(self.full_text, "交付物无法读取")
        param_text = _extract_section(self.full_text, "万相参数")
        self.assertTrue(param_text, "万相参数章节提取为空")
        ratios = [int(v) for v in re.findall(r'ratio["\']?\s*[:：]\s*(\d+)', param_text)]
        print("  [color_palette] 解析 ratio 列表: %s 求和: %d" % (ratios, sum(ratios)))
        self.assertTrue(_check_color_palette(param_text),
                        "color_palette 8 色未全含或 ratio 求和 != 100")

    def test_negative_handling(self):
        """负面要素处理正确：negative_prompt 与"不支持"同段，且含"不要出现"正向句式（A9）"""
        self.assertIsNotNone(self.full_text, "交付物无法读取")
        neg_text = _extract_section(self.full_text, "负面")
        self.assertTrue(neg_text, "负面要素处理章节提取为空")
        self.assertTrue(_check_negative_handling(neg_text),
                        "负面要素处理（不支持 negative_prompt + 不要出现句式）校验未通过")

    def test_variants_3_with_size(self):
        """变体章节 3 个变体（变体[A-C]/变体[1-3]）各含片段/追加引导词与 size 配套值（A10）"""
        self.assertIsNotNone(self.full_text, "交付物无法读取")
        var_text = _extract_section(self.full_text, "变体")
        self.assertTrue(var_text, "变体章节提取为空")
        markers = set(re.findall(r"变体[1-3]|变体[A-C]|①|②|③", var_text))
        print("  [变体] 标记数: %d" % len(markers))
        self.assertTrue(_check_variants_wanx(var_text), "变体数量/片段引导词/size 配套校验未通过")

    def test_feeding_dual_channel(self):
        """投喂步骤双通道：API 方式（messages/input.prompt）与控制台方式（控制台/百炼）（A11）"""
        self.assertIsNotNone(self.full_text, "交付物无法读取")
        feed_text = _extract_section(self.full_text, "投喂")
        self.assertTrue(feed_text, "投喂步骤章节提取为空")
        self.assertTrue(_check_feeding(feed_text), "投喂步骤（API + 控制台双通道）校验未通过")

    def test_no_sensitive_utf8(self):
        """全文敏感词黑名单零命中（暴力/色情/政治敏感等）且 UTF-8 无 \ufffd 替换字符（A12）"""
        self.assertIsNotNone(self.full_text, "交付物无法读取")
        self.assertTrue(_check_sensitive(self.full_text, SENSITIVE_BLACKLIST),
                        "全文出现黑名单敏感词（色情/暴力/政治敏感等）")
        self.assertTrue(_utf8_readable(WANX_DOC),
                        "文档含乱码（\\ufffd 替换字符）或无法按 UTF-8 解码")

    def test_no_svg_produced(self):
        """design/ 下无任何 .svg/.xml 文件（glob 递归校验；本任务为纯文档任务，A13）"""
        self.assertTrue(os.path.isdir(DESIGN_DIR), "design/ 目录不存在: %s" % DESIGN_DIR)
        self.assertTrue(_no_svg_files(DESIGN_DIR),
                        "design/ 下不应存在 SVG/XML 文件")


# ---------------------------------------------------------------------------
# 反案例
# ---------------------------------------------------------------------------
class TestWanxPromptNegative(unittest.TestCase):
    """反案例：非法/缺要素的临时文档应被校验函数拒绝，验证测试逻辑自身有效性"""

    def setUp(self):
        """创建临时目录存放反案例 md 文件（严禁写入 design/ 目录）"""
        self.tmp_dir = tempfile.mkdtemp(prefix="wanx_prompt_neg_", dir=tempfile.gettempdir())

    def tearDown(self):
        """清理临时目录"""
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _write_temp(self, name, content):
        """将内容写入临时目录并返回路径"""
        path = os.path.join(self.tmp_dir, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_reject_invalid_palette(self):
        """缺 hex / ratio≠100 / 删锚点词的临时文档校验失败，完整对照通过（A14）

        四类子断言：
        1) 缺 color_palette 8 色之一 → _check_color_palette 返回 False；
        2) ratio 数值求和 ≠ 100 → _check_color_palette 返回 False；
        3) 删任一锚点词（横向/卷轴/K线/曲折/向上/红色/箭头/水墨/极简）→
           _check_anchors 返回 False；
        4) 对照：未删任何要素的临时文档应通过（校验逻辑不依赖真实文档其他特性）。
        """
        full = _read_doc(WANX_DOC)
        real_param = _extract_section(full, "万相参数")
        self.assertTrue(real_param, "真实万相参数章节提取为空")

        # 1) 缺 1 个 hex（将 #F3E9D6 替换为非法值，其余 7 色保留）
        broken_hex = re.sub(r"#F3E9D6", "#000000", real_param, flags=re.IGNORECASE)
        path = self._write_temp("missing_hex.md", _make_temp_param_doc(broken_hex))
        self.assertFalse(_check_color_palette(_extract_section(_read_doc(path), "万相参数")),
                         "缺 1 个 hex 后色板校验应失败")

        # 2) ratio 求和 ≠ 100（将淡赭纸 ratio 25 改为 30，合计 105）
        broken_ratio = re.sub(r'"ratio":\s*25', '"ratio": 30', real_param)
        path = self._write_temp("ratio_sum_105.md", _make_temp_param_doc(broken_ratio))
        ratios = [int(v) for v in re.findall(r'ratio["\']?\s*[:：]\s*(\d+)', broken_ratio)]
        self.assertNotEqual(sum(ratios), 100, "构造的反例 ratio 求和应 != 100")
        self.assertFalse(_check_color_palette(_extract_section(_read_doc(path), "万相参数")),
                         "ratio 求和 != 100 后色板校验应失败")

        # 3) 删任一锚点词 → _check_anchors False（6 锚点全覆盖逻辑的缺失边界）
        real_main = _extract_section(full, "主提示词")
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

        # 4) 对照：完整临时文档应通过（色板 + 锚点）
        ok_param_path = self._write_temp("full_param_ok.md", _make_temp_param_doc(real_param))
        self.assertTrue(_check_color_palette(_extract_section(_read_doc(ok_param_path), "万相参数")),
                        "完整参数临时文档色板校验应通过")
        ok_main_path = self._write_temp("full_main_ok.md", _make_temp_doc(real_main))
        self.assertTrue(_check_anchors(_extract_section(_read_doc(ok_main_path), "主提示词")),
                        "完整主提示词临时文档锚点校验应通过")


# ---------------------------------------------------------------------------
# 边界案例
# ---------------------------------------------------------------------------
class TestWanxPromptBoundary(unittest.TestCase):
    """边界案例：主提示词长度阈值两侧（200/800 含边界通过，199/801 越界失败）"""

    def setUp(self):
        """创建临时目录存放边界 md 文件（严禁写入 design/ 目录）"""
        self.tmp_dir = tempfile.mkdtemp(prefix="wanx_prompt_bnd_", dir=tempfile.gettempdir())

    def tearDown(self):
        """清理临时目录"""
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _write_temp(self, name, content):
        """将内容写入临时目录并返回路径"""
        path = os.path.join(self.tmp_dir, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_length_boundary(self):
        """主提示词恰 200 字 / 恰 800 字均通过，199 / 801 字失败（边界含，四值四断言，A15）"""
        for n in (200, 800):
            path = self._write_temp("len_ok_%d.md" % n, _make_temp_doc("墨" * n))
            main_text = _extract_section(_read_doc(path), "主提示词")
            self.assertTrue(_main_length_ok(main_text),
                            "恰 %d 字主提示词应通过长度校验" % n)
        for n in (199, 801):
            path = self._write_temp("len_bad_%d.md" % n, _make_temp_doc("墨" * n))
            main_text = _extract_section(_read_doc(path), "主提示词")
            self.assertFalse(_main_length_ok(main_text),
                             "%d 字主提示词应失败（越界）" % n)


# ---------------------------------------------------------------------------
# 结果输出（unit_test.md 第八节）
# ---------------------------------------------------------------------------
def run_tests():
    """执行全部测试，结果写入 unit_test/test/test_wanx_prompt_result.txt 并生成 .gate.json"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestWanxPromptNormal))
    suite.addTests(loader.loadTestsFromTestCase(TestWanxPromptNegative))
    suite.addTests(loader.loadTestsFromTestCase(TestWanxPromptBoundary))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 确保输出目录存在
    test_result_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test")
    os.makedirs(test_result_dir, exist_ok=True)

    # 写入结果文件
    result_file = os.path.join(test_result_dir, "test_wanx_prompt_result.txt")
    with open(result_file, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("test_wanx_prompt 单元测试结果（河图Logo万相提示词）\n")
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
        "test_file": "unit_test/test_wanx_prompt.py",
        "result_file": "unit_test/test/test_wanx_prompt_result.txt",
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
