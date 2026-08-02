# 日志规范

## 一、日志目录

### 1.1 目录结构
所有项目日志统一输出到 `../logs/hetu-altas/` 下，按项目划分子目录：

```
../logs/hetu-altas/
├── hetu-aether/          # 公共项目日志
│   └── hetu-aether.log
├── hetu-mercury/         # 业务项目日志
│   └── hetu-mercury.log
└── hetu-XXX/             # 其他业务项目
    └── hetu-XXX.log
```

### 1.2 规则
- 每个项目的 `file_prefix` 配置为项目名
- 日志文件按**日期**滚动切割，每天零时自动创建新文件，保留最近 30 天的历史文件
- 日志文件名格式：`<项目名>.log`（当天）、`<项目名>.log.YYYY-MM-DD`（历史）

---

## 二、日志字段

每条日志必须包含以下信息：

| 字段 | 说明 | 来源 |
|------|------|------|
| `timestamp` | 时间戳，精确到秒 | 自动生成 |
| `project_name` | 项目名称 | 配置文件 `project_name` |
| `file_name` | Python 文件名 | `log_operation` 装饰器自动捕获 |
| `method_name` | 方法名称 | `log_operation` 装饰器自动捕获 |
| `operation_name` | 操作名称 | 调用时传入或装饰器默认使用方法名 |
| `exec_status` | 执行状态：SUCCESS / FAILURE | 调用时传入，INFO 默认 SUCCESS，ERROR 固定 FAILURE |
| `execution_time` | 执行耗时，格式 `X.XXXXs` | 自动计时或调用时传入 |
| `level` | 日志级别：DEBUG / INFO / WARNING / ERROR | auto |
| `message` | 日志消息 | 调用时传入 |
| `error_code` | 错误码/异常类型名（ERROR 级别） | 调用时传入 |
| `stack_trace` | 异常堆栈信息（ERROR 级别） | 装饰器自动捕获 |

---

## 三、日志格式

### 3.1 通用格式（INFO / WARNING / DEBUG）

```
timestamp | project_name | file_name:method_name | operation_name | exec_status | execution_time | LEVEL | message
```

示例：
```
2026-05-01 10:30:15 | hetu-aether | util_db.py:query_one | query_data | SUCCESS | 0.0234s | INFO | Operation query_data executed successfully
```

### 3.2 ERROR 格式

```
timestamp | project_name | file_name:method_name | operation_name | FAILURE | execution_time | ERROR | error_code | message
--- STACK_TRACE ---
stack_trace_content
```

示例：
```
2026-05-01 10:30:20 | hetu-aether | util_db.py:query_one | query_data | FAILURE | 0.0502s | ERROR | ConnectionError | Connection refused
--- STACK_TRACE ---
Traceback (most recent call last):
  File "util_db.py", line 130, in query_one
    conn = self.connect()
ConnectionError: Connection refused
```

---

## 四、日志级别

| 级别 | 用途 | 使用场景 |
|------|------|---------|
| DEBUG | 调试信息 | 开发阶段详细输出，生产环境默认关闭 |
| INFO | 正常业务流程 | 关键操作执行完成、数据同步结果等 |
| WARNING | 可恢复的异常/警告 | 重试成功、降级处理、配置缺失使用默认值 |
| ERROR | 不可恢复的错误 | 异常捕获、操作失败、外部服务不可用 |

生产环境默认级别为 `INFO`。

---

## 五、使用方式

### 5.1 获取日志实例
```python
from utils.util_log import get_logger

logger = get_logger()  # 默认使用 conf/log_conf.json 配置
```

### 5.2 手动记录
```python
import time

start = time.time()
try:
    result = do_something()
    elapsed = time.time() - start
    logger.info(
        message="数据同步完成",
        operation="sync_data",
        exec_status="SUCCESS",
        execution_time=elapsed,
    )
except Exception as e:
    elapsed = time.time() - start
    import traceback
    logger.error(
        message=str(e),
        operation="sync_data",
        error_code=type(e).__name__,
        execution_time=elapsed,
        stack_trace=traceback.format_exc(),
    )
```

### 5.3 使用装饰器（推荐）
```python
from utils.util_log import log_operation

@log_operation(operation="sync_database")
def sync_database():
    ...  # 自动记录执行时间、状态、异常堆栈
```

装饰器会自动捕获：
- `file_name`：调用文件路径
- `method_name`：被装饰函数名
- `execution_time`：函数执行耗时
- 成功时记录 INFO，失败时记录 ERROR + 异常堆栈

### 5.4 WARNING / DEBUG
```python
logger.warning(
    message="配置缺失，使用默认值",
    operation="load_config",
    execution_time=elapsed,
)

logger.debug(
    message="SQL 参数绑定",
    operation="query_build",
)
```

---

## 六、配置

配置文件 `conf/log_conf.json`：

```json
{
    "log_dir": "../logs/hetu-altas",
    "project_name": "hetu-aether",
    "file_prefix": "hetu-aether",
    "rotation": {
        "when": "midnight",
        "interval": 1,
        "backup_count": 30
    },
    "level": "INFO",
    "format": "%(asctime)s | %(project_name)s | %(file_name)s:%(method_name)s | %(operation_name)s | %(exec_status)s | %(execution_time)s | %(levelname)s | %(message)s",
    "date_format": "%Y-%m-%d %H:%M:%S"
}
```

配置字段说明：

| 字段 | 必填 | 说明 |
|------|------|------|
| `log_dir` | 是 | 日志根目录，每个项目的实际输出目录为 `{log_dir}/{project_name}/` |
| `project_name` | 是 | 项目名称，如 `hetu-aether`、`hetu-mercury` |
| `file_prefix` | 否 | 日志文件名前缀，默认为 `project_name` |
| `rotation.when` | 否 | 滚动周期单位，默认 `midnight`（每天零时） |
| `rotation.interval` | 否 | 滚动间隔数，默认 `1`（与 when 配合，如 `midnight` + `1` = 每天） |
| `rotation.backup_count` | 否 | 保留的历史日志文件数量，默认 30 天 |
| `level` | 否 | 日志级别，默认 `INFO` |
| `format` | 否 | 日志输出格式 |
| `date_format` | 否 | 时间戳格式 |

---

## 七、实现要求

### 7.1 日志实例管理
- `LogRecord` 使用单例模式，通过 `get_logger()` 获取
- 每个进程只初始化一个日志实例
- 初始化时根据 `project_name` 创建对应的日志子目录

### 7.2 输出目标
- 文件输出：`{log_dir}/{project_name}/{file_prefix}.log`（滚动文件）
- 控制台输出：同步输出到 stderr，便于开发调试

### 7.3 性能要求
- 日志记录不应显著影响业务性能
- 避免在日志方法中执行耗时操作
- 高频调用场景考虑异步日志（后续优化）

### 7.4 安全要求
- 日志中不得输出密码、Token、密钥等敏感信息
- 异常堆栈中的敏感字段应做脱敏处理
