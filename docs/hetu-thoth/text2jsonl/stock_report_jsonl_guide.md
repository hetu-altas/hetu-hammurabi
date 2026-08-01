# 个股研报分块生成 JSONL

> 更新日期：2026-06-21 | 模块：`src/text2jsonl/build_stock_report_jsonl.py`

---

## 一、概述

将个股研报 Markdown 文件按 H2 标题分段，使用 LangChain `RecursiveCharacterTextSplitter` 递归切分后，生成 `text-embedding-v4` Batch API 所需的 JSONL 格式文件。

### 1.1 与行业研报的关系

个股研报与行业研报采用相同的分块策略（H2 分段 + 短章节合并 + 递归切分 + 表格保护），核心差异在于数据源筛选和元数据字段：

| 项目 | 行业研报 | 个股研报 |
|------|---------|---------|
| 筛选条件 | `report_type = '行业研报'` | `report_type = '个股研报'` |
| 额外字段 | - | `stock_code`（ts_code）、`stock_name`（name） |
| 元数据前缀 | 标题/作者/机构/发布时间/行业 | 标题/作者/机构/发布时间/股票代码/股票名称/行业 |
| `source` | `industry_report` | `stock_report` |
| 配置文件 | `industry_report_segmentation_conf.json` | `stock_report_segmentation_conf.json` |

### 1.2 处理流程

```
DB 查询个股研报记录（含 ts_code / name）
  → 读取 MD 文件
  → 表格保护（<table> → 等长占位符，大表格截断至 4K 字符）
  → H2 标题分段
  → 短章节合并（相邻章节累加至接近 3,800 字符）
  → 超长章节递归切分（RecursiveCharacterTextSplitter）
  → 表格还原（占位符 → 原始/截断后的表格 HTML）
  → 短 chunk 后合并（正文 < 200 字的 chunk 并入相邻 chunk）
  → 拼入元数据前缀
  → JSONL 文件切分（每文件 ≤ 50,000 行）
  → 写入 JSONL + 记录 embedding_batch_task
```

---

## 二、数据源

### 2.1 数据表

| 表 | 关键字段 | 说明 |
|------|---------|------|
| `research_report` | `id` | 主键，用于 `source_id` 和 `custom_id` |
| `research_report` | `report_type` | 固定筛选条件 `= '个股研报'` |
| `research_report` | `trade_date` | 发布日期，用于日期范围筛选 |
| `research_report` | `md_locate` | MD 文件相对路径（基于 `md_dir`），筛选 `IS NOT NULL` |
| `research_report` | `title` | 研报标题，写入元数据 |
| `research_report` | `inst_csname` | 发布机构，写入元数据 |
| `research_report` | `ind_name` | 行业分类，写入元数据 |
| `research_report` | `author` | 分析师，写入元数据 |
| `research_report` | `ts_code` | 股票代码，写入元数据 |
| `research_report` | `name` | 股票名称，写入元数据 |

### 2.2 筛选条件

```sql
WHERE report_type = '个股研报'
  AND md_locate IS NOT NULL AND md_locate != ''
  AND trade_date >= %s AND trade_date <= %s
ORDER BY trade_date ASC, id ASC
```

---

## 三、脚本

| 文件 | 说明 |
|------|------|
| `src/text2jsonl/build_stock_report_jsonl.py` | 核心生成逻辑 |
| `scripts/build_stock_report_jsonl.sh` | Shell 执行入口 |
| `conf/segmentation/stock_report_segmentation_conf.json` | 分段配置 |

### 3.1 使用方法

```bash
# 默认区间 2025-01-01 至今
bash scripts/build_stock_report_jsonl.sh

# 指定起始日期
bash scripts/build_stock_report_jsonl.sh 2025-06-01

# 指定区间
bash scripts/build_stock_report_jsonl.sh 2025-01-01 2025-12-31
```

Python 直接调用：

```bash
python src/text2jsonl/build_stock_report_jsonl.py --start-date 2025-01-01 --end-date 2025-12-31
```

---

## 四、分块策略

### 4.1 配置参数

读取 `conf/segmentation/stock_report_segmentation_conf.json` 的 `segmentation_rules`：

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

## 公司概况               → section="公司概况"
公司概况正文

## 投资建议               → section="投资建议"
投资建议正文

