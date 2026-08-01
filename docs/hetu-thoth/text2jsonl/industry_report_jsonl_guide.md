# 行业研报分块生成 JSONL 与向量入库

> 更新日期：2026-06-21 | 模块：`src/text2jsonl/build_industry_report_jsonl.py`、`src/indexing/insert_vectors.py`

---

## 一、概述

将行业研报 Markdown 文件按 H2 标题分段，使用 LangChain `RecursiveCharacterTextSplitter` 递归切分后，生成 `text-embedding-v4` Batch API 所需的 JSONL 格式文件，向量化后入库 Milvus。

### 1.1 与其他数据源的差异

行业研报与其他 MD 类数据源（npr / stock_report / anns_d）的核心区别在于 **不使用 `util_jsonl_builder` 公共模块**，而是独立实现分块逻辑：

| 项目 | 其他 MD 数据源 | 行业研报 |
|------|--------------|---------|
| 分块方式 | `util_jsonl_builder._chunk_content()`，按 token 段落切分 | LangChain `RecursiveCharacterTextSplitter`，按字符数切分 |
| 切分粒度 | 按 `\n\n` 段落边界 | H2 标题分段 → 短章节合并 → 递归切分（`\n\n` → `\n` → `。` → `，`） |
| 表格处理 | 无特殊处理 | 等长占位符保护 + 大表格截断 |
| 元数据 | 通过 MD 头部保留 | 以可读文本前缀拼入 `input`，同时 `metadata` 字段供 Milvus 入库 |
| Milvus 入库 | 回查源表获取元数据 | 直接从 JSONL 的 `metadata` 字段读取，无需回查 DB |
| chunk_size 单位 | token（8,000） | 字符数（4,000） |
| 文件拆分 | 各有不同 | 50,000 行/文件自动拆分 |

### 1.2 端到端流程

```
DB 查询行业研报记录（research_report 表）
  → 读取 MD 文件
  → 表格保护（<table> → 等长占位符，大表格截断至 4K 字符）
  → H2 标题分段
  → 短章节合并（相邻章节累加至接近 3,800 字符）
  → 超长章节递归切分（RecursiveCharacterTextSplitter）
  → 表格还原（占位符 → 原始/截断后的表格 HTML）
  → 短 chunk 后合并（正文 < 200 字的 chunk 并入相邻 chunk）
  → 拼入元数据前缀
  → 按 50,000 行/文件拆分写入 JSONL
  → 记录 embedding_batch_task
  → 提交百炼 Batch API 向量化（text-embedding-v4）
  → 向量化结果入库 Milvus（直接从 JSONL metadata 读取元数据）
```

---

## 二、数据源

### 2.1 数据表

| 表 | 关键字段 | 说明 |
|------|---------|------|
| `research_report` | `id` | 主键，用于 `source_id` 和 `custom_id` |
| `research_report` | `report_type` | 固定筛选条件 `= '行业研报'` |
| `research_report` | `trade_date` | 发布日期，用于日期范围筛选 |
| `research_report` | `md_locate` | MD 文件相对路径（基于 `md_dir`），筛选 `IS NOT NULL` |
| `research_report` | `title` | 研报标题，写入元数据 |
| `research_report` | `inst_csname` | 发布机构，写入元数据 |
| `research_report` | `ind_name` | 行业分类，写入元数据 |
| `research_report` | `author` | 分析师，写入元数据 |

### 2.2 筛选条件

```sql
WHERE report_type = '行业研报'
  AND md_locate IS NOT NULL AND md_locate != ''
  AND trade_date >= %s AND trade_date <= %s
ORDER BY trade_date ASC, id ASC
```

---

## 三、脚本与使用方法

| 文件 | 说明 |
|------|------|
| `src/text2jsonl/build_industry_report_jsonl.py` | JSONL 生成 |
| `scripts/build_industry_report_jsonl.sh` | Shell 执行入口 |
| `scripts/insert_vectors.sh` | 向量入库 Milvus |
| `conf/segmentation/industry_report_segmentation_conf.json` | 分段配置 |

### 3.1 生成 JSONL

```bash
# 默认区间 2025-01-01 至今
bash scripts/build_industry_report_jsonl.sh

# 指定起始日期
bash scripts/build_industry_report_jsonl.sh 2025-06-01

# 指定区间
bash scripts/build_industry_report_jsonl.sh 2025-01-01 2025-12-31
```

