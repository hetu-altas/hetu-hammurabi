# JSONL 批量生成指南

> 更新日期：2026-06-19 | 模块：`src/text2jsonl/`、`src/utils/util_jsonl_builder.py`

---

## 一、概述

将已转换为 Markdown 的结构化数据拼接为 `text-embedding-v4` Batch API 所需的 JSONL 格式文件，用于百炼 Batch 向量化。

### 1.1 整体流程

```
数据库记录 → 读取内容（MD文件 / DB字段 / Q&A拼接）→ token分块（超限自动切分）→ 拼接 JSONL → 存入 batch_jsonl 目录 → 记录任务到 embedding_batch_task
```

数据源按内容获取方式分为三类：

| 类别 | 数据源 | 内容来源 |
|------|--------|----------|
| MD 文件读取 | npr, stock_report, industry_report, anns_d | 从 `file_locate` 字段读取 Markdown 文件 |
| 数据库字段 | news, major_news, cctv_news | 直接从 `content` 字段读取 |
| Q&A 拼接 | irm_qa_sh, irm_qa_sz | 拼接 `trade_date` + `name` + `ts_code` + `q` + `a` |

### 1.2 JSONL 每行格式

```json
{
    "custom_id": "{source}_{id}" 或 "{source}_{id}_{n}",
    "method": "POST",
    "url": "/v1/embeddings",
    "body": {
        "model": "text-embedding-v4",
        "input": "# 标题\n\n**元数据字段**: 值\n\n---\n\n正文...",
        "encoding_format": "float"
    }
}
```

| 字段 | 说明 |
|------|------|
| `custom_id` | `{数据源}_{记录主键ID}`，超8K token分块时追加 `_{chunk序号}` |
| `model` | `text-embedding-v4` |
| `input` | 文本内容，分块时每个 chunk 保留元数据头 |
| `encoding_format` | `float` |

### 1.3 Token 分块

`text-embedding-v4` 单条上限 8,192 token。对 MD 类数据源，生成时自动检测 token 数，超限（8,000 token 阈值）按段落边界切分：

| 项目 | 说明 |
|------|------|
| 切分策略 | 先分离元数据头（`# 标题` ~ `---`），正文按 `\n\n` 段落边界累加，每块 ≤ 8,000 token |
| 元数据保留 | 每个 chunk 均带完整元数据头（标题、发文机关、日期），检索时不错失关键信号 |
| custom_id | 单 chunk: `npr_12345`；多 chunk: `npr_12345_0`, `npr_12345_1`, ... |
| 适用范围 | 所有 MD 类数据源（npr / stock_report / industry_report / anns_d） |

---

## 二、国家政策 (npr)

### 2.1 数据源

| 表 | 关键字段 | 说明 |
|------|---------|------|
| `npr` | `id` | 主键，用于 custom_id |
| `npr` | `pubtime` | 发布日期，用于日期范围筛选与去重 |
| `npr` | `file_locate` | MD 文件相对路径 |

### 2.2 脚本

| 文件 | 说明 |
|------|------|
| `src/text2jsonl/build_npr_jsonl.py` | 核心生成逻辑 |
| `scripts/build_npr_jsonl.sh` | Shell 执行入口 |

### 2.3 使用方法

```bash
# 默认区间 2024-07-01 至今
bash scripts/build_npr_jsonl.sh

# 指定区间
bash scripts/build_npr_jsonl.sh 2025-01-01 2025-12-31
```

### 2.4 数据规模

| 范围 | 原始记录 | JSONL 行数 | 说明 |
|------|-------|----------|------|
| 2024-07 至今 | ~710 | ~1,282 | 含 57 条长文拆分为 129 个 chunk |

> 多数政策 1-3 页不超 8K token。法规/条例原文（如矿产资源法实施条例 47K token）按段落切分，每块保留元数据头。

---

## 三、上证e互动问答 (irm_qa_sh)

### 3.1 数据源

| 表 | 关键字段 | 说明 |
|------|---------|------|
| `irm_qa_sh` | `id` | 主键，用于 custom_id |
| `irm_qa_sh` | `trade_date` | 发布日期，用于日期范围筛选与去重 |
| `irm_qa_sh` | `ts_code` | 股票代码，拼入 embedding input |
| `irm_qa_sh` | `name` | 公司名称，拼入 embedding input |
| `irm_qa_sh` | `q` | 问题，拼入 embedding input |
| `irm_qa_sh` | `a` | 回复，拼入 embedding input |

### 3.2 脚本

