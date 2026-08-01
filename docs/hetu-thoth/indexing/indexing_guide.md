# 向量化结果入库 Milvus 指南

> 更新日期：2026-06-19 | 模块：`src/indexing/`、`scripts/insert_vectors.sh`

---

## 一、概述

将 Batch API 返回的 embedding 向量 JSONL 解析后，与源表元数据一起插入 Milvus Collection `thoth_knowledge`，实现知识库的向量检索能力。

### 1.1 整体流程

```
embedding_batch_task（status=completed）
  → 读取输出 JSONL（custom_id + embedding）
  → 读取输入 JSONL（custom_id + body.input 原文）
  → 按 custom_id 前缀路由到源表，批量查询元数据
  → 检查 Milvus 已有 ID（去重）
  → 分批插入 Milvus（每批 ≤ 1000 条）
  → 更新源表 embedding_done 标记
  → 更新 embedding_batch_task.milvus_status
```

### 1.2 与上游模块的关系

```
text2jsonl（生成输入 JSONL）
  → submit_batch_embedding（提交 Batch API）
  → poll + finalize（轮询 + 下载结果 JSONL）
  → insert_vectors（本模块：结果入库 Milvus）  ← 当前位置
```

---

## 二、使用方法

### 2.1 Shell 脚本

```bash
# 按数据源入库（自动找 status=completed 且 milvus_status 为 pending/failed 的记录）
bash scripts/insert_vectors.sh -s npr

# 指定单条 embedding_batch_task.id 入库
bash scripts/insert_vectors.sh -t 42
```

### 2.2 参数说明

| 参数 | 说明 |
|------|------|
| `-s <source>` | 按数据源批量入库，遍历所有待入库任务 |
| `-t <task_id>` | 指定 `embedding_batch_task.id`，处理单条任务 |

`-s` 模式自动拉取的条件：`status = 'completed'` AND `milvus_status IN ('pending', 'failed') OR NULL`。

`-t` 模式不检查状态，可用于重试任意任务。

### 2.3 输出示例

```
[npr] 找到 1 条待入库任务
  处理任务 id=12, output=/mnt/f/embedding_jsonl/npr/20260619/npr_202407_202606_output.jsonl

========================================
插入统计:
  总数:   1282
  成功:   1282
  跳过:   0
  失败:   0
========================================
```

---

## 三、custom_id 路由规则

每条向量结果通过 `custom_id` 前缀路由到对应源表查询元数据：

| 前缀 | 源表 | 查询字段 | 映射到 Milvus 字段 |
|------|------|---------|-------------------|
| `npr_` | npr | pubtime, title, puborg | publish_date, title, publisher |
| `news_` | news | datetime, title, channels | publish_date, title, channel |
| `major_news_` | major_news | pub_time, title, src | publish_date, title, src |
| `cctv_news_` | cctv_news | date, title | publish_date, title |
| `irm_qa_sh_` | irm_qa_sh | trade_date, ts_code, name | publish_date, stock_code, stock_name |
| `irm_qa_sz_` | irm_qa_sz | trade_date, ts_code, name | publish_date, stock_code, stock_name |

### 3.1 custom_id 格式

| 格式 | 说明 | 示例 |
|------|------|------|
| `{source}_{id}` | 单 chunk | `npr_12345` |
| `{source}_{id}_{n}` | 多 chunk（长文切分） | `npr_12345_0`, `npr_12345_1` |

解析由 `util_jsonl_builder.parse_custom_id()` 完成，支持含下划线的 source 名称（如 `irm_qa_sh_789`）。

---

## 四、Milvus 插入格式

每条记录写入 `thoth_knowledge` Collection 的完整字段：

```python
{
    "id": "npr_12345",          # 主键 = custom_id
    "source": "npr",            # 数据源
    "source_id": 12345,         # 源表主键
    "title": "国务院办公厅关于...",
    "publish_date": "2025-01-15",
    "content": "政策原文内容...",  # 从输入 JSONL 的 body.input 读取
    "vector": [0.01, -0.02, ...],  # 1024 维
    "chunk_index": 0,           # 分块序号（不分块=0）
    "chunk_count": 1,           # 总块数（不分块=1）
    # 以下为可选字段，按源表路由填充，其余为 None
    "publisher": "国务院办公厅",
    "stock_code": None,
    "stock_name": None,
    "channel": None,
    "src": None,
    ...
}
```

