# -*- coding: utf-8 -*-
"""
test_wanx_prompt_v2 单元测试
20260804任务5 河图Logo万相提示词极简优化：万相提示词 V2 文档文本合规性单元测试

测试对象：design/河图Logo万相提示词V2.md（markdown 文本内容断言，非 SVG/XML 断言）
覆盖范围（任务书第七节 + 实施计划 §四，共 16 用例 = 正常 14 + 反例 1 + 边界 1）：
  - 正常案例 14 个：A1~A14 逐条落位（A9 为新增"无米色 token"断言，A3 为扩展
    8 组锚点（6 基础 + 3阳2阴 + 黑白红三色）），见下方"A 类 → 用例名映射"；
  - 反案例    1 个：缺 3阳2阴锚点词 / color_palette 超 3 色（含旧 8 色板 hex）/
                     ratio 求和 ≠ 100 / 主提示词正文含米色色名 四类临时文档校验
                    失败（A15，验证测试逻辑自身有效性），含完整对照；
  - 边界案例  1 个：主提示词恰 200/700 字通过、199/701 字失败（四值四断言，A16）。
反案例与边界案例均通过 tempfile 构造临时 md 验证（严格写临时目录、tearDown 清理），
严禁写入 design/ 目录，避免污染"无 SVG 产出"断言。

A 类 → 用例名映射（与任务书第七节 #1~16 一致）：
  A1  → test_doc_exists_not_empty      A9  → test_no_beige
  A2  → test_six_sections_present      A10 → test_negative_handling
  A3  → test_anchors_covered           A11 → test_variants_3
  A4  → test_main_prompt_length        A12 → test_feeding_dual
  A5  → test_model                     A13 → test_no_sensitive_utf8
  A6  → test_size                      A14 → test_no_svg
  A7  → test_thinking_extend           A15 → test_reject_invalid
  A8  → test_color_palette_exactly3    A16 → test_length_boundary

与任务4 test_wanx_prompt.py 的关系：以任务4 单测（15 用例）为实现基线，复用
_read_doc/_extract_section/_check_sections/_check_model/_check_size/_check_thinking/
_check_variants_wanx/_check_feeding/_check_sensitive/_utf8_readable/_no_svg_files/
_make_temp_doc/_make_temp_param_doc/run_tests 框架，**必须改写**：
  ① _check_color_palette：8 色 all-in → "恰 3 色 + hex 去重计数 + ratio 求和 100"
    （V2 口径：8 色→3 色，不得复用任务4 8 色断言）；
  ② _check_anchors：6 组 → 8 组（新增锚点 7 3阳2阴、锚点 8 黑白红三色）；
  ③ 新增 _check_no_beige（旧 8 色 hex 零残留 + "不要出现"之前色名零残留）；
  ④ _check_negative_handling：V2 扩展（句式须覆盖米色/米黄与渐变禁词）；
  ⑤ 长度边界常量 MAIN_LEN_MAX：800 → 700。

关键口径（任务书第七节 + 实施计划 §四约定）：
  1. 章节提取：line.startswith("## ") 且 line[3:].startswith(标题前缀)；
     文内 ### 三级标题不会误切；标题支持前缀匹配；
  2. 锚点/参数词匹配统一 re.IGNORECASE；K线/K 线/kline/k-line 多拼写兼容；
  3. 长度口径：去除全部空白字符后 len()，边界含 [200,700]（编码节点实测
     主提示词章节 489 字，安全区内）；
  4. color_palette（V2 口径）：参数章节 #hex 全量提取小写化去重后计数恰为 3
     且集合恰等于 {#ffffff,#1c1c22,#b33a2e}（文档中表格/JSON/色值说明多处
     重复同一 hex 不影响，出现第 4 个不同 hex 即失败）；ratio 数值真实解析
     求和 == 100（re.findall(r'ratio["\']?\\s*[:：]\\s*(\\d+)')，仅命中
     API JSON 请求体的 "ratio": n 格式，表格竖线格式不匹配）；
  5. "不要出现"句式仅 1 处（主提示词正文末尾）；A9 禁色校验以
     main_text.split("不要出现")[0] 截取纯正面正文；
  6. 测试纯标准库（unittest/re/os/glob/tempfile/shutil），零外部依赖。
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
WANX_DOC = os.path.join(DESIGN_DIR, "河图Logo万相提示词V2.md")

# 6 个必需章节标题前缀（A2，按前缀匹配，容忍"万相参数配置"等扩展命名）
REQUIRED_SECTIONS = (
    "主提示词", "万相参数", "负面", "变体", "投喂", "翻车",
)

# V2 3 色极简色板 hex（A8，仅允许这三色，大小写不敏感；V2 口径：8 色→3 色）
NEW_COLOR_HEX = ("#FFFFFF", "#1C1C22", "#B33A2E")

# 任务4 旧 8 色板 hex（A9①，全文档零残留，大小写不敏感）
OLD_COLOR_HEX = (
    "#F3E9D6", "#3B3733", "#57504A", "#8D8578",
    "#B7AFA2", "#4E5D66", "#A96B5F", "#A9976B",
)

# 米色系色名（A9②，主提示词"不要出现"句式之前正文零残留）
BEIGE_NAMES = ("米色", "米黄", "淡赭", "棕色", "金色", "哑金", "赭")

# 敏感词黑名单（A13，与正文用词零交集，沿用任务4 口径）
SENSITIVE_BLACKLIST = (
    "色情", "淫秽", "暴力", "凶杀", "毒品", "军火", "赌博",
    "恐怖主义", "爆炸物", "枪支", "颠覆国家", "分裂国家",
)

# 主提示词长度边界（A4/A15/A16，去空白字符计，边界含；V2 口径：800→700）
MAIN_LEN_MIN = 200
MAIN_LEN_MAX = 700

# 变体数量区间（A11）
VARIANT_MIN = 2
VARIANT_MAX = 3


# ---------------------------------------------------------------------------
# 模块级纯函数（供正常 / 反案例 / 边界案例直接调用，验证测试逻辑自身有效性）
# ---------------------------------------------------------------------------
def _read_doc(path: str) -> str:
    """UTF-8 读取文档全文；文件不存在或解码失败时抛异常（复用任务4 口径）"""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _extract_section(text: str, title: str) -> str:
    """按 '## 标题前缀' 切出章节正文（至下一个 '## ' 前，不含标题行）

    口径（复用任务4）：仅匹配 line.startswith("## ") 的二级标题；### 三级标题
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
    """校验 6 个必需章节标题（## 前缀匹配）是否全部出现（A2，复用任务4 口径）"""
    found = set()
    for line in text.splitlines():
        if line.startswith("## "):
            for title in REQUIRED_SECTIONS:
                if line[3:].startswith(title):
                    found.add(title)
    return found == set(REQUIRED_SECTIONS)