### 3.2 向量入库 Milvus

```bash
# 按数据源自动入库（找 status=completed + milvus_status=pending 的记录）
bash scripts/insert_vectors.sh -s industry_report

# 指定某条任务记录入库
bash scripts/insert_vectors.sh -t 40
```

---

## 四、分块策略

### 4.1 配置参数

读取 `conf/segmentation/industry_report_segmentation_conf.json` 的 `segmentation_rules`：

| 参数 | 值 | 说明 |
|------|-----|------|
| `max_chunk_size` | 4,000 字符 | 单 chunk 最大长度（字符数，非 token） |
| `chunk_overlap` | 200 字符 | 相邻 chunk 重叠区 |
| `separators` | `\n\n` → `\n` → `。` → `，` | RecursiveCharacterTextSplitter 递归分隔符优先级 |
| `keep_tables_intact` | true | 表格保护开关 |

实际切分时，`effective_max = max_chunk_size - 200`（预留元数据前缀空间），即 **3,800 字符**。

### 4.2 H2 标题分段

按 `## ` 正则拆分 MD 全文为独立章节：

```
# 标题                    → section=""（前言）
前言内容

## 行业概述               → section="行业概述"
行业概述正文

## 投资建议               → section="投资建议"
投资建议正文

## 风险提示               → section="风险提示"
风险提示正文
```

### 4.3 短章节合并

H2 拆分后，相邻短章节自动合并，直到累加长度接近 `effective_max`（3,800 字符）。避免一个 H2 段一个 chunk 的碎片化。

示例：前言（200 字）+ 行业概述（300 字）+ 投资建议（500 字）+ 风险提示（100 字）= 1,100 字 → 合并为 1 个 chunk。

### 4.4 递归切分

合并后仍超过 `effective_max` 的章节，使用 LangChain `RecursiveCharacterTextSplitter` 按分隔符优先级递归切分：

1. 先尝试按 `\n\n`（段落）切分
2. 不够则按 `\n`（行）切分
3. 再不够按 `。`（句号）切分
4. 最后按 `，`（逗号）切分

### 4.5 短 chunk 后合并

分块完成后，正文不足 200 字符的 chunk（通常为表格间的图表标题、数据来源等碎片文本）自动并入相邻 chunk：

- 优先向前合并（追加到上一个 chunk）
- 不可时向后合并（拼入下一个 chunk）
- 两侧均满载无法吸收时保留原样

---

## 五、表格处理

### 5.1 等长占位符保护

拆分前将 `<table>...</table>` 替换为 **等长占位符**（由 `__TABLE_PLACEHOLDER_{n}__` + `X` 填充至与截断后表格等长）。

```
原始表格（2,500 字符）
  → 截断（如超过 4,000 字符）
  → 生成等长占位符（2,500 个字符，全由 _ 和 X 组成）
  → splitter 按占位符真实大小计算切分点
  → 不在占位符内部切分（占位符不含 \n\n、\n、。、，等分隔符）
  → 拆分后将占位符还原为表格 HTML
```

等长占位符的关键作用：让 `RecursiveCharacterTextSplitter` 感知表格的真实大小，避免多张表格堆叠在同一个 chunk 中导致还原后 chunk 膨胀（之前短占位符方案导致单 chunk 高达 32K 字符）。

### 5.2 大表格截断

超过 4,000 字符的 HTML 数据表格（股票交付量、招投标明细等原始数据网格），截断为表头 + 前几行数据：

```html
<table>
  <tr><td>表头1</td><td>表头2</td></tr>
  <tr><td>数据1</td><td>数据2</td></tr>
  ... (保留前 N 行，直到接近 4,000 字符)
</table>
[表格已截断，保留前5行，原始约200行]
```

---

## 六、JSONL 格式

### 6.1 每行格式

```json
{
    "custom_id": "industry_report_12345_3",
    "method": "POST",
    "url": "/v1/embeddings",
    "body": {
        "model": "text-embedding-v4",
        "input": "标题：半导体行业深度报告\n作者：张三\n机构：中信证券\n发布时间：2025-06-15\n行业：半导体\n\n## 投资建议\n\n建议买入...",
        "dimensions": 1024
    },
    "metadata": {
        "source": "industry_report",
        "source_id": 12345,
        "title": "半导体行业深度报告",
        "publish_date": "2025-06-15",
        "institution": "中信证券",
        "industry": "半导体",
        "author": "张三",
        "report_type": "行业研报",
        "section": "投资建议",
        "chunk_index": 3,
        "chunk_count": 10
    }
}
```