| 文件 | 说明 |
|------|------|
| `src/text2jsonl/build_irm_qa_sh_jsonl.py` | 核心生成逻辑 |
| `scripts/build_irm_qa_sh_jsonl.sh` | Shell 执行入口 |

### 3.3 使用方法

```bash
# 默认区间 2025-01-01 至今
bash scripts/build_irm_qa_sh_jsonl.sh

# 指定起始日期
bash scripts/build_irm_qa_sh_jsonl.sh 2025-06-01

# 指定区间
bash scripts/build_irm_qa_sh_jsonl.sh 2025-01-01 2025-12-31
```

### 3.4 数据规模

| 范围 | 记录数 | 文件数 | 说明 |
|------|-------|-------|------|
| 2025-01 至今 | 108,856 | 3 | 按 50,000 行/文件拆分，不在同一天内切割 |

### 3.5 Embedding Input 格式

```
[{trade_date}] {name}（{ts_code}）
问：{q}
答：{a}
```

> 将日期、公司名称、股票代码显式拼入 input，以增强语义检索精度。同一只股票的不同时间 Q&A 在向量空间上更接近。

---

## 四、深证易互动问答 (irm_qa_sz)

### 4.1 数据源

| 表 | 关键字段 | 说明 |
|------|---------|------|
| `irm_qa_sz` | `id` | 主键，用于 custom_id |
| `irm_qa_sz` | `trade_date` | 发布日期 |
| `irm_qa_sz` | `ts_code` | 股票代码 |
| `irm_qa_sz` | `name` | 公司名称 |
| `irm_qa_sz` | `q` | 问题 |
| `irm_qa_sz` | `a` | 回复 |

> 与 `irm_qa_sh` 表结构一致，额外包含 `industry`（涉及行业）字段。

### 4.2 脚本

| 文件 | 说明 |
|------|------|
| `src/text2jsonl/build_irm_qa_sz_jsonl.py` | 核心生成逻辑 |
| `scripts/build_irm_qa_sz_jsonl.sh` | Shell 执行入口 |

### 4.3 使用方法

```bash
# 默认区间 2025-01-01 至今
bash scripts/build_irm_qa_sz_jsonl.sh

# 指定区间
bash scripts/build_irm_qa_sz_jsonl.sh 2025-01-01 2025-12-31
```

### 4.4 数据规模

| 范围 | 记录数 | 文件数 | 说明 |
|------|-------|-------|------|
| 2025-01 至今 | 107,404 | 3 | 按 50,000 行/文件拆分，不在同一天内切割 |

### 4.5 Embedding Input 格式

与 irm_qa_sh 相同：

```
[{trade_date}] {name}（{ts_code}）
问：{q}
答：{a}
```

---

## 五、新闻快讯 (news)

### 5.1 数据源

| 表 | 关键字段 | 说明 |
|------|---------|------|
| `news` | `id` | 主键，用于 custom_id |
| `news` | `datetime` | 发布时间，用于日期范围筛选与分批 |
| `news` | `channels` | 板块分类，拼入 embedding input |
| `news` | `title` | 标题 |
| `news` | `content` | 正文内容 |

### 5.2 脚本

| 文件 | 说明 |
|------|------|
| `src/text2jsonl/build_news_jsonl.py` | 核心生成逻辑 |
| `scripts/build_news_jsonl.sh` | Shell 执行入口 |

### 5.3 使用方法

```bash
# 默认区间 2026-05-01 至今
bash scripts/build_news_jsonl.sh

# 指定起始日期
bash scripts/build_news_jsonl.sh 2026-06-01

# 指定区间
bash scripts/build_news_jsonl.sh 2026-05-01 2026-05-31
```

### 5.4 数据规模

| 范围 | 原始记录数 | 去重后 | 文件数 | 说明 |
|------|--------|-------|-------|------|
| 2026-05 至今 | ~524,368 | ~149,901 | ~3 | 按 content 去重，按 50,000 行/文件拆分 |

> 查询时通过 `GROUP BY content` + `MIN(id)` 按 content 去重，过滤约 71.4% 的重复数据。按月分组，单月超 50,000 行时按天继续拆分。从 DB `content` 字段直接读取，无需 MD 文件。

### 5.5 Embedding Input 格式

```
板块：{channels}
发布时间：{datetime}

{content}
```

> 将板块和发布时间拼入 input，以增强语义检索精度。时间格式为 `YYYY-MM-DD HH:MM:SS`。空 content 的记录在 SQL 层已过滤，不参与生成。

### 5.6 输出目录结构

