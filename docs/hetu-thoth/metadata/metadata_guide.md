# Milvus 元数据字段说明

> 更新日期：2026-06-12 | 配置：`conf/segmentation/metadata_conf.json`

---

## 一、设计原则

所有大模型语料数据（共 8 张 GreatSQL 表）统一存入 **同一个 Milvus Collection**，通过 `source` 字段区分数据类型。

元数据字段分为两类：
- **通用字段（common_fields）**：所有 chunk 均包含的字段
- **扩展字段（extra_fields）**：不同数据源特有的字段

数据流：`GreatSQL 表` → `download_files` → `convert2md` → `segmentation（分块）` → `vectorization（向量化）` → `Milvus Collection`

---

## 二、通用字段

所有数据源的每个 chunk 均包含以下字段：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | VARCHAR(256) | ✓ | Milvus 主键，格式 `{source}_{source_id}_{chunk_index}` |
| `content` | VARCHAR(65535) | ✓ | 分块后的文本内容 |
| `vector` | FLOAT_VECTOR(1024) | | text-embedding-v4 向量，1024 维 |
| `source` | VARCHAR(32) | ✓ | 数据源标识，取值见第三节 |
| `source_id` | INT64 | ✓ | 来源表主键 ID |
| `title` | VARCHAR(500) | ✓ | 文档标题 |
| `publish_date` | VARCHAR(10) | ✓ | 发布日期，格式 YYYY-MM-DD |
| `chunk_index` | INT64 | ✓ | 当前 chunk 序号（0-based） |
| `chunk_count` | INT64 | ✓ | 本文档总 chunk 数 |
| `section` | VARCHAR(100) | ✓ | 分段类型（风险提示/投资建议/正文/问题/回复 等） |
| `token_count` | INT64 | | 该 chunk 的 token 数 |
| `file_path` | VARCHAR(1000) | | 原始/Markdown 文件路径 |

### 2.1 ID 生成规则

```
id = {source}_{source_id}_{chunk_index}
```

示例：
- `research_report_619401_8` — 研报 ID=619401 的第 9 个 chunk
- `anns_d_305201_0` — 公告 ID=305201 的第 1 个 chunk
- `npr_12001_0` — 政策 ID=12001 的第 1 个 chunk

---

## 三、数据源概览

| # | source 值 | 逻辑名称 | 来源表 | 记录数条件 | 向量化方式 |
|---|-----------|---------|--------|-----------|-----------|
| 1 | `npr` | 国家政策库 | `npr` | 全量 | 网页抓取 → MD → 分段 → 向量化 |
| 2 | `research_report` | 个股研报 | `research_report` | `report_type='个股研报'` | PDF → MD → 分段 → 向量化 |
| 3 | `research_report` | 行业研报 | `research_report` | `report_type='行业研报'` | PDF → MD → 分段 → 向量化 |
| 4 | `news` | 新闻快讯 | `news` | 全量 | 原文本 → 分段 → 向量化 |
| 5 | `major_news` | 新闻通讯 | `major_news` | 全量 | 原文本 → 分段 → 向量化 |
| 6 | `cctv_news` | 新闻联播文字稿 | `cctv_news` | 全量 | 原文本 → 分段 → 向量化 |
| 7 | `anns_d` | 上市公司公告 | `anns_d` | 全量 | PDF → MD → 分段 → 向量化 |
| 8 | `irm_qa_sh` | 上证e互动问答 | `irm_qa_sh` | 全量 | 原文本 → 分段 → 向量化 |
| 9 | `irm_qa_sz` | 深证易互动问答 | `irm_qa_sz` | 全量 | 原文本 → 分段 → 向量化 |

> 注：个股研报和行业研报均来自同一张 `research_report` 表，通过 `report_type` 字段区分，但使用相同的 `source` 值 `research_report`。

---

## 四、各数据源扩展字段详述

### 4.1 国家政策库（npr）

来源表 `npr`，分段类型为政策正文各级章节。

| 字段 | 列映射 | 说明 |
|------|-------|------|
| `publisher` | `puborg` | 发文机关，如"国务院办公厅" |
| `doc_id` | `pcode` | 发文字号，如"国办发〔2020〕35号" |
| `category` | `ptype` | 主题分类，如"财政、金融、审计\证券" |

日期映射：`publish_date` ← `npr.pubtime` (DATETIME)

### 4.2 券商研究报告（research_report）