def _check_anchor7(main_text: str) -> bool:
    """校验锚点 7：3 阳 2 阴（V2 新增，A3）

    阳 3 组与阴 2 组两组均须命中（re.IGNORECASE）：
      阳组：(3|三)[根支]?阳(线)? 或直接命中 3阳2阴/三阳两阴；
      阴组：(2|两)[根支]?阴(线)? 或直接命中 3阳2阴/三阳两阴。
    """
    yang = re.search(r"(?:3|三)\s*[根支]?\s*阳(?:线)?|3阳2阴|三阳两阴",
                     main_text, re.IGNORECASE)
    yin = re.search(r"(?:2|两)\s*[根支]?\s*阴(?:线)?|3阳2阴|三阳两阴",
                    main_text, re.IGNORECASE)
    return bool(yang) and bool(yin)


def _check_anchor8(main_text: str) -> bool:
    """校验锚点 8：黑白红三色（V2 新增，A3）

    白色组（白色|白底|纯白）且 黑色组（黑色|墨黑|纯黑|浓墨）且
    红色组（红色|朱砂红|朱砂），三组均须命中（re.IGNORECASE）。
    """
    white = re.search(r"白色|白底|纯白", main_text, re.IGNORECASE)
    black = re.search(r"黑色|墨黑|纯黑|浓墨", main_text, re.IGNORECASE)
    red = re.search(r"红色|朱砂红|朱砂", main_text, re.IGNORECASE)
    return bool(white) and bool(black) and bool(red)


