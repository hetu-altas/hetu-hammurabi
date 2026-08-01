# Milvus 向量数据库使用说明

## 一、环境信息

| 项目 | 值 |
|------|-----|
| 服务地址 | localhost:19530 |
| 数据库 | qmt |
| 配置文件 | `hetu-aether/conf/milvus_conf.json` |
| 工具模块 | `hetu-aether/utils/util_milvus.py` |

---

## 二、工具模块 util_milvus

`MilvusDB` 是基于 PyMilvus 3.0 `MilvusClient` 封装的单例类，提供 Collection 管理、索引、数据操作等功能。

### 2.1 获取实例

```python
from utils.util_milvus import get_milvus

milvus = get_milvus()
```

### 2.2 方法一览

| 方法 | 功能 |
|------|------|
| `connect()` | 创建连接（懒加载，首次调用时自动触发） |
| `disconnect()` | 关闭连接 |
| `has_collection(name)` | 检查 Collection 是否存在 |
| `create_collection(schema, name)` | 创建 Collection |
| `drop_collection(name)` | 删除 Collection |
| `create_index(name)` | 按配置创建向量索引 |
| `load_collection(name)` | 加载 Collection 到内存 |
| `insert(data, name)` | 插入数据（list[dict]） |
| `search(vectors, top_k, filter_expr, output_fields, name)` | 向量搜索 |
| `query(filter_expr, output_fields, limit, name)` | 标量查询 |
| `delete(filter_expr, name)` | 按表达式删除 |
| `get_stats(name)` | 获取 Collection 统计 |

所有 `name` 参数可省略，默认使用配置文件中的 `collection_name`。

### 2.3 配置文件

`conf/milvus_conf.json` 结构：

```json
{
  "host": "localhost",
  "port": 19530,
  "user": "",
  "password": "",
  "database": "qmt",
  "collection_name": "thoth_knowledge",
  "index": {
    "field_name": "vector",
    "index_type": "HNSW",
    "metric_type": "IP",
    "params": { "M": "16", "efConstruction": "200" }
  },
  "search": {
    "metric_type": "IP",
    "params": { "ef": "64" }
  }
}
```

---

## 三、thoth_knowledge Collection

### 3.1 基本信息

| 项目 | 值 |
|------|-----|
| 数据库 | qmt |
| Collection | thoth_knowledge |
| 向量维度 | 1024（text-embedding-v4） |
| 创建脚本 | `hetu-thoth/src/indexing/create_collection.py` |

### 3.2 创建方式

```bash
# 使用项目虚拟环境执行
/mnt/d/workspace/hetu-altas/venv-hetu/bin/python \
  /mnt/d/workspace/hetu-altas/hetu-thoth/src/indexing/create_collection.py
```

脚本具备幂等性，Collection 已存在时自动跳过。

也可在代码中调用：

```python
from create_collection import create_thoth_knowledge

create_thoth_knowledge()
```

### 3.3 Schema 字段

#### 必填字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | VARCHAR(256) | 主键，格式 `{source}_{source_id}` |
| `source` | VARCHAR(32) | 数据来源：npr / news / major_news / cctv_news / irm_qa_sh / irm_qa_sz / stock_report / industry_report / anns_d |
| `source_id` | INT64 | 原始表主键 |
| `title` | VARCHAR(500) | 标题 |
| `publish_date` | VARCHAR(10) | 发布日期（YYYY-MM-DD） |
| `content` | VARCHAR(65535) | 文本内容（送向量的原文） |
| `vector` | FLOAT_VECTOR(1024) | text-embedding-v4 向量 |
| `chunk_index` | INT64 | 分块序号（不分块=0） |
| `chunk_count` | INT64 | 总块数（不分块=1） |

#### 可选字段（nullable）

| 字段 | 类型 | 说明 |
|------|------|------|
| `section` | VARCHAR(100) | 分段名（研报/公告用） |
| `stock_code` | VARCHAR(20) | 股票代码 |
| `stock_name` | VARCHAR(100) | 股票名称 |
| `institution` | VARCHAR(200) | 发布方/机构 |
| `industry` | VARCHAR(100) | 行业 |
| `report_type` | VARCHAR(20) | 研报类型 |
| `ann_type` | VARCHAR(50) | 公告子类型 |
| `publisher` | VARCHAR(200) | 发文机关 |
| `doc_id` | VARCHAR(100) | 发文字号 |
| `category` | VARCHAR(100) | 主题分类 |
| `channel` | VARCHAR(50) | 新闻频道 |
| `src` | VARCHAR(50) | 新闻来源 |

### 3.4 索引配置

| 索引类型 | 字段 | 参数 |
|---------|------|------|
| HNSW | vector | metric_type=IP, M=16, efConstruction=200 |
| INVERTED | publish_date | 日期过滤 |
| INVERTED | source | 数据源过滤 |
| INVERTED | stock_code | 股票代码过滤 |

### 3.5 使用示例

```python
from utils.util_milvus import get_milvus

milvus = get_milvus()

# 插入数据
milvus.insert([{
    "id": "npr_12345",
    "source": "npr",
    "source_id": 12345,
    "title": "示例标题",
    "publish_date": "2026-06-19",
    "content": "示例文本内容",
    "vector": [0.1] * 1024,
    "chunk_index": 0,
    "chunk_count": 1,
}])

# 向量搜索（带日期过滤）
results = milvus.search(
    vectors=[[0.1] * 1024],
    top_k=10,
    filter_expr='publish_date >= "2026-06-01"',
    output_fields=["id", "title", "source", "publish_date"],
)

# 标量查询
rows = milvus.query(
    filter_expr='source == "npr" and stock_code == "000001"',
    output_fields=["id", "title", "content"],
    limit=50,
)
```
