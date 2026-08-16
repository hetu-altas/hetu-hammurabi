# 河图 Logo 文生图提示词（第三期 · 品牌设计资产）

> 来源任务：20260804任务3 河图Logo文生图提示词（任务目录 `opencode_schedule/20260804/20260804任务3河图Logo文生图提示词/`）
> 产出日期：2026-08-08（charter-coder 编码节点产出）
> 用途：投喂 Midjourney / DALL·E 3 / Stable Diffusion / 通义万相 等主流文生图模型，生成河图体系水墨风 logo 底稿（AIGC 文生图路线前置提示词工程）
> 与一、二期关系：延续任务1（SVG 极简系列 01~05）的"卷轴母题 + 量化要素"视觉基因与任务2（SVG 水墨系列 06~10）的低饱和水墨色板与"墨分五色 / 飞白 / 印章"母题；本任务**不产出任何 SVG 文件、不实际调用文生图模型出图**，实测生成由用户后续自行安排。
> 使用前提：本文档所有提示词均可直接复制投喂；具体模型版本参数随官方更新，投喂前以模型官方最新文档为准。

### 核心要求与提示词段位映射

| 用户核心要求 | 承载段位 | 关键词 |
|-------------|----------|--------|
| 横向卷轴画卷 | 【主体】【构图】 | 横向、卷轴画卷、横卷、横幅构图、轴杆 |
| 水墨风 K 线图 | 【细节】 | 毛笔手绘、蜡烛形态、K 线 |
| 曲折向上的红色箭头 | 【细节】 | 曲折向上、蜿蜒折返、攀升、朱砂点睛 |
| 极简中国水墨风 | 【风格】【色彩】【质感】【光线】 | 极简、水墨、宣纸底、克制用色、留白 |

---

## 目录

- 一、主提示词（中文详细版）
- 二、英文提示词（逐段对照 + SD tag）
- 三、负面提示词（中文 + 英文）
- 四、参数建议（按模型参数基线表）
- 五、变体微调方向（5 个方向）
- 六、使用说明（模型适配与翻车规避）

---

## 主提示词（中文详细版）

> 说明：8 段连贯成文，可直接整段复制投喂中文模型（通义万相 / 即梦等）。

**【主体】**一幅横向展开的水墨卷轴画卷居中：半展开横卷横陈，左右焦墨轴杆立定，宣纸卷面半卷半舒。

**【构图】**横幅构图、卷面居中、左右均衡，四周留白不小于画布五分之一，疏朗透气。

**【风格】**极简中国水墨风，中式写意笔法，线条克制。

**【色彩】**宣纸米白淡赭纸底，焦墨黑主笔，朱砂红单点点睛，全图不超过三色。

**【质感】**宣纸纤维纹理，墨色晕染、墨分五色，飞白笔触，笔锋起收。

**【光线】**柔和均匀纸面光感，无投影，平面纸感。

**【细节】**卷面毛笔手绘水墨K线，蜡烛形态可辨；一根红色箭头蜿蜒折返、总体向上攀升，朱砂点睛；无文字无印章。

**【质量词】**极简高雅、疏朗留白、意境悠远，适合品牌标识底稿。

---

## 英文提示词（逐段对照 + SD tag）

> 说明：英文版分三种形态——①与中文 8 段逐段对照的短语组；②完整英文主提示词（MJ 风格词形态，可直接粘贴到 Midjourney）；③SD tag 形态（逗号分隔词串，供 Stable Diffusion 拆分为 positive 标签输入）。

### 3.1 与中文逐段对照（8 段）