### 6.2 custom_id 格式

```
industry_report_{source_id}_{chunk_index}
```

- `source_id`：`research_report` 表主键 `id`
- `chunk_index`：0-based 全局连续编号

### 6.3 元数据前缀

每个 chunk 的 `body.input` 开头拼入可读文本前缀，增强向量语义信号：

```
标题：{title}
作者：{author}
机构：{inst_csname}
发布时间：{trade_date}
行业：{ind_name}

{chunk正文}
```

缺失字段自动跳过（不输出空行）。前缀约占 80-150 字符，已在切分时预留 200 字符缓冲。

### 6.4 metadata 字段

`metadata` 字段独立于 `body`，入库 Milvus 时直接映射为标量字段：

| 字段 | 来源 | 说明 |
|------|------|------|
| `source` | 固定 | `"industry_report"` |
| `source_id` | DB `id` | 原始表主键 |
| `title` | DB `title` | 研报标题 |
| `publish_date` | DB `trade_date` | 发布日期 |
| `institution` | DB `inst_csname` | 发布机构 |
| `industry` | DB `ind_name` | 行业分类 |
| `author` | DB `author` | 分析师 |
| `report_type` | 固定 | `"行业研报"` |
| `section` | H2 标题原文 | 当前章节名（合并时取首个非空标题） |
| `chunk_index` | 程序 | 第几个 chunk（0-based） |
| `chunk_count` | 程序 | 该篇研报总 chunk 数 |

> **section 字段说明：** 当前为 H2 标题原文，尚未做标准化分类。后续可基于 `common_sections` 配置的关键词匹配归类为 `risk` / `investment_advice` / `toc` / `body` 等标准类别，用于 Milvus 过滤检索。

### 6.5 文件拆分

单文件超过 50,000 行时自动拆分，每个文件对应一条 `embedding_batch_task` 记录：

- 不拆分：`industry_report_202501_202606.jsonl`
- 拆分后：`industry_report_202501_202606_01.jsonl`、`_02.jsonl`、...

---

## 七、Milvus 入库

### 7.1 入库方案

行业研报采用 **B 方案（JSONL metadata 直接入库）**，与其他数据源的 A 方案（回查源表）不同：

| 方案 | 适用数据源 | 元数据来源 |
|------|-----------|-----------|
| A：回查源表 | npr, news, major_news 等 | `_query_source_metadata` 查询源表 |
| **B：JSONL metadata** | **industry_report** | 直接从输入 JSONL 的 `metadata` 字段读取 |

`insert_vectors.py` 中通过 `_SOURCE_META["industry_report"]["use_jsonl_metadata"] = True` 标记启用 B 方案。

### 7.2 字段截断

Milvus VARCHAR 的 `max_length` 按 **UTF-8 字节数**计算（中文每字 3 字节），入库前通过 `_truncate_field` 按字节截断：

```python
encoded = value.encode("utf-8")
if len(encoded) > max_len:
    return encoded[:max_len].decode("utf-8", errors="ignore")
```

各字段字节上限：

| 字段 | max_length（字节） | 约等于中文字符 |
|------|------------------|--------------|
| `title` | 500 | ~166 字 |
| `section` | 100 | ~33 字 |
| `institution` | 200 | ~66 字 |
| `industry` | 100 | ~33 字 |
| `report_type` | 20 | ~6 字 |

### 7.3 Milvus 字段映射

| Milvus 字段 | JSONL metadata 字段 | 说明 |
|------------|-------------------|------|
| `id` | `custom_id` | 主键 |
| `source` | `source` | `"industry_report"` |
| `source_id` | `source_id` | 原始表主键 |
| `title` | `title` | 研报标题 |
| `publish_datetime` | `publish_date` | 发布日期 |
| `content` | `body.input` | chunk 全文（含元数据前缀） |
| `vector` | Batch API 输出 | 1024 维向量 |
| `chunk_index` | `chunk_index` | 分块序号 |
| `chunk_count` | `chunk_count` | 总块数 |
| `section` | `section` | 章节名 |
| `institution` | `institution` | 发布机构 |
| `industry` | `industry` | 行业分类 |
| `report_type` | `report_type` | `"行业研报"` |