## 风险提示               → section="风险提示"
风险提示正文
```

### 4.3 短章节合并

H2 拆分后，相邻短章节自动合并，直到累加长度接近 `effective_max`（3,800 字符）。避免一个 H2 段一个 chunk 的碎片化。

### 4.4 递归切分

合并后仍超过 `effective_max` 的章节，使用 LangChain `RecursiveCharacterTextSplitter` 按分隔符优先级递归切分：

1. 先尝试按 `\n\n`（段落）切分
2. 不够则按 `\n`（行）切分
3. 再不够按 `。`（句号）切分
4. 最后按 `，`（逗号）切分

### 4.5 短 chunk 后合并

分块完成后，正文不足 200 字符的 chunk 自动并入相邻 chunk：

- 优先向前合并（追加到上一个 chunk）
- 不可时向后合并（拼入下一个 chunk）
- 两侧均满载无法吸收时保留原样

---

## 五、表格处理

### 5.1 表格保护

拆分前将 `<table>...</table>` 替换为**等长占位符**（由 `__TABLE_PLACEHOLDER_{n}__` + `X` 填充至与表格等长），确保 `RecursiveCharacterTextSplitter` 按真实大小计算切分点。拆分后将占位符还原为原始表格。

```
原始表格（2,500 字符） → 占位符（2,500 字符，不含任何分隔符）
                        → splitter 将其视为一个不可分割的整体
                        → 拆分后还原为原始表格
```

关键：占位符仅由 `_` 和 `X` 组成，不包含 `\n\n`、`\n`、`。`、`，` 等分隔符，因此 splitter 不会在表格内部切分。

### 5.2 大表格截断

超过 4,000 字符的 HTML 数据表格截断为表头 + 前几行数据：

```html
<table>
  <tr><td>表头1</td><td>表头2</td></tr>
  <tr><td>数据1</td><td>数据2</td></tr>
  ... (保留前 N 行，直到接近 4,000 字符)
</table>
[表格已截断，保留前5行，原始约200行]
```

### 5.3 实际数据统计

| 指标 | 数值 |
|------|------|
| 总表格数 | 2,237 |
| 保留完整 | 2,195（98.1%） |
| 被截断 | 42（1.9%） |

---

## 六、JSONL 格式

### 6.1 每行格式

```json
{
    "custom_id": "stock_report_12345_3",
    "method": "POST",
    "url": "/v1/embeddings",
    "body": {
        "model": "text-embedding-v4",
        "input": "标题：平安银行深度报告\n作者：张三\n机构：中信证券\n发布时间：2025-06-15\n股票代码：000001.SZ\n股票名称：平安银行\n行业：银行\n\n## 投资建议\n\n建议买入...",
        "dimensions": 1024
    },
    "metadata": {
        "source": "stock_report",
        "source_id": 12345,
        "title": "平安银行深度报告",
        "publish_date": "2025-06-15",
        "stock_code": "000001.SZ",
        "stock_name": "平安银行",
        "institution": "中信证券",
        "industry": "银行",
        "author": "张三",
        "report_type": "个股研报",
        "section": "投资建议",
        "chunk_index": 3,
        "chunk_count": 10
    }
}
```

### 6.2 custom_id 格式

```
stock_report_{source_id}_{chunk_index}
```

- `source_id`：`research_report` 表主键 `id`
- `chunk_index`：0-based 全局连续编号

### 6.3 元数据前缀

每个 chunk 的 `body.input` 开头拼入可读文本前缀：

```
标题：{title}
作者：{author}
机构：{inst_csname}
发布时间：{trade_date}
股票代码：{ts_code}
股票名称：{name}
行业：{ind_name}

{chunk正文}
```

缺失字段自动跳过（不输出空行）。前缀约占 100-200 字符，已在切分时预留 200 字符缓冲。

### 6.4 metadata 字段

`metadata` 字段独立于 `body`，后续入库 Milvus 时直接映射为标量字段：

| 字段 | 来源 | 说明 |
|------|------|------|
| `source` | 固定 | `"stock_report"` |
| `source_id` | DB `id` | 原始表主键 |
| `title` | DB `title` | 研报标题 |
| `publish_date` | DB `trade_date` | 发布日期 |
| `stock_code` | DB `ts_code` | 股票代码 |
| `stock_name` | DB `name` | 股票名称 |
| `institution` | DB `inst_csname` | 发布机构 |
| `industry` | DB `ind_name` | 行业分类 |
| `author` | DB `author` | 分析师 |
| `report_type` | 固定 | `"个股研报"` |
| `section` | H2 标题原文 | 当前章节名（合并时取首个非空标题） |
| `chunk_index` | 程序 | 第几个 chunk（0-based） |
| `chunk_count` | 程序 | 该篇研报总 chunk 数 |

---

## 七、JSONL 文件切分

当总行数超过 50,000 时自动切分为多个文件：

| 参数 | 值 |
|------|------|
| `_MAX_LINES_PER_FILE` | 50,000 |
| 单文件命名 | `stock_report_{start}_{end}.jsonl` |
| 多文件命名 | `stock_report_{start}_{end}_001.jsonl`、`_002.jsonl`、... |

每个文件独立插入一条 `embedding_batch_task` 记录。返回值中 `output_paths` 为路径列表，`file_count` 为文件数。

---

## 八、数据规模

基于 2026 年 6 月数据的实际统计（2026-05 ~ 2026-06 区间）：

| 指标 | 数值 |
|------|------|
| 研报数 | 285 篇 |
| 总 chunk 数 | 1,802 |
| 平均每篇 | 6.3 chunk |
| JSONL 文件大小 | ~8.5 MB |

### 8.1 chunk 长度分布

| 区间 | 数量 | 占比 |
|------|------|------|
| < 1K | 64 | 3.6% |
| 1K-2K | 384 | 21.3% |
| **2K-4K** | **1,318** | **73.1%** |
| 4K-6K | 36 | 2.0% |
| 6K+ | 0 | 0% |

- avg = 2,646 字符 | max = 4,153 字符
- 超 4,000 字符的 36 个 chunk 均因元数据前缀（~100-200 字）轻微超限

---

## 九、输出目录

```
/mnt/f/batch_jsonl/
└── stock_report/
    └── 20260621/
        └── stock_report_202605_202606.jsonl