| # | 中文段 | 英文对照（MJ 风格短语） |
|---|--------|--------------------------|
| 1 | 主体 | A horizontal Chinese ink painting scroll, half-unrolled horizontal scroll centered, two dark ink roller rods standing on both sides, rice paper surface half rolled half unfolded |
| 2 | 构图 | horizontal banner composition, scroll centered, left-right balanced, large negative space around, blank margin no less than one fifth of the canvas |
| 3 | 风格 | minimalist Chinese ink wash style, freehand xieyi brushwork, restrained thin lines, no clutter |
| 4 | 色彩 | rice paper off-white and light ochre base, dark ink main strokes, single vermilion red accent dot, no more than three colors in total |
| 5 | 质感 | rice paper fiber texture, ink wash with five shades of ink, dry-brush flying white strokes, visible brush-tip start and end |
| 6 | 光线 | soft even paper-surface lighting, no shadow, no volumetric light, flat paper feel |
| 7 | 细节 | hand-drawn ink candlestick k-line chart on the scroll, one vermilion red arrow curving upward with zigzag pullbacks, rising trend, no text, no seal |
| 8 | 质量词 | minimalist and elegant, spacious negative space, poetic artistic conception, suitable as brand logo draft |

### 3.2 完整英文主提示词（MJ 风格词形态，可直接粘贴）

```
A horizontal Chinese ink painting scroll, half-unrolled horizontal scroll centered, two dark ink roller rods, rice paper surface half rolled half unfolded, horizontal banner composition, scroll centered, left-right balanced, large negative space, minimalist sumi-e style, freehand xieyi brushwork, restrained thin lines, rice paper fiber texture, ink wash with five shades of ink, dry-brush flying white strokes, soft even flat paper lighting, no shadow, hand-drawn ink candlestick k-line chart on the scroll, one vermilion red arrow curving upward with zigzag pullbacks, rising trend, minimalist elegant, poetic mood, suitable as brand logo draft, no text
```

### 3.3 SD tag 形态（逗号分隔词串，进 positive 框）

```
horizontal scroll, rice paper, ink wash, sumi-e, minimalist, candlestick chart, k-line, red arrow, rising trend, zigzag pullback, negative space, flat lighting, dry brush, no text
```

> 投喂提示：SD 用户请将上方词串填入 positive 文本框（可逐词调权重），负面词填入 negative 文本框（见第三节）。

---

## 负面提示词（中文 + 英文）

> 说明：负面提示词用于排除常见翻车现象。英文版进 MJ `--no` 参数或 SD negative 框；中文版进通义万相等国产模型的负面/规避描述（若模型不支持负面框，可将关键禁词并入主提示词末尾"不要……"句式）。

### 4.1 英文负面提示词（Negative Prompt，必含 5 禁词）

```
text, watermark, 3d render, photorealistic, clutter, no logo, no border, no signature, no frame, no icon, no shadow, no gradient, no barcode, no grid lines, no typography, plain background
```

### 4.2 中文负面提示词（Negative Prompt 中文对应）

```
文字、水印、三维渲染、写实照片、杂乱堆砌、不要Logo、不要边框、不要签名、不要画框、不要图标、不要阴影、不要渐变、不要条形码、不要网格线、不要排版字样、纯色背景
```

> 5 禁词对应关系：`text`＝文字、`watermark`＝水印、`3d render`＝三维渲染、`photorealistic`＝写实照片、`clutter`＝杂乱堆砌；扩展项（no logo / no border / no signature 等）为加分清单，可按需增删。

---

## 参数建议（按模型参数基线表）

> 说明：以下参数为基线建议值，按模型分别给出；数值随官方版本迭代，投喂前以模型官方最新文档为准。

### 5.1 参数基线总表

| 模型 | 宽高比 | 风格权重 | 其他参数 |
|------|--------|----------|----------|
| Midjourney（主推） | `--ar 16:9`（画卷横幅主推）／`--ar 1:1`（logo 通用）／`--ar 2:3`（竖版备用） | `--stylize 100~250`（默认 100） | `--v 6`（或最新版本）；`--no text, watermark, 3d render, photorealistic, clutter` |
| Stable Diffusion | 1280×720（横幅）／1024×1024（方图） | CFG 4~7（默认 7） | 采样器 DPM++ 2M Karras、步数 20~30；positive 用英文主提示词（3.3 tag 形态），negative 填禁词清单（4.1） |
| DALL·E 3 | 1792×1024（横幅）／1024×1024（方图） | 无 CFG 类参数，用自然语言描述 | 尺寸参数 `size`；"no text" 等约束直接写入描述语句 |
| 通义万相 | 16:9（横幅）／1:1（方图） | 风格选项选"水墨 / 国画"类 | 中文主提示词（第一节）直投 + 参数面板调尺寸；负面约束写进提示词末尾 |