---

## 八、数据规模与费用

基于 2025-01 至 2026-06 全量数据的实际统计：

### 8.1 总览

| 指标 | 数值 |
|------|------|
| 研报数 | 27,440 篇 |
| 总 chunk 数 | 230,944 |
| 平均每篇 | 8.4 chunk |
| JSONL 文件数 | 5（按 50,000 行拆分） |
| JSONL 总大小 | ~1.28 GB |

### 8.2 chunk 长度分布

| 区间 | 数量 | 占比 |
|------|------|------|
| < 1K | 25,484 | 11.0% |
| 1K-2K | 30,745 | 13.3% |
| **2K-4K** | **163,453** | **70.8%** |
| 4K-6K | 11,262 | 4.9% |
| 6K-8K | 0 | 0% |
| 8K+ | 0 | 0% |

- P50 = 3,187 字符 | P90 = 3,885 字符 | max = 5,534 字符
- 70.8% 落在 2K-4K 理想区间，0% 超过 8K

### 8.3 表格统计

| 指标 | 数值 |
|------|------|
| 总表格数 | ~10,400 |
| 保留完整 | ~86.7% |
| 被截断（超 4K） | ~13.3% |

### 8.4 向量化费用

| 项目 | 数值 |
|------|------|
| 预估总 token | ~5.09 亿 |
| Batch API 单价 | 0.00035 元/千 token |
| **预估费用** | **~178 元** |

### 8.5 Milvus 入库

| 指标 | 数值 |
|------|------|
| 入库总数 | 230,944 条 |
| 任务数 | 5 |
| 全部状态 | `milvus=completed` |
| title 填充率 | 100% |
| section 填充率 | 99.2% |
| institution 填充率 | 100% |
| industry 填充率 | 98.6% |

---

## 九、召回实验

查询：`对于AI硬件设备各家机构的核心观点`

| 排名 | 相似度 | 机构 | 行业 | 章节 | 相关性 |
|------|--------|------|------|------|--------|
| #1 | 0.698 | 德硕管理咨询 | 互联网服务 | AI硬件的新时代：生态格局与发展方向 | 高 |
| #2 | 0.661 | 中国银河 | 半导体 | 硬件产业链：中场时刻，核心矛盾转向 | 高 |
| #3 | 0.659 | 爱建证券 | 半导体 | 高算力芯片市场格局 | 高 |
| #4 | 0.659 | 深企投 | 互联网服务 | AI 芯片 | 高 |
| #5 | 0.656 | 东海证券 | 通用设备 | 服务器功耗密度攀升，液冷散热技术 | 中 |
| #6 | 0.653 | 东吴证券 | 半导体 | 国外巨头仍占据大部分市场份额 | 高 |
| #7 | 0.648 | 国信证券 | 计算机设备 | 谷歌2026年芯片需求测算 | 高 |
| #8 | 0.647 | 山西证券 | 互联网服务 | 国产 AI 芯片加速追赶 | 高 |

Top 10 中 8 条高度相关，覆盖 8 家不同机构的 AI 硬件/芯片观点，section 字段有效区分了章节语义。2 条噪声来自德勤报告的致谢页（OCR 残留），后续可通过 section 标准化过滤无效章节。

---

## 十、输出目录

```
/mnt/f/batch_jsonl/
└── industry_report/
    └── 20260621/
        ├── industry_report_202501_202606_01.jsonl  (50,000 行, 276 MB)
        ├── industry_report_202501_202606_02.jsonl  (50,000 行, 273 MB)
        ├── industry_report_202501_202606_03.jsonl  (50,000 行, 275 MB)
        ├── industry_report_202501_202606_04.jsonl  (50,000 行, 280 MB)
        └── industry_report_202501_202606_05.jsonl  (30,944 行, 177 MB)
```

- 中间目录为运行日期（`YYYYMMDD`）
- 文件命名：`industry_report_{数据起始月}_{数据结束月}[_{序号}].jsonl`
- 不足 50,000 行时不带序号后缀

---

## 十一、关键常量