```

- 中间目录为运行日期（`YYYYMMDD`）
- 文件命名：`stock_report_{数据起始月}_{数据结束月}.jsonl`

---

## 十、关键常量

| 常量 | 值 | 说明 |
|------|-----|------|
| `_SOURCE` | `"stock_report"` | 数据源标识 |
| `_DEFAULT_START_DATE` | `"2025-01-01"` | 默认起始日期 |
| `_TARGET_MODEL` | `"text-embedding-v4"` | 目标模型 |
| `_TARGET_DIMENSIONS` | `1024` | 向量维度 |
| `_METADATA_PREFIX_BUFFER` | `200` | 元数据前缀预留字符数 |
| `_MAX_TABLE_CHARS` | `4000` | 单张表格最大字符数，超过截断 |
| `_MIN_CHUNK_CHARS` | `200` | chunk 正文最小字符数，不足则合并 |
| `_MAX_LINES_PER_FILE` | `50000` | 单文件最大行数，超过切分 |

---

## 十一、配置文件

### 11.1 dir_conf.json

| 键 | 说明 |
|------|------|
| `jsonl_dir` | JSONL 输出根目录（`/mnt/f/batch_jsonl`） |
| `md_dir` | MD 文件根目录（`/mnt/e/files`） |

### 11.2 stock_report_segmentation_conf.json

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
        {"name": "rating", "keywords": ["评级", "增持", "买入", "中性"]},
        {"name": "earnings_forecast", "keywords": ["盈利预测", "EPS", "PE", "营收"]},
        {"name": "investment_advice", "keywords": ["投资建议", "投资要点"]},
        {"name": "risk", "keywords": ["风险提示", "风险"]},
        ...
    ]
}
```

---

## 十二、Milvus 入库

`src/indexing/insert_vectors.py` 已支持 `stock_report` 数据源：

- `_VALID_SOURCES` 包含 `"stock_report"`
- `_SOURCE_META` 配置 `use_jsonl_metadata: True`，入库时直接读取 JSONL 中的 `metadata` 字段
- 入库命令：`python src/indexing/insert_vectors.py -s stock_report`

---

## 十三、召回验证

使用查询 "针对比亚迪，请给出各家机构近期对于比亚迪基本面的预测情况" 进行召回实验，Top 20 结果：

- 全部命中比亚迪（002594.SZ），无噪声
- 覆盖 8 家机构：海通国际、东莞证券、群益证券、浦银国际、民生证券、信达证券、国元证券、东吴证券
- 时间跨度 2025-01 ~ 2025-11
- 相似度分数范围：0.676 ~ 0.705（IP 度量）
- 内容覆盖：盈利预测、销量分析、智驾技术、海外扩张、财务数据等维度

---

## 十四、单元测试

```bash
python unit_test/test_build_stock_report_jsonl.py
```

63 个用例，覆盖场景：

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
| TestBuildMetadataPrefix | 3 | 完整/部分/空元数据（含股票代码和名称） |
| TestChunkReport | 6 | 单 chunk、表格保护、空内容、长文本拆分、多章节合并、索引连续 |
| TestMakeJsonlLine | 2 | JSONL 格式、metadata 字段完整性（含 stock_code / stock_name） |
| TestQueryStockReportRecords | 3 | 日期范围、无结果、无过滤 |
| TestBuildOutputPath | 4 | 正常路径、None 日期、带序号、多序号 |
| TestEnsureDateColumns | 2 | 字段存在/不存在 |
| TestCheckExistingCoverage | 3 | 未覆盖、已覆盖、source 参数 |
| TestInsertTaskRecord | 1 | 正常插入 |
| TestBuildStockReportJsonl | 5 | 正常生成、已覆盖跳过、无记录、空 MD、含表格 |
| TestFileSplitting | 3 | 多文件切分、未超限不切分、多文件任务记录 |
| TestCustomIdFormat | 2 | 格式校验、第 0 个 chunk |

---

## 十五、依赖

| 包 | 版本 | 用途 |
|------|------|------|
| `langchain-text-splitters` | 1.1.2 | `RecursiveCharacterTextSplitter` 递归切分 |

已添加至 `requirements.txt`。