```
/mnt/f/batch_jsonl/
└── news/
    ├── 202605/
    │   ├── news_202605_01.jsonl
    │   ├── news_202605_02.jsonl
    │   └── ...
    └── 202606/
        └── news_202606_01.jsonl
```

> 中间目录为数据月份（`YYYYMM`），文件命名为 `news_{数据月份}_{序号}.jsonl`。

---

## 六、新闻通讯 (major_news)

### 6.1 数据源

| 表 | 关键字段 | 说明 |
|------|---------|------|
| `major_news` | `id` | 主键，用于 custom_id |
| `major_news` | `pub_time` | 发布时间，用于日期范围筛选与分批 |
| `major_news` | `title` | 标题，拼入 embedding input |
| `major_news` | `src` | 来源网站（财联社/证券时报/新浪财经等），拼入 embedding input |
| `major_news` | `content` | 正文内容 |

### 6.2 脚本

| 文件 | 说明 |
|------|------|
| `src/text2jsonl/build_major_news_jsonl.py` | 核心生成逻辑 |
| `scripts/build_major_news_jsonl.sh` | Shell 执行入口 |

### 6.3 使用方法

```bash
# 默认区间 2026-05-01 至今
bash scripts/build_major_news_jsonl.sh

# 指定区间
bash scripts/build_major_news_jsonl.sh 2026-05-01 2026-05-31
```

### 6.4 数据规模

| 范围 | 记录数 | 文件数 | 说明 |
|------|-------|-------|------|
| 2026-05 至今 | ~83,318 | 2 | 按 50,000 行/文件拆分 |

> 按月分组，单月超 50,000 行时按天继续拆分。从 DB `content` 字段直接读取，无需 MD 文件。

### 6.5 Embedding Input 格式

```
标题：{title}
发布时间：{pub_time}
来源：{src}
{content}
```

> content 为富文本（含 HTML 标签），向量化前需由 `util_jsonl_builder` 做文本清洗或直接保留原始格式。

### 6.6 输出目录结构

```
/mnt/f/batch_jsonl/
└── major_news/
    └── 20260613/
        ├── major_news_202605_01.jsonl
        └── major_news_202605_02.jsonl
```

> 中间目录为当天运行日期（`YYYYMMDD`），文件命名为 `major_news_{数据月份}_{序号}.jsonl`。

---

## 七、新闻联播 (cctv_news)

### 7.1 数据源

| 表 | 关键字段 | 说明 |
|------|---------|------|
| `cctv_news` | `id` | 主键，用于 custom_id |
| `cctv_news` | `date` | 播出日期，用于日期范围筛选 |
| `cctv_news` | `title` | 标题，拼入 embedding input |
| `cctv_news` | `content` | 文字稿正文 |

### 7.2 脚本

| 文件 | 说明 |
|------|------|
| `src/text2jsonl/build_cctv_news_jsonl.py` | 核心生成逻辑 |
| `scripts/build_cctv_news_jsonl.sh` | Shell 执行入口 |

### 7.3 使用方法

```bash
# 默认区间 2025-01-01 至今
bash scripts/build_cctv_news_jsonl.sh

# 指定起始日期
bash scripts/build_cctv_news_jsonl.sh 2025-06-01

# 指定区间
bash scripts/build_cctv_news_jsonl.sh 2025-01-01 2025-12-31
```

### 7.4 数据规模

| 范围 | 记录数 | 文件数 | 说明 |
|------|-------|-------|------|
| 2025-01 至今 | ~7,184 | 1 | 远低于 50,000 行上限，单 JSONL 文件 |

> 从 DB `content` 字段直接读取，无需 MD 文件。数据量小，不拆分。

### 7.5 Embedding Input 格式

```
{title}
{date}
{content}
```

> 将标题和播出日期拼入 input，以 `\n` 切分。空 content 的记录在 SQL 层已过滤，不参与生成。

### 7.6 输出目录结构

```
/mnt/f/batch_jsonl/
└── cctv_news/
    └── 20260613/
        └── cctv_news_2025_2026.jsonl
```

> 中间目录为当天运行日期（`YYYYMMDD`），文件命名为 `cctv_news_{起始年份}_{结束年份}.jsonl`。

---

## 八、日期去重机制

生成 JSONL 时向 `embedding_batch_task` 表记录该批次覆盖的 **数据时间范围**（`data_start_date` / `data_end_date`），后续运行前查重：

| 字段 | 说明 |
|------|------|
| `data_start_date` | 该批次数据的最早日期（npr 为 `pubtime`，QA 类为 `trade_date`） |
| `data_end_date` | 该批次数据的最晚日期 |