### 5.2 各模型参数写法示例

- **Midjourney**：`/imagine <英文主提示词全文> --ar 16:9 --stylize 150 --v 6 --no text, watermark, 3d render, photorealistic, clutter`
- **Midjourney（进阶·权重分段）**：可用 `::` 按权重分段控制要素优先级，如 `k-line chart::1.5, red arrow::1.8, scroll::1.2`；`--stylize` 值越低越忠实于描述词（100 最忠实），越高艺术性越强（250）。
- **Stable Diffusion（WebUI）**：positive 框 = 3.3 tag 词串；negative 框 = 4.1 禁词清单；采样器 DPM++ 2M Karras、步数 24、CFG 7、尺寸 1280×720。
- **DALL·E 3**：直接粘贴完整英文主提示词（3.2），并在句尾追加 "No text, no watermark, flat paper style."；size 选 1792×1024。
- **通义万相**：直接粘贴中文主提示词（第一节）整段，风格选项选"国画 / 水墨"，比例选 16:9；句尾可追加"不要文字、不要水印"强化负面约束（若面板支持负面提示词输入框，可直接填入 4.2 中文负面清单，二选一即可）。

---

## 变体微调方向（5 个方向）

> 说明：每个变体给出方向名 + 一句**可替换 / 追加**的提示词片段（中英文各一），并标注替换 / 追加位置；替换时直接替换主提示词对应段落内容，追加时在【细节】段末尾或指定位置补一句即可。默认主提示词为基础版（第 0 版），5 个变体互不相同、非同图微调。

### 变体1｜箭头形态变体（调节点睛力度）

- **要点**：默认"曲折向上的红色箭头"为折线式；可改为毛笔一笔式飞白箭头（笔意更足）或圆头弯箭（更柔和）。
- **中文替换片段**：一根毛笔一笔式飞白红色箭头，一笔呵成、蜿蜒攀升至画幅右上方，朱砂红点睛（替换【细节】段中"一根曲折向上的红色箭头……点睛"）。
- **英文替换片段**：one single-brush flying-white vermilion arrow drawn in one stroke, curving upward to the upper right (replace the arrow phrase in Section 7).

### 变体2｜K 线疏密变体（疏密两档）

- **要点**：默认 K 线为 7 根左右密布；可改 5 根疏朗（气韵更足）或 3 根极简（禅意更浓），延续任务2"传承与差异"口径。
- **中文替换片段**：卷面上以毛笔手绘五根疏朗的水墨K线，蜡烛形态可辨（替换【细节】段中"水墨K线图"为疏密档描述）。
- **英文替换片段**：five sparse hand-drawn ink candlesticks on the scroll, clearly readable candle shapes (replace the k-line phrase in Section 7).

### 变体3｜留白比例变体（气韵 vs 饱满）

- **要点**：默认四周留白 ≥ 画布 1/5；可加大至 1/3（气韵优先，画幅居中小巧）或收至 1/10（卷面满铺、饱满优先）。
- **中文替换片段**：四周大量留白，留白不小于画布三分之一，卷轴居中小巧、气韵绵长（替换【构图】段中"留白不小于画布五分之一"）。
- **英文替换片段**：large negative space around, blank margin no less than one third of the canvas, scroll small and centered (replace the margin phrase in Section 2).

### 变体4｜印章变体（加淡朱砂方印落款）

- **要点**：默认无印章；可追加右下角淡朱砂方印落款（36 见方、白文留白、无真实文字），仿任务2 10 号"落款为凭"作品感。
- **中文追加片段**：卷轴右下角盖一枚淡朱砂色方形印章落款，印文以抽象块面示意、不含真实文字（追加于【细节】段末尾）。
- **英文追加片段**：a light vermilion square seal stamp in the lower right corner of the scroll, abstract block pattern without real characters (append at the end of Section 7).