def _check_anchors(main_text: str) -> bool:
    """校验 8 组必需要素锚点全部命中（V2 口径：6 基础锚点复用任务4 + 锚点 7/8 新增）

    AND 关系：横向+卷轴/画卷/横卷；(曲折|蜿蜒|折返)+(向上|上行|上扬|攀升)；
              红色+箭头；锚点 7 阳组+阴组；锚点 8 白+黑+红三组。
    OR 关系：K线|K 线|kline|k-line；水墨；极简。
    统一 re.IGNORECASE。
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
    # 7 3 阳 2 阴（V2 新增）
    if not _check_anchor7(main_text):
        return False
    # 8 黑白红三色（V2 新增）
    if not _check_anchor8(main_text):
        return False
    return True


def _main_length_ok(main_text: str) -> bool:
    """校验主提示词章节去空白后长度 ∈ [200, 700]（中文按字符计，边界含，A4/A16）

    V2 口径：任务4 上限 800 收窄为 700。
    """
    stripped = re.sub(r"\s", "", main_text)
    return MAIN_LEN_MIN <= len(stripped) <= MAIN_LEN_MAX


def _check_model(param_text: str) -> bool:
    """校验模型选型：参数章节含 wan2.7-image-pro（主推）与 wan2.6-t2i（备选），
    且 wan2.7-image-pro 所在行含"主推/旗舰"主推语义（A5，复用任务4 口径）"""
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
    """校验 size 参数合规：含"宽*高"星号格式说明，且给出 16:9/1:1 任一建议值（A6，复用任务4 口径）"""
    if not re.search(r"2688\*1536|2048\*2048|4096\*2304", param_text):
        return False
    # "宽*高" / "宽×高" 格式说明（星号或乘号分隔）
    if not re.search(r"宽\s*[＊*×]\s*高", param_text):
        return False
    return True


def _check_thinking(param_text: str) -> bool:
    """校验 thinking_mode / prompt_extend 描述正确（A7，复用任务4 口径）：
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
    """校验 color_palette 恰 3 色且 ratio 求和 == 100（A8，V2 口径：8 色→3 色）

    1) 参数章节 #hex 全量提取（re.findall(r'#[0-9a-fA-F]{6}')）小写化**去重**后
       计数恰为 3，且集合恰等于 {#ffffff,#1c1c22,#b33a2e}（表格/JSON/色值说明
       多处重复同一 hex 不影响；出现第 4 个不同 hex 即失败）；
    2) 真实解析 ratio 数值求和 == 100——re.findall(r'ratio["\']?\\s*[:：]\\s*(\\d+)')
       仅命中 API JSON 请求体 "ratio": n 格式（70/20/10 求和 100），表格竖线
       格式（| 70 |）与投喂章节完整 JSON（属投喂章节，不在参数章节内）不参与。
    """
    hexes = [h.lower() for h in re.findall(r"#[0-9a-fA-F]{6}", param_text)]
    if len(set(hexes)) != 3:
        return False
    if set(hexes) != set(h.lower() for h in NEW_COLOR_HEX):
        return False
    ratios = [int(v) for v in re.findall(r'ratio["\']?\s*[:：]\s*(\d+)', param_text)]
    return sum(ratios) == 100