### 4.1 content 字段说明

`content` 存储的是**向量化的原文**（即 Batch API 的 body.input），从输入 JSONL 文件读取，而非源表的原始字段。各数据源向量化前都做了内容增强：

| 数据源 | content 内容（= 向量化原文） |
|--------|---------------------------|
| npr | Markdown 文件全文 |
| news | `板块：{channels}\n发布时间：{datetime}\n\n{content}` |
| major_news | `标题：{title}\n发布时间：{pub_time}\n来源：{src}\n{content}` |
| cctv_news | `{title}\n{date}\n{content}` |
| irm_qa_sh/sz | `[{trade_date}] {name}（{ts_code}）\n{q}\n{a}` |

这保证了 `content` 与 `vector` 语义完全一致，检索时可直接展示。

---

## 五、JSONL 文件格式

### 5.1 输出 JSONL（Batch API 结果）

路径存储在 `embedding_batch_task.output_file_path`，每行格式：

```json
{
    "custom_id": "npr_12345",
    "response": {
        "status_code": 200,
        "body": {
            "data": [{"embedding": [0.01, -0.02, ...], "index": 0}]
        }
    }
}
```

仅 `status_code = 200` 的行会被处理，其余跳过并计入日志。

### 5.2 输入 JSONL（向量化请求）

路径存储在 `embedding_batch_task.input_file_path`，每行含 `body.input`（向量化原文）：

```json
{
    "custom_id": "npr_12345",
    "method": "POST",
    "url": "/v1/embeddings",
    "body": {
        "model": "text-embedding-v4",
        "input": "# 国务院办公厅关于...\n\n**发文字号**: ...\n\n---\n\n正文...",
        "encoding_format": "float"
    }
}
```

---

## 六、数据库变更

本模块运行时自动检测并添加以下字段（无需手动 DDL）：

### 6.1 embedding_batch_task 表

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `milvus_status` | VARCHAR(20) | `pending` | Milvus 入库状态 |

状态流转：

```
pending → completed    （全部批次插入成功）
pending → failed       （存在批次插入失败，可通过 -s 或 -t 重试）
```

### 6.2 源表（npr / news / major_news / ...）

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `embedding_done` | TINYINT | 0 | 0=未入库，1=已入库 |

插入成功后批量更新对应 source_id 的记录。

---

## 七、去重与重试

### 7.1 ID 去重

插入前批量查询 Milvus 中已有的 ID，已存在则跳过，计入 `skipped` 统计。

### 7.2 重试机制

| 场景 | 处理方式 |
|------|---------|
| 批次部分失败 | 已插入的批次不回滚，失败批次标记 `milvus_status=failed`，下次重试时已存在的 ID 自动跳过 |
| `-s` 模式 | 自动拉取 `milvus_status` 为 `pending` 或 `failed` 的任务 |
| `-t` 模式 | 不检查状态，始终执行，可用于手动重试任意任务 |

### 7.3 幂等性

同一任务多次执行不会产生重复数据——已存在的 ID 会被跳过。

---

## 八、代码结构

```
src/indexing/
├── __init__.py
├── create_collection.py        # 创建 thoth_knowledge Collection
└── insert_vectors.py           # 向量结果入库（本模块）

scripts/
└── insert_vectors.sh           # Shell 执行入口
```

### 8.1 核心函数

| 函数 | 功能 |
|------|------|
| `parse_output_jsonl(filepath)` | 解析输出 JSONL → `{custom_id: embedding}` |
| `parse_input_jsonl(filepath)` | 解析输入 JSONL → `{custom_id: content}` |
| `insert_vectors_for_task(task_record, db)` | 处理单条任务的完整入库流程 |
| `insert_by_source(source)` | 按数据源批量入库 |
| `insert_by_task_id(task_id)` | 指定任务 ID 入库 |

### 8.2 内部函数