### 变体5｜画幅比例变体（双构图基因）

- **要点**：默认半展开横卷；可改为完全展开横幅（左右卷曲轴杆、全谱系展开感），延续任务1 方案1/方案3 双构图基因。
- **中文替换片段**：一幅完全展开的横向水墨横幅画卷居中，左右两根焦墨卷曲轴杆立定（替换【主体】段中"半展开横卷横陈画布中央"）。
- **英文替换片段**：a fully unrolled horizontal ink banner scroll centered, two dark ink rolled rods on both sides (replace the subject phrase in Section 1).

---

## 使用说明（模型适配与翻车规避）

### 6.1 模型适配表（各模型投喂方式）

| 模型 | 投喂方式 | 参数写法差异 | 备注 |
|------|----------|--------------|------|
| Midjourney | 直接粘贴英文主提示词（3.2）＋参数后缀 | `--ar` / `--stylize` / `--v` / `--no` 一次写全 | 负面词挂 `--no`，勿再单独输负面框 |
| Stable Diffusion | 正面 / 负面分开：positive 填 3.3 tag 词串，negative 填 4.1 禁词清单 | 权重用 `(word:1.2)` 调节；CFG 4~7；采样器 DPM++ 2M Karras | 尺寸按 5.1 选横幅或方图 |
| DALL·E 3 | 直接粘贴完整英文主提示词（3.2）自然语言 | 无 CFG；`size` 参数选 1792×1024；"no text" 等约束写进描述 | 中文场景可改用第一节中文主提示词直投 |
| 通义万相 | 中文主提示词（第一节）直投，参数面板选尺寸与风格 | 风格选项选"水墨 / 国画"类；比例 16:9 / 1:1 | 负面约束并入提示词末尾"不要……"句式；若所用版本支持负面提示词输入框，可直填 4.2 中文负面清单（与句尾句式二选一） |

### 6.2 常见翻车规避清单

| # | 翻车现象 | 规避手段 |
|---|----------|----------|
| 1 | **文字乱码**：画面出现乱码字符 / 伪汉字 | 负面提示词必加 `text`；画面描述中禁用字形词（如"写几个字"）；中文版句尾加"不要任何文字" |
| 2 | **元素拼贴 / 割裂**：卷轴、K 线、箭头各自为政、构图散乱 | 元素种类克制在 5 类以内；构图词用"居中 / 单主体 / 均衡"；负面加 `clutter` |
| 3 | **风格不统一**：水墨与写实混搭、半卷半照片 | 统一墨阶与用色词（焦墨 / 淡墨 / 墨分五色）；避免中英混写与多风格并列词；负面加 `photorealistic` |
| 4 | **K 线被读成条形码**：蜡烛变成整齐几何条 | 加 `hand-drawn candlestick` / "毛笔手绘、蜡烛形态可辨"；负面加 `no barcode`、`no grid lines` |
| 5 | **红色箭头过细被吞**：箭头在留白中看不清 | 主词加 `bold vermilion arrow` 强化朱砂色对比（单独成句强调"一根红色箭头……总体向上攀升"）；或采用变体3（加大留白比例）提升箭头可见性；负面加 `no watermark` 防叠加水印干扰 |

### 6.3 使用流程建议

1. **首轮**：按"默认主提示词 + 5.1 参数基线"分别投喂 2~3 个模型，各出 2~4 张对比；
2. **微调**：从第五节 5 个变体中挑 1~2 个方向替换 / 追加片段，控制变量逐项验证；
3. **精选**：将效果最佳的 1~2 张底稿交由矢量重绘 / 人工精修，再进入品牌资产定稿流程（与一二期 SVG 方案并案评估）。

---

*本文档由 charter-coder 节点依据任务书（20260804任务3）与实施计划产出，为纯提示词工程文档，不含任何 SVG / XML 设计文件，不实际调用文生图模型；实测出图与效果回评由用户后续自行安排。*