来源表 `research_report`，覆盖个股研报和行业研报。

| 字段 | 列映射 | 说明 |
|------|-------|------|
| `stock_code` | `ts_code` | 股票代码，仅个股研报有值 |
| `stock_name` | `name` | 股票名称，仅个股研报有值 |
| `institution` | `inst_csname` | 发布机构，如"国金证券" |
| `industry` | `ind_name` | 行业分类，如"银行" |
| `author` | `author` | 分析师姓名 |
| `report_type` | `report_type` | 研报类别：`个股研报` / `行业研报` |

日期映射：`publish_date` ← `research_report.trade_date` (DATE YYYYMMDD)

### 4.3 新闻快讯（news）

来源表 `news`，短新闻文本。

| 字段 | 列映射 | 说明 |
|------|-------|------|
| `channel` | `channels` | 新闻频道分类 |

日期映射：`publish_date` ← `news.datetime` (DATETIME)

### 4.4 新闻通讯（major_news）

来源表 `major_news`，长篇通讯文本。

| 字段 | 列映射 | 说明 |
|------|-------|------|
| `src` | `src` | 来源网站（财联社、证券时报、新浪财经等） |

日期映射：`publish_date` ← `major_news.pub_time` (DATETIME)

### 4.5 新闻联播文字稿（cctv_news）

来源表 `cctv_news`，无额外扩展字段。

日期映射：`publish_date` ← `cctv_news.date` (DATE YYYYMMDD)

### 4.6 上市公司公告（anns_d）

来源表 `anns_d`，PDF 转 Markdown 后分段。

| 字段 | 列映射 | 说明 |
|------|-------|------|
| `stock_code` | `ts_code` | 股票代码 |
| `stock_name` | `name` | 股票名称 |
| `ann_type` | 由分词配置匹配 | 公告子类型：`resolution` / `equity_distribution` / `legal_opinion` 等 |

日期映射：`publish_date` ← `anns_d.ann_date` (DATE YYYYMMDD)

### 4.7 上证e互动问答（irm_qa_sh）

来源表 `irm_qa_sh`，一问一答文本，分段类型为 `问题` 和 `回复`。

| 字段 | 列映射 | 说明 |
|------|-------|------|
| `stock_code` | `ts_code` | 股票代码 |
| `stock_name` | `name` | 公司名称 |

日期映射：`publish_date` ← `irm_qa_sh.trade_date` (DATE YYYYMMDD)
内容构造：`q`（问题）和 `a`（回复）分别作为独立 chunk，通过 `section` 区分

### 4.8 深证易互动问答（irm_qa_sz）

来源表 `irm_qa_sz`，一问一答文本，分段类型为 `问题` 和 `回复`。

| 字段 | 列映射 | 说明 |
|------|-------|------|
| `stock_code` | `ts_code` | 股票代码 |
| `stock_name` | `name` | 公司名称 |
| `industry` | `industry` | 涉及行业（仅 irm_qa_sz 表有此字段） |

日期映射：`publish_date` ← `irm_qa_sz.trade_date` (DATE YYYYMMDD)
内容构造：`q`（问题）和 `a`（回复）分别作为独立 chunk，通过 `section` 区分

---

## 五、Milvus Collection Schema

### 5.1 字段设计

| 字段 | Milvus 类型 | 最大长度/维度 |
|------|------------|-------------|
| `id` | VARCHAR | 256 |
| `content` | VARCHAR | 65535 |
| `vector` | FLOAT_VECTOR | 1024 |
| `source` | VARCHAR | 32 |
| `source_id` | INT64 | — |
| `publish_date` | VARCHAR | 10 |
| `title` | VARCHAR | 500 |
| `chunk_index` | INT64 | — |
| `chunk_count` | INT64 | — |
| `section` | VARCHAR | 100 |
| `token_count` | INT64 | — |
| `file_path` | VARCHAR | 1000 |
| `stock_code` | VARCHAR | 20 |
| `stock_name` | VARCHAR | 100 |
| `institution` | VARCHAR | 200 |
| `industry` | VARCHAR | 100 |
| `author` | VARCHAR | 200 |
| `report_type` | VARCHAR | 20 |
| `ann_type` | VARCHAR | 50 |
| `publisher` | VARCHAR | 200 |
| `doc_id` | VARCHAR | 100 |
| `category` | VARCHAR | 50 |
| `channel` | VARCHAR | 50 |
| `src` | VARCHAR | 50 |

