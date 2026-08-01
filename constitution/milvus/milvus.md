# Milvus 操作规范

> 通用规范。Milvus 连接与操作必须统一使用 hetu-aether 公共工具 `utils/util_milvus.py`，禁止直接使用原生 `MilvusClient` 或各自重复封装。

## 一、连接管理

### 1.1 使用公共工具（强制）

```python
from utils.util_milvus import get_milvus

milvus = get_milvus(project_name="hetu-xxx")   # 业务项目需传 project_name 切换日志归属
conn = milvus.connect()                         # 获取连接
try:
    ...
finally:
    milvus.disconnect()
```

1. 通过 `get_milvus()` 获取单例 `MilvusDB`，禁止重复创建实例
2. 业务项目调用时传入 `project_name`，便于日志归属到对应项目
3. 连接使用完毕必须 `disconnect()` 释放，推荐 `try/finally`
4. 配置文件默认 `conf/milvus_conf.json`（位于 hetu-aether，业务项目可覆盖）

### 1.2 公共工具提供的能力

| 方法 | 说明 |
|------|------|
| `has_collection(name)` | 检查 Collection 是否存在 |
| `create_collection(schema, name)` | 创建 Collection |
| `drop_collection(name)` | 删除 Collection |
| `create_index(name)` | 创建向量索引 |
| `load_collection(name)` | 加载 Collection 到内存 |
| `insert(data, name)` | 插入数据（批量） |
| `search(vectors, top_k, filter_expr, output_fields, name)` | 向量检索 |
| `query(filter_expr, name)` | 标量过滤查询 |
| `delete(filter_expr, name)` | 按过滤条件删除 |
| `get_stats(name)` | 获取统计信息 |

## 二、Collection 管理

### 2.1 Schema 定义

Collection Schema 定义集中存放，DDL 与业务代码分离：

- 统一放在业务项目 `src/xxx/schema/` 目录（如 thoth 为 `src/indexing/schema/`）
- 使用 `pymilvus` 的 `FieldSchema` / `CollectionSchema` 定义
- 主键建议 `VARCHAR(64)`（用业务 ID），向量字段 `FLOAT_VECTOR`

```python
from pymilvus import FieldSchema, CollectionSchema, DataType

fields = [
    FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=64, is_primary=True),
    FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
    FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=dim),
    FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=256),
    FieldSchema(name="chunk_index", dtype=DataType.INT64),
    FieldSchema(name="metadata", dtype=DataType.JSON),
]
schema = CollectionSchema(fields, description="text embedding collection")
```

### 2.2 创建与删除

1. 创建前必须用 `has_collection()` 检查，避免重复创建
2. 删除 Collection 属于数据销毁操作，必须先备份（遵循顶层宪法"数据增删改先备份"）
3. 字段、索引、分区分批等规则按业务约定，禁止直接改公共工具

## 三、批量入库

1. 批量插入，每批不超过 1000 条，禁止逐条插入
2. 按业务键（如 `source` / `chunk_index`）分组插入
3. 插入后核对返回的 `insert_count` 与预期一致，不一致需告警
4. 入库完成后为向量字段创建索引（`create_index`），加速后续检索

## 四、向量检索

1. 必须指定 `top_k` 与检索参数
2. 检索前先 `load_collection()` 确保已加载到内存
3. 查询必须带过滤表达式（`filter_expr`）缩小范围，避免全量扫描
4. 返回字段按需用 `output_fields` 裁剪，减少网络传输
5. 距离度量：默认 `IP`（内积，Embedding 已归一化）；`L2` 用于一般向量；文本向量可选 `COSINE`

## 五、Partition 分区

1. 按数据源或业务领域划分 Partition，命名 `p_<来源>` 或 `p_<业务域>`
2. 单个 Partition 数据量建议 10 万条以内
3. 检索优先在指定 Partition 内进行

## 六、配置管理

配置统一放 hetu-aether `conf/milvus_conf.json`，业务项目如需覆盖在同名路径提供：

```json
{
    "host": "localhost",
    "port": 19530,
    "user": "",
    "password": "",
    "alias": "default",
    "db_name": "",
    "search": {
        "metric_type": "IP",
        "params": {"nprobe": 16}
    }
}
```

- `host`/`port`：服务地址与端口
- `user`/`password`：认证凭据（可选，禁止硬编码）
- `search`：检索默认参数

## 七、错误处理

1. 所有 Milvus 操作必须捕获异常并记录日志（`utils/util_log.py`）
2. 连接失败时重试（最多 3 次）
3. 批量插入部分失败时记录失败批次并继续，最终汇总上报
4. 禁止在日志中输出连接密码等敏感信息

## 八、性能优化

1. 批量入库，避免逐条
2. 搜索前确保索引已创建并加载
3. 大数据量查询分页或分区
4. 定期 `flush()`，必要时 `compact()` 优化存储
5. 根据数据规模调整索引参数（如 `nlist`、`nprobe`）