| 函数 | 功能 |
|------|------|
| `_build_milvus_record(...)` | 组装单条 Milvus 插入记录 |
| `_check_existing_ids(milvus, ids)` | 批量检查 Milvus 已有 ID |
| `_query_source_metadata(db, source, ids)` | 批量查询源表元数据 |
| `_ensure_milvus_status_column(db)` | 自动补齐 milvus_status 字段 |
| `_ensure_embedding_done_column(db, table)` | 自动补齐 embedding_done 字段 |
| `_update_milvus_status(id, status, db)` | 更新 milvus_status |
| `_update_source_embedding_done(db, table, ids)` | 批量标记源表 embedding_done |

---

## 九、thoth_knowledge Collection Schema

| 字段 | 类型 | 长度 | 说明 |
|------|------|------|------|
| `id` | VARCHAR | 256 | 主键，`{source}_{source_id}` |
| `source` | VARCHAR | 32 | 数据源标识 |
| `source_id` | INT64 | — | 源表主键 |
| `title` | VARCHAR | 500 | 标题 |
| `publish_date` | VARCHAR | 10 | 发布日期 YYYY-MM-DD |
| `content` | VARCHAR | 65535 | 向量化原文 |
| `vector` | FLOAT_VECTOR | 1024 | text-embedding-v4 向量 |
| `chunk_index` | INT64 | — | 分块序号 |
| `chunk_count` | INT64 | — | 总块数 |
| `section` | VARCHAR | 100 | 分段名（可选） |
| `stock_code` | VARCHAR | 20 | 股票代码（可选） |
| `stock_name` | VARCHAR | 100 | 股票名称（可选） |
| `institution` | VARCHAR | 200 | 机构（可选） |
| `industry` | VARCHAR | 100 | 行业（可选） |
| `report_type` | VARCHAR | 20 | 研报类型（可选） |
| `ann_type` | VARCHAR | 50 | 公告子类型（可选） |
| `publisher` | VARCHAR | 500 | 发文机关（可选） |
| `doc_id` | VARCHAR | 100 | 发文字号（可选） |
| `category` | VARCHAR | 100 | 主题分类（可选） |
| `channel` | VARCHAR | 50 | 新闻频道（可选） |
| `src` | VARCHAR | 50 | 新闻来源（可选） |

索引：
- 向量索引：`vector` — HNSW（M=16, efConstruction=200, metric=IP）
- 标量索引：`publish_date`、`source`、`stock_code` — INVERTED

---

## 十、配置依赖

| 配置文件 | 用途 |
|---------|------|
| `hetu-aether/conf/milvus_conf.json` | Milvus 连接（host/port/database/collection_name） |
| `hetu-aether/conf/db_conf.json` | GreatSQL 连接（源表元数据查询） |

---

## 十一、单元测试

```bash
python unit_test/test_insert_vectors.py
```

52 个用例，覆盖 13 个测试类：

| 测试类 | 覆盖场景 |
|--------|---------|
| TestFormatDate | datetime / date / string / None / 空字符串 / 带时间字符串 |
| TestParseOutputJsonl | 正常解析 / 非200跳过 / 空embedding / 无效JSON / 文件不存在 / 空文件 |
| TestParseInputJsonl | 正常解析 / 文件不存在 / 空内容 |
| TestBuildMilvusRecord | npr / news / irm_qa_sh / 分块 / 无元数据 / 超长截断 / 可选字段 |
| TestCheckExistingIds | 无已有 / 部分已有 / 查询异常 / 空列表 |
| TestEnsureMilvusStatusColumn | 字段已存在 / 字段不存在 |
| TestQuerySourceMetadata | 正常查询 / 无效源 / 空ID |
| TestInsertVectorsForTask | 正常插入 / 跳过已存在 / 缺少文件 / 插入失败 / 空JSONL |
| TestInsertBySource | 无效源 / 无任务 / 多任务 |
| TestInsertByTaskId | 不存在 / 正常 |
| TestUpdateSourceEmbeddingDone | 正常 / 空ID / 字段创建失败 |
| TestConstants | 源列表 / 元数据覆盖 / 批次大小 / 状态常量 |
| TestBatchInsertBoundary | 恰好1000条单批次 / 1001条分2批次 |