若目标日期区间与 `pending` / `uploaded` / `validating` / `in_progress` / `finalizing` / `completed` 状态的任务存在重叠，则跳过生成。

### 首次部署字段自动补齐

各 `build_*_jsonl.py` 运行时自动检测并添加 `data_start_date` / `data_end_date` 列，无需手动 DDL。

---

## 九、代码结构

```python
# 以 build_irm_qa_sh_jsonl.py 为例
_load_dir_config()              # 加载 dir_conf.json
_ensure_date_columns(db)        # 自动补齐日期字段
_check_existing_coverage()      # 查重（日期区间去重）
query_irm_qa_sh_records(db)     # 查询记录
_to_embedding_input(record)     # 构建 input: [date] name（code）\n问：Q\n答：A
_split_records_into_chunks()    # 按 trade_date 分组后累积到 50,000 行切块，不跨天切割
_build_output_path(...)         # 构建输出路径
_insert_task_record(...)        # 写入任务追踪记录

# 主入口
build_irm_qa_sh_jsonl(start_date=None, end_date=None)

# 内容构建使用 util_jsonl_builder.build_jsonl_from_records()
```

### 9.1 公共 JSONL 构建（util_jsonl_builder.py）

所有数据源共用，根据数据源类型自动选择内容读取策略：
- **MD 文件读取**：从 `file_locate` 读取 Markdown 文件内容，自动 token 检测与段落切分
- **数据库字段**：直接读 `content` 字段（通过 `build_jsonl_from_records()`）
- **Q&A 拼接**：拼接 `q + "\n" + a`（通过 `build_jsonl()`）

核心分块函数：
- `_chunk_content(content, source_id, source, model)` — token 检测 + 段落切分
- `_split_markdown_header_body(content)` — 分离元数据头与正文
- `_make_jsonl_line(source_id, source, content, model, chunk_index)` — 构建 JSONL 行

新增数据源只需传入 `records`（含 `id` 及对应内容字段）即可复用。

---

## 十、配置

### 10.1 dir_conf.json

| 键 | 说明 | 示例 |
|------|------|------|
| `jsonl_dir` | JSONL 输出根目录 | `/mnt/f/batch_jsonl` |
| `md_dir` | Markdown 文件根目录 | `/mnt/e/files` |

### 10.2 输出结构

```
/mnt/f/batch_jsonl/
├── news/                        # 新闻快讯
│   ├── 202605/
│   │   ├── news_202605_01.jsonl
│   │   └── news_202605_02.jsonl
│   └── 202606/
│       └── news_202606_01.jsonl
├── npr/                        # 国家政策
│   └── 20260613/
│       └── npr_202410_202606.jsonl
├── major_news/                  # 新闻通讯
│   └── 20260613/
│       ├── major_news_202605_01.jsonl
│       └── major_news_202605_02.jsonl
├── cctv_news/                   # 新闻联播
│   └── 20260613/
│       └── cctv_news_2025_2026.jsonl
├── irm_qa_sh/                  # 上证e互动问答
│   └── 20260613/
│       ├── irm_qa_sh_2025_01.jsonl
│       ├── irm_qa_sh_2025_02.jsonl
│       └── irm_qa_sh_2025_03.jsonl
└── irm_qa_sz/                  # 深证易互动问答
    └── 20260613/
        ├── irm_qa_sz_2025_01.jsonl
        ├── irm_qa_sz_2025_02.jsonl
        └── irm_qa_sz_2025_03.jsonl
```

---

## 十一、单元测试

```bash
# 国家政策
python unit_test/test_build_npr_jsonl.py

# 新闻快讯
python unit_test/test_build_news_jsonl.py

# 新闻通讯
python unit_test/test_build_major_news_jsonl.py

# 新闻联播
python unit_test/test_build_cctv_news_jsonl.py

# 上证e互动问答
python unit_test/test_build_irm_qa_sh_jsonl.py

# 深证易互动问答
python unit_test/test_build_irm_qa_sz_jsonl.py
```

覆盖场景：正常生成、多文件拆分、已有覆盖跳过、部分覆盖、无记录、日期字段自动补齐、custom_id 格式校验、embedding input 格式。

---

## 十二、向量化回写

Batch API 返回每条结果都带 `custom_id`，格式为 `{source}_{id}` 或 `{source}_{id}_{n}`（分块），解析出 `id` 后：

1. 回查原表获取元数据（`title`、`pubtime`、`puborg`、`pcode`、`ptype` 等）
2. 与向量一起写入 Milvus，`id` 作为唯一关联键
3. 分块记录的多个 chunk 共享同一个 `id`，检索时去重即可