### 5.2 索引设计

- **向量索引**：`vector` 字段，`IP`（内积），`IVF_FLAT` 或 `IVF_SQ8`
- **标量索引**：`source`、`publish_date`、`stock_code`、`section` 等高频过滤字段

---

## 六、向量化方案

使用阿里 `text-embedding-v4` 的 OpenAI 兼容 Batch API：

| 参数 | 值 |
|------|------|
| 模型 | `text-embedding-v4` |
| 维度 | 1024 |
| 单价 | 0.00025 元/千 token |
| 方式 | JSONL 文件上传 → 创建 Batch 任务 → 轮询 → 下载结果 |

---

## 七、配置文件说明

元数据配置位于 `conf/segmentation/metadata_conf.json`，结构如下：

```
{
    "description": "配置文件说明",
    "common_fields": { ... },     // 所有数据源通用的 chunk 元数据字段
    "stock_report": { ... },      // 个股研报特有配置
    "industry_report": { ... },   // 行业研报特有配置
    "news": { ... },              // 新闻快讯特有配置
    "major_news": { ... },        // 新闻通讯特有配置
    "cctv_news": { ... },         // 新闻联播特有配置
    "announcement": { ... },      // 上市公司公告特有配置
    "policy": { ... },            // 国家政策库特有配置
    "irm_qa_sh": { ... },         // 上证e互动问答特有配置
    "irm_qa_sz": { ... },         // 深证易互动问答特有配置
    "usage_example": { ... }      // 使用示例
}
```

每个数据源配置包含：

| 属性 | 说明 |
|------|------|
| `source` | Milvus Collection 中的 `source` 字段值 |
| `source_table` | 对应的 GreatSQL 表名 |
| `condition` | 筛选条件（如有，如研报按 report_type 分） |
| `date_column` | 发布日期对应的 DB 列名 |
| `extra_fields` | 该数据源特有的扩展字段及其列映射 |

---

## 八、Chunk 示例

### 8.1 个股研报 chunk

```json
{
    "id": "research_report_619401_8",
    "content": "风险提示：下游需求复苏不及预期；新品导入不及预期；行业竞争加剧。",
    "source": "research_report",
    "source_id": 619401,
    "title": "中科蓝讯：Q3 业绩稳健增长，端侧应用合作持续深化",
    "publish_date": "2025-11-12",
    "stock_code": "688332.SH",
    "stock_name": "中科蓝讯",
    "institution": "华安证券",
    "industry": "半导体",
    "author": "陈耀波",
    "report_type": "个股研报",
    "section": "风险提示",
    "chunk_index": 8,
    "chunk_count": 12,
    "token_count": 128,
    "file_path": "个股研报/688332.SH/华安证券/20251112/H3_xxx.md"
}
```

### 8.2 投资者问答 chunk

```json
{
    "id": "irm_qa_sh_12345_1",
    "content": "尊敬的投资者您好，公司2024年度现金分红方案已经股东大会审议通过，将于近期实施。感谢您的关注。",
    "source": "irm_qa_sh",
    "source_id": 12345,
    "title": "投资者问答",
    "publish_date": "2024-03-15",
    "stock_code": "600519.SH",
    "stock_name": "贵州茅台",
    "section": "回复",
    "chunk_index": 1,
    "chunk_count": 2,
    "token_count": 96,
    "file_path": ""
}
```

### 8.3 政策 chunk

```json
{
    "id": "npr_12001_0",
    "content": "为进一步优化营商环境，降低企业用电成本……",
    "source": "npr",
    "source_id": 12001,
    "title": "关于深化燃煤发电上网电价形成机制改革的指导意见",
    "publish_date": "2023-10-15",
    "publisher": "国家发展改革委",
    "doc_id": "发改价格〔2023〕1651号",
    "category": "财政、金融、审计\\证券",
    "section": "正文",
    "chunk_index": 0,
    "chunk_count": 3,
    "token_count": 256,
    "file_path": "npr/20231015/xxx.md"
}
```

---

## 九、变更记录

| 日期 | 变更内容 |
|------|---------|
| 2026-06-12 | 新增 `irm_qa_sh`、`irm_qa_sz` 数据源；拆分 `news` 为独立的 news/major_news/cctv_news；新增 `token_count` 通用字段；统一 source 值为表名；字段 `source_site` 重命名为 `src` |
