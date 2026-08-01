# Batch Embedding 提交与回写指南

> 更新日期：2026-06-19 | 模块：`src/text2jsonl/submit_batch_embedding.py`、`src/utils/util_text_embedding.py`、`src/utils/util_embedding_task.py`

---

## 一、概述

将 JSONL 生成阶段产出的文件通过百炼 Batch API 提交给 `text-embedding-v4` 模型进行向量化，轮询任务状态，下载结果文件并回写统计信息。

### 1.1 整体流程

```
embedding_batch_task (status=pending)
  → 上传 JSONL (uploaded)
    → 创建 Batch 任务 (validating)
      → API 处理中 (in_progress)
        → API 完成 → DB 标记 (finalizing)
          → 下载结果 + 统计回写 (completed)
            → 钉钉通知
```

### 1.2 三种操作模式

| 模式 | 命令标志 | 说明 |
|------|---------|------|
| 提交 | `--submit` | 从 DB 读取 `pending` 任务，上传 JSONL 并创建 Batch |
| 轮询 | `--poll` | 轮询 `uploaded` / `validating` / `in_progress` 状态的任务，同步 API 状态 |
| 下载 | `--finalize` | 下载 `finalizing` 状态的任务结果，解析统计，发送钉钉通知 |

三种模式通过独立 Shell 脚本调用，可分别配置 cron 定时执行。

---

## 二、状态流转

### 2.1 状态机

```
pending → uploaded → validating → in_progress → finalizing → completed
                                                    ↓
                                            failed / expired / cancelled
```

### 2.2 各阶段更新字段

| 阶段 | 触发方 | 更新字段 |
|------|--------|---------|
| pending | `build_*_jsonl.py` | INSERT (source, status, input_file_path, record_count, data_start_date, data_end_date) |
| uploaded | `--submit` | UPDATE file_id, status, started_at |
| validating | `--submit` | UPDATE task_id, status, api_cost（预估） |
| in_progress | `--poll` | UPDATE status |
| finalizing | `--poll` | UPDATE status（API 返回 completed 时设置） |
| completed | `--finalize` | UPDATE status, output_file_path, success_count, failed_count, total_tokens, api_cost（实际）, completed_at |
| failed | `--poll` / `--finalize` | UPDATE status, error_code, error_message, completed_at |

### 2.3 API finalizing 处理

API 的 `finalizing` 状态表示"即将完成，尚无输出文件"。poll 检测到此状态时**不更新 DB**，保持当前运行状态继续轮询，直到 API 返回 `completed` 后才将 DB 设为 `finalizing`（待下载）。

---

## 三、使用方法

### 3.1 提交任务

从 `embedding_batch_task` 表读取所有 `status='pending'` 的记录，逐个上传 JSONL 并创建 Batch 任务。JSONL 文件路径从表中 `input_file_path` 字段读取，不通过命令行传入。

```bash
# 提交所有 pending 任务
bash scripts/submit_batch_task.sh

# 只提交指定数据源
bash scripts/submit_batch_task.sh -s npr
bash scripts/submit_batch_task.sh -s news
```

### 3.2 轮询状态

轮询所有 `uploaded` / `validating` / `in_progress` 状态且 `task_id` 非空的任务，同步 API 端最新状态到 DB。

```bash
# 轮询全部
bash scripts/poll_batch_tasks.sh

# 只轮询指定数据源
bash scripts/poll_batch_tasks.sh -s npr
```

### 3.3 下载结果

下载所有 `status='finalizing'` 的任务输出文件，解析成功/失败/token 统计，回写 DB 并发送钉钉通知。

```bash
# 下载全部
bash scripts/finalize_batch_tasks.sh

# 只处理指定数据源
bash scripts/finalize_batch_tasks.sh -s news
```

### 3.4 典型 cron 配置

```cron
# 每小时轮询一次
0 * * * * bash /path/to/scripts/poll_batch_tasks.sh >> /mnt/e/logs/poll.log 2>&1

# 每小时尝试下载结果
5 * * * * bash /path/to/scripts/finalize_batch_tasks.sh >> /mnt/e/logs/finalize.log 2>&1
```

---

## 四、核心方法

### 4.1 submit_batch(jsonl_path, source) → dict

上传 JSONL 文件并创建 Batch 任务。

```python
from submit_batch_embedding import submit_batch

result = submit_batch("/mnt/f/batch_jsonl/npr/20260614/npr_202504_202606.jsonl", source="npr")
# → {"file_id": "file-xxx", "task_id": "batch-xxx", "record_id": 1, "skipped": False}
```

流程：
1. 查找 DB 中对应 `input_file_path` 的 `pending` 记录
2. 若无则自动创建 `pending` 记录
3. 重复检查（同 source + 日期范围已有 `completed` 记录则跳过）
4. 调用 `util_text_embedding.upload_batch_file()` 上传
5. 调用 `util_text_embedding.create_batch_task()` 创建 Batch
6. 更新 DB 状态至 `validating`

### 4.2 poll_all_pending_tasks(source=None) → list

轮询所有运行中任务并同步状态。

```python
from submit_batch_embedding import poll_all_pending_tasks

changed = poll_all_pending_tasks(source="news")
# → [{"record_id": 2, "task_id": "batch-xxx", "old_status": "validating", "new_status": "in_progress"}]
```

### 4.3 finalize_completed_tasks(source=None) → list