def _check_no_beige(full_text: str, main_text: str) -> bool:
    """校验无米色系颜色 token（A9，V2 新增）

    ① 全文档旧 8 色板 hex 零残留（#F3E9D6/#3B3733/#57504A/#8D8578/#B7AFA2/
       #4E5D66/#A96B5F/#A9976B，大小写不敏感子串扫描）；
    ② 主提示词"不要出现"句式之前文本零出现米色系色名
       （米色|米黄|淡赭|棕色|金色|哑金|赭）——"不要出现"唯一性口径：
       主提示词正文仅 1 处"不要出现"（负面句式末尾），split()[0] 即纯正面正文。
    """
    low = full_text.lower()
    if any(h.lower() in low for h in OLD_COLOR_HEX):
        return False
    before_neg = main_text.split("不要出现")[0]
    if any(name in before_neg for name in BEIGE_NAMES):
        return False
    return True


def _check_negative_handling(neg_text: str) -> bool:
    """校验负面要素处理正确（A10，V2 扩展：任务4 口径 + 米色/渐变禁词覆盖）：
    - negative_prompt 与"不支持"同段出现（wan2.7 系列不支持 negative_prompt）；
    - 含正向"不要出现"句式；
    - "不要出现"句式覆盖米色禁词（米色|米黄）与渐变禁词（渐变）。
    """
    if "不要出现" not in neg_text:
        return False
    if "negative_prompt" not in neg_text.lower():
        return False
    # 句式覆盖米色禁词（米色|米黄）与渐变禁词（渐变）
    sentence = neg_text.split("不要出现", 1)[1]
    if not re.search(r"米色|米黄", sentence):
        return False
    if not re.search(r"渐变", sentence):
        return False
    for line in neg_text.splitlines():
        if "negative_prompt" in line.lower() and "不支持" in line:
            return True
    return False


def _check_variants_wanx(var_text: str) -> bool:
    """校验变体章节（A11，复用任务4 口径）：变体标记（变体[A-C]|变体[1-3]|①|②|③）
    数量 ∈ [2,3]，各变体小节含片段/追加引导词，且章节内含 size 配套值
    （2688*1536|2048*2048 至少一处）"""
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
    """校验投喂步骤双通道（A12，复用任务4 口径）：API 方式（messages 或
    input.prompt 任一）与百炼控制台方式（控制台 或 百炼 任一）"""
    low = feed_text.lower()
    api_ok = ("messages" in low) or ("input.prompt" in low)
    console_ok = ("控制台" in feed_text) or ("百炼" in feed_text)
    return api_ok and console_ok


def _check_sensitive(text: str, blacklist) -> bool:
    """校验全文黑名单敏感词零命中（小写化后子串扫描，复用任务4 口径）"""
    low = text.lower()
    return not any(word in low for word in blacklist)


def _no_svg_files(design_dir: str) -> bool:
    """校验 design/ 目录（含子目录递归）下无任何 .svg / .xml 文件（复用任务4 口径）"""
    svg_files = glob.glob(os.path.join(design_dir, "**", "*.svg"), recursive=True)
    xml_files = glob.glob(os.path.join(design_dir, "**", "*.xml"), recursive=True)
    return len(svg_files) == 0 and len(xml_files) == 0