| 常量 | 值 | 说明 |
|------|-----|------|
| `_SOURCE` | `"industry_report"` | 数据源标识 |
| `_DEFAULT_START_DATE` | `"2025-01-01"` | 默认起始日期 |
| `_TARGET_MODEL` | `"text-embedding-v4"` | 目标模型 |
| `_TARGET_DIMENSIONS` | `1024` | 向量维度 |
| `_METADATA_PREFIX_BUFFER` | `200` | 元数据前缀预留字符数 |
| `_MAX_TABLE_CHARS` | `4000` | 单张表格最大字符数，超过截断 |
| `_MIN_CHUNK_CHARS` | `200` | chunk 正文最小字符数，不足则合并 |
| `_MAX_ROWS_PER_BATCH` | `50000` | 单文件最大行数，超过自动拆分 |

---

## 十二、配置文件

### 12.1 dir_conf.json

| 键 | 说明 |
|------|------|
| `jsonl_dir` | JSONL 输出根目录（`/mnt/f/batch_jsonl`） |
| `md_dir` | MD 文件根目录（`/mnt/e/files`） |

### 12.2 industry_report_segmentation_conf.json

```json
{
    "segmentation_rules": {
        "max_chunk_size": 4000,
        "chunk_overlap": 200,
        "separators": ["\n\n", "\n", "。", "，"],
        "keep_tables_intact": true,
        "merge_short_sections": true,
        "min_section_length": 50
    },
    "common_sections": [
        {"name": "summary", "keywords": ["摘要", "核心观点", "事件", "结论"]},
        {"name": "risk", "keywords": ["风险提示", "风险"]},
        {"name": "investment_advice", "keywords": ["投资建议", "投资策略"]},
        ...
    ]
}
```

---

## 十三、单元测试

```bash
# JSONL 生成
python unit_test/test_build_industry_report_jsonl.py

# 向量入库
python unit_test/test_insert_vectors.py
```

### 13.1 JSONL 生成测试（59 个用例）

| 测试类 | 用例数 | 覆盖内容 |
|--------|--------|----------|
| TestProtectTables | 4 | 单/多/无表格替换、带属性表格 |
| TestRestoreTables | 3 | 单/多表格还原、无占位符 |
| TestHasTablePlaceholder | 2 | 占位符检测 |
| TestTruncateTable | 4 | 小表格不截、大表格截断、闭合标签、自动截断 |
| TestSplitByH2 | 4 | 正常/无H2/仅H2/前言+H2 |
| TestMatchSectionName | 2 | 标题匹配、空标题 |
| TestMergeSections | 5 | 短章节合并、超限不合并、空列表、单章节、heading 保留 |
| TestMergeShortChunks | 5 | 向前/向后合并、超限不合并、单 chunk、重新编排索引 |
| TestBuildMetadataPrefix | 3 | 完整/部分/空元数据 |
| TestChunkReport | 6 | 单 chunk、表格保护、空内容、长文本拆分、多章节合并、索引连续 |
| TestMakeJsonlLine | 2 | JSONL 格式、metadata 字段完整性（含元数据前缀验证） |
| TestQueryIndustryReportRecords | 3 | 日期范围、无结果、无过滤 |
| TestBuildOutputPath | 3 | 正常路径、None 日期、带序号路径 |
| TestEnsureDateColumns | 2 | 字段存在/不存在 |
| TestCheckExistingCoverage | 3 | 未覆盖、已覆盖、source 参数 |
| TestInsertTaskRecord | 1 | 正常插入 |
| TestBuildIndustryReportJsonl | 5 | 正常生成、已覆盖跳过、无记录、空 MD、含表格 |
| TestCustomIdFormat | 2 | 格式校验、第 0 个 chunk |

### 13.2 向量入库测试（52 个用例）

覆盖 `parse_input_jsonl` 返回元组、`_build_milvus_record` 的 `input_meta` 分支、`_truncate_field` UTF-8 字节截断等场景。

---

## 十四、依赖

| 包 | 版本 | 用途 |
|------|------|------|
| `langchain-text-splitters` | 1.1.2 | `RecursiveCharacterTextSplitter` 递归切分 |

已添加至 `requirements.txt`。

---

## 十五、已知问题与后续优化

| 问题 | 现状 | 后续方案 |
|------|------|---------|
| section 未标准化 | H2 原文直接入库，存在 OCR 乱码和超长标题 | 基于 `common_sections` 关键词匹配归类为标准类别 |
| 德勤等英文报告噪声 | 致谢/免责声明页参与向量化 | section 标准化后可过滤 `acknowledgments` / `免责声明` |
| OCR 质量 | 部分研报 MD 文本含乱码 | 源头优化 OCR 转换质量 |