下载已完成任务的结果并回写统计。

```python
from submit_batch_embedding import finalize_completed_tasks

finalized = finalize_completed_tasks()
# → [{"record_id": 1, "source": "npr", "success_count": 705, "failed_count": 0, "total_tokens": 1069667}]
```

### 4.4 submit_all_pending_tasks(source=None) → list

批量提交所有 `pending` 状态的任务，`--submit` 模式的入口方法。

```python
from submit_batch_embedding import submit_all_pending_tasks

results = submit_all_pending_tasks(source="npr")
```

---

## 五、重复检查

提交前查询 `embedding_batch_task` 表，若同一 `source` 在目标日期范围内已存在 `completed` 状态的记录则跳过，避免重复提交和重复计费。

| 检查条件 | SQL |
|---------|-----|
| 覆盖检查 | `source = ? AND data_start_date <= ? AND data_end_date >= ? AND status = 'completed'` |

---

## 六、输出目录

结果文件保存在 `embedding_dir`（配置于 `conf/dir_conf.json`），路径结构与输入 JSONL 一致：

```
输入: /mnt/f/batch_jsonl/npr/20260614/npr_202504_202606.jsonl
输出: /mnt/f/embedding_jsonl/npr/20260614/npr_202504_202606_output.jsonl
```

```
/mnt/f/embedding_jsonl/
├── npr/
│   └── 20260614/
│       └── npr_202504_202606_output.jsonl
├── news/
│   └── 202605/
│       ├── news_202605_01_output.jsonl
│       └── news_202605_02_output.jsonl
└── ...
```

### 输出 JSONL 每行格式

```json
{
    "id": "uuid",
    "custom_id": "npr_30753",
    "response": {
        "status_code": 200,
        "body": {
            "data": [{"index": 0, "embedding": [0.067, -0.035, ...]}],
            "usage": {"total_tokens": 1520}
        }
    }
}
```

---

## 七、配置

### 7.1 dir_conf.json

| 键 | 说明 | 值 |
|------|------|-----|
| `jsonl_dir` | 输入 JSONL 根目录 | `/mnt/f/batch_jsonl` |
| `embedding_dir` | 输出结果根目录 | `/mnt/f/embedding_jsonl` |

### 7.2 model_conf.json（hetu-aether）

| 字段 | 说明 |
|------|------|
| `api_key` | DashScope API Key |
| `base_url` | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `endpoint` | `/v1/embeddings` |
| `dimensions` | `1024` |
| `usage.price_per_1k_tokens` | `0.00025`（元/千token） |

### 7.3 API Key 优先级

```
函数参数 > 环境变量 DASHSCOPE_API_KEY > model_conf.json 的 api_key 字段
```

---

## 八、钉钉通知

`finalize_completed_tasks` 完成后自动发送 Markdown 格式的钉钉消息，包含：

- 完成时间、任务数量
- 各数据源的成功/失败/token/费用明细
- 汇总统计

通知失败不影响任务结果，仅记录 warning 日志。

---

## 九、错误处理与重试

### 9.1 提交失败

单个任务提交失败不影响其他任务，错误记录到日志，任务保持 `pending` 状态，下次运行 `--submit` 时自动重试。

### 9.2 轮询异常

API 查询失败时跳过该任务，不更新状态，下次轮询时重试。

### 9.3 下载失败

下载失败的任务标记为 `failed`，记录 `error_code` 和 `error_message`。可通过将状态重置为 `finalizing` 触发重新下载：

```sql
UPDATE embedding_batch_task
SET status = 'finalizing', error_code = NULL, error_message = NULL, completed_at = NULL
WHERE id = ? AND status = 'failed';
```

然后重新运行 `bash scripts/finalize_batch_tasks.sh`。

---

## 十、有效数据源

```
npr / news / major_news / cctv_news / irm_qa_sh / irm_qa_sz / stock_report / industry_report / anns_d
```

---

## 十一、依赖模块

| 模块 | 来源 | 说明 |
|------|------|------|
| `util_text_embedding` | hetu-thoth/src/utils | Batch API 上传 / 创建 / 查询 / 下载 |
| `util_embedding_task` | hetu-thoth/src/utils | embedding_batch_task 表 CRUD 与状态流转 |
| `util_log` | hetu-aether/utils | 日志记录 |
| `util_db` | hetu-aether/utils | GreatSQL 数据库连接 |
| `util_dingtalk` | hetu-aether/utils | 钉钉消息推送 |

---

## 十二、单元测试

```bash
python unit_test/test_submit_batch_embedding.py
```

42 个测试用例，覆盖场景：

| 类别 | 覆盖内容 |
|------|---------|
| 路径推断 | 各数据源路径识别、无效路径、空路径 |
| 输出路径 | jsonl_dir → embedding_dir 映射、非标准路径回退 |
| 结果解析 | 全成功、混合结果、空文件、无效 JSON、无 usage |
| 重复检查 | 已有 completed、无记录、无日期 |
| 提交任务 | 新任务、已有 pending、文件不存在、无数据源、重复跳过 |
| 轮询状态 | 状态变化、completed→finalizing、API finalizing 跳过、失败、API 异常、数据源过滤 |
| 下载结果 | 成功下载、下载失败标记 failed、无任务、钉钉失败不影响结果 |
| 批量提交 | 按源提交、全源提交、无任务、文件缺失、部分失败 |