def _utf8_readable(path: str) -> bool:
    """校验文档 UTF-8 解码无异常且不含 \ufffd 替换字符（复用任务4 口径）"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except (OSError, UnicodeDecodeError):
        return False
    return "\ufffd" not in text


def _make_temp_doc(main_body: str) -> str:
    """构造最小文档模板：'## 主提示词' + 主提示词正文（供反例/边界长度用例，复用任务4 口径）"""
    return "## 主提示词\n\n%s\n" % main_body


def _make_temp_param_doc(param_body: str) -> str:
    """构造最小参数文档模板：'## 万相参数配置' + 参数正文（供色板反例用例，复用任务4 口径）"""
    return "## 万相参数配置\n\n%s\n" % param_body


# ---------------------------------------------------------------------------
# 正常案例
# ---------------------------------------------------------------------------
class TestWanxPromptV2Normal(unittest.TestCase):
    """正常案例：对 design/ 下真实万相提示词 V2 交付物的文本合规性断言（A1~A14）"""

    @classmethod
    def setUpClass(cls):
        """一次性读取交付物文档全文，供全部正常用例共享（不存在时为 None）"""
        cls.full_text = None
        if os.path.exists(WANX_DOC):
            cls.full_text = _read_doc(WANX_DOC)

    def test_doc_exists_not_empty(self):
        """交付物存在且非空：V2 文档文件存在、可读、内容长度 > 0（A1）"""
        self.assertTrue(os.path.exists(WANX_DOC), "交付物不存在: %s" % WANX_DOC)
        self.assertTrue(os.path.isfile(WANX_DOC), "交付物路径不是文件: %s" % WANX_DOC)
        self.assertIsNotNone(self.full_text, "交付物无法读取")
        self.assertGreater(len(self.full_text), 0, "交付物内容为空")

    def test_six_sections_present(self):
        """6 个必需章节齐全：主提示词/万相参数/负面/变体/投喂/翻车（A2）"""
        self.assertIsNotNone(self.full_text, "交付物无法读取")
        self.assertTrue(_check_sections(self.full_text), "6 个必需章节标题未全部出现")

    def test_anchors_covered(self):
        """扩展锚点组全覆盖：6 基础锚点 + 3阳2阴 + 黑白红三色 8 组全命中（A3）"""
        self.assertIsNotNone(self.full_text, "交付物无法读取")
        main_text = _extract_section(self.full_text, "主提示词")
        self.assertTrue(main_text, "主提示词章节提取为空")
        self.assertTrue(_check_anchors(main_text), "8 组必需要素锚点未全部命中")

    def test_main_prompt_length(self):
        """主提示词章节去空白后长度 ∈ [200, 700]（边界含，V2 口径，A4）"""
        self.assertIsNotNone(self.full_text, "交付物无法读取")
        main_text = _extract_section(self.full_text, "主提示词")
        self.assertTrue(_main_length_ok(main_text),
                        "主提示词去空白长度不在 [200, 700] 区间")
        print("  [主提示词] 去空白长度: %d" % len(re.sub(r"\s", "", main_text)))

    def test_model(self):
        """模型选型准确：参数章节含 wan2.7-image-pro（主推/旗舰）与 wan2.6-t2i（备选）（A5）"""
        self.assertIsNotNone(self.full_text, "交付物无法读取")
        param_text = _extract_section(self.full_text, "万相参数")
        self.assertTrue(param_text, "万相参数章节提取为空")
        self.assertTrue(_check_model(param_text),
                        "模型选型（主推 wan2.7-image-pro / 备选 wan2.6-t2i）校验未通过")

    def test_size(self):
        """size 参数合规：含"宽*高"星号格式说明与建议值（2688*1536/2048*2048/4096*2304 任一）（A6）"""
        self.assertIsNotNone(self.full_text, "交付物无法读取")
        param_text = _extract_section(self.full_text, "万相参数")
        self.assertTrue(param_text, "万相参数章节提取为空")
        self.assertTrue(_check_size(param_text), "size 参数（宽*高格式/建议值）校验未通过")

    def test_thinking_extend(self):
        """thinking_mode/prompt_extend 语义正确：thinking_mode 默认 true 仅 wan2.7；
        prompt_extend 标注 wan2.7 不支持（A7）"""
        self.assertIsNotNone(self.full_text, "交付物无法读取")
        param_text = _extract_section(self.full_text, "万相参数")
        self.assertTrue(param_text, "万相参数章节提取为空")
        self.assertTrue(_check_thinking(param_text), "thinking_mode/prompt_extend 语义校验未通过")

    def test_color_palette_exactly3(self):
        """color_palette 恰 3 色：参数章节 #hex 去重计数恰 3 且集合={#ffffff,#1c1c22,#b33a2e}，
        ratio 数值求和 == 100（V2 口径：8 色→3 色，A8）"""
        self.assertIsNotNone(self.full_text, "交付物无法读取")
        param_text = _extract_section(self.full_text, "万相参数")
        self.assertTrue(param_text, "万相参数章节提取为空")
        hexes = [h.lower() for h in re.findall(r"#[0-9a-fA-F]{6}", param_text)]
        ratios = [int(v) for v in re.findall(r'ratio["\']?\s*[:：]\s*(\d+)', param_text)]
        print("  [color_palette] hex 全量: %s 去重计数: %d" % (hexes, len(set(hexes))))
        print("  [color_palette] 解析 ratio 列表: %s 求和: %d" % (ratios, sum(ratios)))
        self.assertTrue(_check_color_palette(param_text),
                        "color_palette 非恰 3 色（#FFFFFF/#1C1C22/#B33A2E）或 ratio 求和 != 100")

    def test_no_beige(self):
        """无米色系颜色 token：①全文档旧 8 色板 hex 零残留；
        ②主提示词"不要出现"句式之前正文零米色系色名（A9，V2 新增）"""
        self.assertIsNotNone(self.full_text, "交付物无法读取")
        main_text = _extract_section(self.full_text, "主提示词")
        self.assertTrue(main_text, "主提示词章节提取为空")
        self.assertTrue(_check_no_beige(self.full_text, main_text),
                        "检测到旧 8 色板 hex 残留或主提示词正文出现米色系色名")

    def test_negative_handling(self):
        """负面要素处理正确：negative_prompt 与"不支持"同段、含"不要出现"句式，
        且句式覆盖米色禁词（米色|米黄）与渐变禁词（渐变）（A10，V2 扩展）"""
        self.assertIsNotNone(self.full_text, "交付物无法读取")
        neg_text = _extract_section(self.full_text, "负面")
        self.assertTrue(neg_text, "负面要素处理章节提取为空")
        self.assertTrue(_check_negative_handling(neg_text),
                        "负面要素处理（不支持 negative_prompt + 不要出现句式 + 米色/渐变禁词）校验未通过")

    def test_variants_3(self):
        """变体章节 3 个变体（变体[A-C]/变体[1-3]/①~③）各含片段/追加引导词与 size 配套值（A11）"""
        self.assertIsNotNone(self.full_text, "交付物无法读取")
        var_text = _extract_section(self.full_text, "变体")
        self.assertTrue(var_text, "变体章节提取为空")
        markers = set(re.findall(r"变体[1-3]|变体[A-C]|①|②|③", var_text))
        print("  [变体] 标记数: %d" % len(markers))
        self.assertTrue(_check_variants_wanx(var_text),
                        "变体数量/片段引导词/size 配套校验未通过")

    def test_feeding_dual(self):
        """投喂步骤双通道：API 方式（messages/input.prompt）与控制台方式（控制台/百炼）（A12）"""
        self.assertIsNotNone(self.full_text, "交付物无法读取")
        feed_text = _extract_section(self.full_text, "投喂")
        self.assertTrue(feed_text, "投喂步骤章节提取为空")
        self.assertTrue(_check_feeding(feed_text),
                        "投喂步骤（API + 控制台双通道）校验未通过")

    def test_no_sensitive_utf8(self):
        """全文敏感词黑名单零命中（暴力/色情/政治敏感等）且 UTF-8 无 \ufffd 替换字符（A13）"""
        self.assertIsNotNone(self.full_text, "交付物无法读取")
        self.assertTrue(_check_sensitive(self.full_text, SENSITIVE_BLACKLIST),
                        "全文出现黑名单敏感词（色情/暴力/政治敏感等）")
        self.assertTrue(_utf8_readable(WANX_DOC),
                        "文档含乱码（\\ufffd 替换字符）或无法按 UTF-8 解码")

    def test_no_svg(self):
        """design/ 下无任何 .svg/.xml 文件（glob 递归校验；本任务为纯文档任务，A14）"""
        self.assertTrue(os.path.isdir(DESIGN_DIR), "design/ 目录不存在: %s" % DESIGN_DIR)
        self.assertTrue(_no_svg_files(DESIGN_DIR),
                        "design/ 下不应存在 SVG/XML 文件")


# ---------------------------------------------------------------------------
# 反案例
# ---------------------------------------------------------------------------
class TestWanxPromptV2Negative(unittest.TestCase):
    """反案例：非法/缺要素的临时文档应被校验函数拒绝，验证测试逻辑自身有效性"""

    def setUp(self):
        """创建临时目录存放反案例 md 文件（严禁写入 design/ 目录）"""
        self.tmp_dir = tempfile.mkdtemp(prefix="wanx_prompt_v2_neg_", dir=tempfile.gettempdir())

    def tearDown(self):
        """清理临时目录"""
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _write_temp(self, name, content):
        """将内容写入临时目录并返回路径"""
        path = os.path.join(self.tmp_dir, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_reject_invalid(self):
        """缺 3阳2阴 / 色板超3色（含旧 hex）/ ratio≠100 / 正文含米色 四类临时文档校验失败，
        完整对照通过（A15，V2 扩展）

        四类子断言：
        1) 删"3根阳线""2根阴线" → _check_anchors 返回 False（锚点 7 缺失）；
        2) color_palette 数组追加旧 8 色板 hex #F3E9D6 → _check_color_palette
           False（hex 去重计数变 4）且 _check_no_beige False（旧 hex 残留）；
        3) "ratio": 70 改 75 → 求和 105 ≠ 100 → _check_color_palette False；
        4) 主提示词正文（"不要出现"之前）插入"米色" → _check_no_beige False；
        5) 对照：完整真实章节（主提示词 + 参数）临时文档应全部通过。
        """
        full = _read_doc(WANX_DOC)
        real_param = _extract_section(full, "万相参数")
        self.assertTrue(real_param, "真实万相参数章节提取为空")
        real_main = _extract_section(full, "主提示词")
        self.assertTrue(real_main, "真实主提示词章节提取为空")

        # 1) 删"3根阳线"与"2根阴线" → 锚点 7（3阳2阴）缺失 → 锚点校验失败
        broken_anchor7 = re.sub(r"3根阳线|2根阴线", "", real_main)
        path = self._write_temp("missing_anchor7.md", _make_temp_doc(broken_anchor7))
        main_text = _extract_section(_read_doc(path), "主提示词")
        self.assertFalse(_check_anchors(main_text),
                         "删除 3阳2阴 锚点词后扩展锚点校验应失败")

        # 2) 向 color_palette 数组追加旧 8 色板 hex #F3E9D6 → 色板校验失败 + 禁色校验失败
        broken_palette = re.sub(
            r'\{\s*"color": "#B33A2E", "ratio": 10\s*\}',
            '{ "color": "#B33A2E", "ratio": 10 },\n      { "color": "#F3E9D6", "ratio": 0 }',
            real_param, flags=re.IGNORECASE,
        )
        hexes = [h.lower() for h in re.findall(r"#[0-9a-fA-F]{6}", broken_palette)]
        self.assertEqual(len(set(hexes)), 4, "构造的反例 hex 去重计数应变为 4")
        path = self._write_temp("palette_over3.md", _make_temp_param_doc(broken_palette))
        doc_text = _read_doc(path)
        self.assertFalse(_check_color_palette(_extract_section(doc_text, "万相参数")),
                         "color_palette 超过 3 色后色板校验应失败")
        self.assertFalse(_check_no_beige(doc_text, _extract_section(doc_text, "主提示词")),
                         "混入旧 8 色板 hex 后禁色校验应失败")

        # 3) ratio 70 改 75（求和 105 ≠ 100）→ 色板校验失败
        broken_ratio = re.sub(r'"ratio":\s*70', '"ratio": 75', real_param)
        ratios = [int(v) for v in re.findall(r'ratio["\']?\s*[:：]\s*(\d+)', broken_ratio)]
        self.assertNotEqual(sum(ratios), 100, "构造的反例 ratio 求和应 != 100")
        path = self._write_temp("ratio_sum_105.md", _make_temp_param_doc(broken_ratio))
        self.assertFalse(_check_color_palette(_extract_section(_read_doc(path), "万相参数")),
                         "ratio 求和 != 100 后色板校验应失败")

        # 4) 主提示词正文（"不要出现"之前）插入"米色" → 禁色校验失败
        broken_main = real_main.replace("不含真实文字。", "不含真实文字。底色偏米色。", 1)
        self.assertNotIn("底色偏米色", real_main, "真实文档不应已含插入语")
        path = self._write_temp("main_beige.md", _make_temp_doc(broken_main))
        doc_text = _read_doc(path)
        main_text = _extract_section(doc_text, "主提示词")
        self.assertFalse(_check_no_beige(doc_text, main_text),
                         "主提示词正文含米色色名后禁色校验应失败")

        # 5) 对照：完整真实章节临时文档应全部通过
        ok_main_path = self._write_temp("full_main_ok.md", _make_temp_doc(real_main))
        ok_main = _extract_section(_read_doc(ok_main_path), "主提示词")
        self.assertTrue(_check_anchors(ok_main), "完整主提示词临时文档锚点校验应通过")
        self.assertTrue(_check_no_beige(_read_doc(ok_main_path), ok_main),
                        "完整主提示词临时文档禁色校验应通过")
        ok_param_path = self._write_temp("full_param_ok.md", _make_temp_param_doc(real_param))
        ok_param = _extract_section(_read_doc(ok_param_path), "万相参数")
        self.assertTrue(_check_color_palette(ok_param),
                        "完整参数临时文档色板校验应通过")


# ---------------------------------------------------------------------------
# 边界案例
# ---------------------------------------------------------------------------
class TestWanxPromptV2Boundary(unittest.TestCase):
    """边界案例：主提示词长度阈值两侧（200/700 含边界通过，199/701 越界失败）"""

    def setUp(self):
        """创建临时目录存放边界 md 文件（严禁写入 design/ 目录）"""
        self.tmp_dir = tempfile.mkdtemp(prefix="wanx_prompt_v2_bnd_", dir=tempfile.gettempdir())

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
        """主提示词恰 200 字 / 恰 700 字均通过，199 / 701 字失败（边界含，四值四断言，A16）"""
        for n in (200, 700):
            path = self._write_temp("len_ok_%d.md" % n, _make_temp_doc("墨" * n))
            main_text = _extract_section(_read_doc(path), "主提示词")
            self.assertTrue(_main_length_ok(main_text),
                            "恰 %d 字主提示词应通过长度校验" % n)
        for n in (199, 701):
            path = self._write_temp("len_bad_%d.md" % n, _make_temp_doc("墨" * n))
            main_text = _extract_section(_read_doc(path), "主提示词")
            self.assertFalse(_main_length_ok(main_text),
                             "%d 字主提示词应失败（越界）" % n)


# ---------------------------------------------------------------------------
# 结果输出（unit_test.md 第八节）
# ---------------------------------------------------------------------------
def run_tests():
    """执行全部测试，结果写入 unit_test/test/test_wanx_prompt_v2_result.txt 并生成 .gate.json"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestWanxPromptV2Normal))
    suite.addTests(loader.loadTestsFromTestCase(TestWanxPromptV2Negative))
    suite.addTests(loader.loadTestsFromTestCase(TestWanxPromptV2Boundary))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 确保输出目录存在
    test_result_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test")
    os.makedirs(test_result_dir, exist_ok=True)

    # 写入结果文件
    result_file = os.path.join(test_result_dir, "test_wanx_prompt_v2_result.txt")
    with open(result_file, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("test_wanx_prompt_v2 单元测试结果（河图Logo万相提示词 V2）\n")
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
        "test_file": "unit_test/test_wanx_prompt_v2.py",
        "result_file": "unit_test/test/test_wanx_prompt_v2_result.txt",
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
