# TDengine 使用规范

## 一、概述

TDengine 作为时序数据库，用于存储海量时序数据（行情数据、财务数据等）。项目通过 `taosrest` REST API 连接 TDengine，使用自定义连接池管理连接。

---

## 二、连接配置

### 2.1 配置文件

TDengine 连接配置统一存放在 `conf/taos_conf.json`，格式如下：

```json
{
    "host": "<host>",
    "port": <port>,
    "user": "<user>",
    "password": "<password>",
    "database": "<database>",
    "charset": "utf-8",
    "pool": {
        "min_connections": 1,
        "max_connections": 10,
        "idle_timeout": 300
    },
    "options": {
        "connect_timeout": 10,
        "read_timeout": 30,
        "write_timeout": 30,
        "auto_reconnect": true,
        "batch_size": 1000
    }
}
```

### 2.2 配置字段说明

| 字段 | 必填 | 说明 |
|------|------|------|
| `host` | 是 | TDengine 服务器地址 |
| `port` | 是 | REST API 端口，默认 6041 |
| `user` | 是 | 数据库用户名 |
| `password` | 是 | 数据库密码 |
| `database` | 是 | 默认数据库名称 |
| `charset` | 否 | 字符集，默认 `utf-8` |
| `pool.min_connections` | 否 | 最小连接数 |
| `pool.max_connections` | 否 | 最大连接数，默认 10 |
| `pool.idle_timeout` | 否 | 空闲超时时间（秒） |
| `options.connect_timeout` | 否 | 连接超时（秒） |
| `options.read_timeout` | 否 | 读超时（秒） |
| `options.write_timeout` | 否 | 写超时（秒） |
| `options.auto_reconnect` | 否 | 是否自动重连 |
| `options.batch_size` | 否 | 批量写入行数，默认 1000 |

### 2.3 规则

1. 配置文件中不得包含明文密码（如外部系统要求，需加密存储）
2. 连接配置统一从 `conf/` 目录的 JSON 配置文件获取，禁止硬编码
3. 不同环境（开发/测试/生产）使用独立配置文件

---

## 三、连接获取与使用

### 3.1 获取 TDengine 实例

使用 `get_tdengine()` 工厂函数获取单例：

```python
from utils.util_db import get_tdengine

td = get_tdengine()                     # 使用默认配置 conf/taos_conf.json
td = get_tdengine("conf/taos_conf.json")  # 显式指定配置路径
```

`get_tdengine()` 内部调用 `TDengine.get_instance()`，使用**双重检查锁（double-checked locking）**保证线程安全的单例模式。

### 3.2 执行 SQL

```python
# 执行任意 SQL（DDL / DML）
td.execute("CREATE STABLE IF NOT EXISTS your_db.daily (...) TAGS (...)")

# 查询数据，返回 List[Tuple]
rows = td.query("SELECT * FROM your_db.daily WHERE ts >= '2026-01-01'")

# 获取服务器版本
version = td.get_server_version()  # 如 "3.4.0.0"
```

### 3.3 使用连接池

```python
# 通过上下文管理器获取/归还连接（推荐）
with td.get_connection() as conn:
    result = conn.execute(sql, params)
    data = result.fetch_all()
```

连接池基于 `queue.Queue` 实现，启动时预创建所有连接，空闲时阻塞等待。

### 3.4 规则

1. **必须**使用 `get_tdengine()` 获取单例，禁止重复创建 `TDengine` 实例
2. **必须**通过上下文管理器 `with td.get_connection()` 获取连接，确保连接归还
3. 禁止绕过连接池直接创建 `TaosRestConnection`
4. **taosrest REST API 不支持参数化查询（`%s` 占位符）**，`td.execute()` 和 `td.query()` 的 `params` 参数仅为接口兼容保留，实际不使用。SQL 中的参数需通过调用方自行格式化（注意防注入）
5. 程序退出前调用 `td.close_pool()` 关闭连接池

### 3.5 调试与运维

无论是 Python 代码还是 Shell 脚本，调试 TDengine 时必须通过 **REST API** 方式访问，禁止使用原生 `taos` 客户端直连：

**Python 调试：**

```python
from utils.util_db import get_tdengine

td = get_tdengine()
rows = td.query("SELECT * FROM your_db.daily LIMIT 5")
print(rows)
version = td.get_server_version()
print(version)
```

**Shell 调试：**

```bash
# 通过 curl 调用 REST API
curl -u <user>:<password> "http://<host>:6041/rest/sql" \
  -d "SELECT * FROM your_db.daily LIMIT 5"

# 查看服务器版本
curl -u <user>:<password> "http://<host>:6041/rest/sql" \
  -d "SELECT SERVER_VERSION()"
```

**规则：**
1. Python 脚本中统一使用 `get_tdengine()` → REST API（`taosrest`），禁止 `import taos` 原生驱动
2. Shell 脚本中通过 `curl` + REST API 调试，禁止使用 `taos` CLI 客户端
3. 连接信息从 `conf/taos_conf.json` 读取，禁止硬编码

---

## 四、超级表（STABLE）规范

### 4.1 超级表创建

TDengine 采用**超级表-子表**两级模型，超级表定义数据 schema 和标签（区分不同数据源）。

**基本语法：**

```sql
CREATE STABLE IF NOT EXISTS your_db.daily (
    ts TIMESTAMP,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    pre_close DOUBLE,
    change DOUBLE,
    pct_chg DOUBLE,
    vol DOUBLE,
    amount DOUBLE
) TAGS (
    ts_code NCHAR(100)
);
```

### 4.2 超级表设计规则

1. **时间戳列：** 每个超级表必须有 `TIMESTAMP` 类型的主时间列，统一命名为 `ts`
2. **标签列：**
   - 以 `ts_code`（股票代码）为标签的数据，标签值为 NCHAR(100)
   - 如需多个标签，按业务含义命名，如 `hk_code`、`freq`、`ts_code`
   - 标签列不能为空，不支持部分子表有标签而另一部分没有
3. **空标签表：** 如果数据不对应具体股票（如大盘资金流向），声明空标签 `TAGS ()`，但不创建子表，直接向超级表插入
4. **数据库限定：** DDL 中始终使用 `数据库名.表名` 格式，如 `your_db.daily`

### 4.3 列定义规范

1. 数据列使用大写或小写均接受，统一风格即可
2. 价格、金额相关列使用 `DOUBLE`
3. 成交量、持仓量相关列使用 `DOUBLE`（兼容小数）
4. 整型标识列使用 `BIGINT`
5. 字符串列使用 `NCHAR(N)`（支持中文），N 按实际需要设定
6. 时间戳列统一命名 `ts`，类型 `TIMESTAMP`

### 4.4 超级表存放

1. 所有 DDL 语句集中存放在 `src/batch/sql/tdengine/` 目录下，按数据类别分文件
2. 文件命名规范：`股票数据.sql`、`期货数据.sql` 等
3. 每个文件包含该类别的所有超级表 DDL，使用 `--` 注释说明分组
4. DDL SQL 文件应与对应数据同步脚本配套

---

## 五、子表命名与创建

### 5.1 子表命名规则

子表名由**前缀 + 股票代码**组成：

| 数据类别 | 超级表名 | 子表前缀 | 示例 |
|---------|---------|---------|------|
| 日线行情 | `daily` | `d_` | `d_000001_sz` |
| 分钟行情 | `stk_mins` | `n_` | `n_000001_sz` |
| 周线行情 | `weekly` | `w_` | `w_000001_sz` |
| 月线行情 | `monthly` | `m_` | `m_000001_sz` |
| 利润表 | `income` | `pi_` | `pi_000001_sz` |
| 资产负债表 | `balancesheet` | `bs_` | `bs_000001_sz` |
| 现金流量表 | `cashflow` | `cf_` | `cf_000001_sz` |
| 融资融券 | `margin` | `mg_` | `mg_000001_sz` |
| 资金流向 | `moneyflow` | `mf_` | `mf_000001_sz` |

**命名规则：**
1. 前缀必须小写 + 下划线
2. 股票代码中的 `.` 和 `-` 替换为 `_`
3. 最终格式示例：`d_000001_sz`、`n_000001_sh`

### 5.2 子表创建

子表无需预先创建，在首次插入数据时通过 `CREATE TABLE IF NOT EXISTS` 自动创建：

```sql
CREATE TABLE IF NOT EXISTS your_db.d_000001_sz USING your_db.daily TAGS ('000001.SZ')
```

规则：
1. 子表始终使用 `USING` 关键字关联超级表
2. `TAGS` 中的标签值必须与超级表中 TAGS 定义的顺序一致
3. 插入前优先使用 `CREATE TABLE IF NOT EXISTS`，避免因表不存在导致插入失败
4. 数据同步脚本中，应在首次插入失败时回退到 CREATE 再重试

---

## 六、数据插入规范

### 6.1 超级表插入

使用 `INSERT INTO ... USING ... TAGS ... VALUES` 模式：

```sql
INSERT INTO your_db.d_000001_sz USING your_db.daily
TAGS ('000001.SZ')
(ts, open, high, low, close, pre_close, change, pct_chg, vol, amount)
VALUES ('2026-01-02 00:00:00', 10.5, 11.2, 10.3, 10.8, 10.6, 0.2, 1.89, 500000, 5250000)
```

### 6.2 批量插入

大数据量写入必须使用批量 INSERT，单条 SQL 包含多组 VALUES：

```sql
INSERT INTO your_db.d_000001_sz USING your_db.daily
TAGS ('000001.SZ')
(ts, open, high, low, close, pre_close, change, pct_chg, vol, amount)
VALUES
('2026-01-02 00:00:00', 10.5, 11.2, 10.3, 10.8, 10.6, 0.2, 1.89, 500000, 5250000),
('2026-01-03 00:00:00', 10.8, 11.0, 10.6, 10.9, 10.8, 0.1, 0.93, 480000, 5040000)
```

### 6.3 分批策略

```python
def insert_dataframe_to_td(table_name: str, df: pd.DataFrame) -> int:
    for ts_code, group in df.groupby("ts_code", sort=False):
        ts_code_str = str(ts_code)
        sub_table = prefix + ts_code_str.replace(".", "_").replace("-", "_")
        for i in range(0, len(group), batch_size):
            batch = group.iloc[i:i + batch_size]
            stmt = (
                f"INSERT INTO {_TD_DB}.{sub_table} USING {table_name} "
                f"TAGS ('{ts_code_str}') "
                f"({col_list_str}) VALUES {', '.join(batch)}"
            )
            td.execute(stmt)
```

**规则：**
1. 按 `ts_code`（股票代码）分组批量插入，每组对应一个子表
2. 每批最多 **500 行**（td_utils.py 中的默认值），避免单条 SQL 过长
3. 批量 INSERT 不返回影响行数时，通过计数估算
4. 时间戳列使用 `YYYY-MM-DD HH:MM:SS` 格式或 pandas Timestamp 自动转换

### 6.4 普通表插入（无标签）

对于不需要按股票代码分区的数据（如大盘资金流向、沪深港通数据），使用普通表直接插入：

```python
def insert_plain_table(table_name: str, df: pd.DataFrame, ts_col: str = "trade_date") -> int:
    for _, row in df.iterrows():
        vals = [_format_value(row[col], col) for col in df.columns]
        sql = f"INSERT INTO {_TD_DB}.{table_name} ({', '.join(df.columns)}) VALUES ({', '.join(vals)})"
        td.execute(sql)
```

**规则：**
1. 普通表直接向超级表插入（无需子表）
2. 空标签超级表 `TAGS ()` 使用普通表插入方式
3. 普通表插入默认逐行执行，批量优化同 6.3

---

## 七、列定义与字段映射

### 7.1 列定义映射表

在 `td_utils.py` 中维护 `_TD_COLUMNS_MAP`，定义每个超级表的完整列列表：

```python
_TD_COLUMNS_MAP = {
    "daily": [
        "ts", "open", "high", "low", "close",
        "pre_close", "change", "pct_chg", "vol", "amount"
    ],
    "income": [
        "ts", "basic_eps", "diluted_eps",
        "total_revenue", "revenue", "oper_cost",
        ...
    ],
    "stk_mins": [
        "ts", "freq_type", "open", "high", "low", "close",
        "vol", "amount", "pre_close", "change", "pct_chg"
    ],
}
```

### 7.2 源字段到 TDengine 字段映射

在 `td_utils.py` 中维护 `_TD_FIELD_MAP`，定义 Tushare 数据源字段到 TDengine 列名的映射：

```python
_TD_FIELD_MAP = {
    "daily": {
        "trade_date": "ts",
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "close",
        "pre_close": "pre_close",
        "change": "change",
        "pct_chg": "pct_chg",
        "vol": "vol",
        "amount": "amount",
    },
    "income": {
        "ann_date": "ts",
        "f_ann_date": "ts",
        "end_date": "end_date",
        ...
    },
}
```

**规则：**
1. 每个超级表必须维护完整的 `_TD_COLUMNS_MAP` 和 `_TD_FIELD_MAP` 条目
2. 时间列统一映射为 `ts`
3. 源数据中不存在的列不进行映射
4. 新增超级表时必须同步更新两个映射表

### 7.3 子表前缀映射

```python
_TABLE_PREFIX = {
    "daily": "d_",
    "stk_mins": "n_",
    "weekly": "w_",
    "monthly": "m_",
    "adj_factor": "a_",
    "income": "pi_",
    "balancesheet": "bs_",
    "cashflow": "cf_",
    ...
}
```

**规则：**
1. 前缀必须简短（2-3 字符），不与现有前缀冲突
2. 新增超级表时必须同步添加前缀映射

---

## 八、查询规范

### 8.1 基本查询

```python
from utils.util_db import get_tdengine

td = get_tdengine()

# 查询单个子表
rows = td.query("SELECT * FROM your_db.d_000001_sz WHERE ts >= '2026-01-01'")

# 查询超级表（跨所有子表）
rows = td.query("SELECT * FROM your_db.daily WHERE ts >= '2026-01-01'")

# 通过标签过滤子表
rows = td.query(
    "SELECT * FROM your_db.daily WHERE ts_code = '000001.SZ' AND ts >= '2026-01-01'"
)
```

### 8.2 聚合查询

```python
rows = td.query("""
    SELECT AVG(close), MAX(high), MIN(low)
    FROM your_db.daily
    WHERE ts >= '2026-01-01' AND ts_code = '000001.SZ'
    INTERVAL(1d)
""")

# TIMESTAMP 列的时间边界查询使用 FIRST/LAST，而非 MIN/MAX
rows = td.query("SELECT FIRST(ts), LAST(ts) FROM your_db.daily")
# MIN(ts) / MAX(ts) 在 TDengine 的 TIMESTAMP 列上不支持，会报错:
# [0x2802]: Invalid parameter data type : min
```

### 8.3 查询规则

1. 查询时尽可能指定时间范围以加速检索
2. 大结果集使用 `INTERVAL` 窗口聚合避免内存溢出
3. 跨子表查询直接对超级表进行，由 TDengine 自动路由
4. 查询结果通过 `td.query()` 返回 `List[Tuple]`，如需 DataFrame 在调用方转换
5. 禁止 `SELECT *` 查询无时间过滤条件的大表全量数据
6. **TIMESTAMP 列的时间边界查询使用 `FIRST(ts)` / `LAST(ts)`**，`MIN(ts)` / `MAX(ts)` 在 TDengine 中不支持

---

## 九、DDL 管理

### 9.1 DDL 文件组织

```
src/batch/sql/tdengine/
├── 股票数据.sql           # 行情、财务、融资融券等
├── 指数专题.sql           # 指数相关数据
├── 期货数据.sql           # 期货行情
├── 期权数据.sql           # 期权数据
├── 港股数据.sql           # 港股行情
├── 美股数据.sql           # 美股行情
├── 宏观经济.sql           # 宏观指标
├── 现货数据.sql           # 大宗商品现货
├── 外汇数据.sql           # 外汇行情
├── 公募基金.sql           # 基金数据
├── 债券专题.sql           # 债券数据
├── ETF专题.sql            # ETF 数据
└── 大模型语料专题数据.sql  # LLM 语料
```

### 9.2 全量同步时的表处理

```python
from sync_utils import clear_tdengine_supertable, insert_tdengine_supertable

td = get_tdengine()

# 删除旧的超级表
clear_tdengine_supertable("your_db", "daily")

# 重新创建
td.execute("""
    CREATE STABLE IF NOT EXISTS your_db.daily (
        ts TIMESTAMP, open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE,
        pre_close DOUBLE, change DOUBLE, pct_chg DOUBLE, vol DOUBLE, amount DOUBLE
    ) TAGS (ts_code NCHAR(100))
""")

# 插入数据
insert_tdengine_supertable("your_db", "daily", df, columns, tag_col="ts_code", ts_col="ts")
```

### 9.3 规则

1. **全量同步**：使用 `DROP STABLE IF EXISTS` → `CREATE STABLE` 重建表结构
2. **增量同步**：使用 `CREATE STABLE IF NOT EXISTS` 确保表存在，不删除已有数据
3. 子表通过 `CREATE TABLE IF NOT EXISTS ... USING ... TAGS` 自动创建
4. 禁止手动创建子表，统一通过代码自动管理
5. DDL 文件是表结构的**声明式定义**，同步脚本依赖配套 SQL 文件
6. 修改表结构（加列、改列）后必须更新对应的 DDL SQL 文件和 `_TD_COLUMNS_MAP`

---

## 十、错误处理

### 10.1 连接错误

```python
from utils.util_db import get_tdengine

try:
    td = get_tdengine()
    td.execute("SELECT 1")
except ConnectionError as e:
    logger.error("TDengine 连接失败", operation="td_connect", error_code=type(e).__name__)
    raise
```

### 10.2 执行错误

```python
try:
    td.execute(sql)
except Exception as e:
    error_msg = str(e)
    # 常见的 TDengine 错误码
    # [0x2602]: 列名无效
    # [0x0200]: tbname 列不能为空
    # [0x0600]: 表不存在
    logger.error(
        message=f"TDengine SQL 执行失败: {error_msg}",
        operation="td_execute",
        error_code=type(e).__name__,
    )
    raise
```

### 10.3 插入容错

```python
def safe_insert(supertable: str, subtable: str, tag: str, sql: str):
    try:
        td.execute(sql)
    except Exception:
        # 子表不存在，先创建再重试
        create_sql = (
            f"CREATE TABLE IF NOT EXISTS {subtable} "
            f"USING {supertable} TAGS ('{tag}')"
        )
        td.execute(create_sql)
        td.execute(sql)
```

### 10.4 规则

1. 所有 TDengine 操作必须包裹 try/except 并记录到日志
2. 连接失败必须有重试机制（最多 3 次，间隔递增）
3. 插入失败应优先尝试 `CREATE TABLE IF NOT EXISTS` 再重试
4. 错误日志必须包含错误码、SQL 语句摘要、操作名称
5. 批量操作中某批失败不应影响其他批次

---

## 十一、性能优化

### 11.1 批量写入

1. 批量插入时每组 VALUES 控制在 **500 行**以内
2. 使用 `queue.Queue` 连接池避免频繁创建/销毁连接
3. 写入前按 `ts_code` 分组，减少子表切换

### 11.2 查询优化

1. 查询时必须包含时间范围过滤
2. 优先使用超级表 + 标签过滤，避免扫描所有子表
3. 大结果集使用 `INTERVAL` 窗口聚合降低数据量
4. 避免在 WHERE 条件中使用函数包装时间列

### 11.3 连接池

1. 最大连接数根据并发度合理设置（默认 10）
2. 写入超时设置合理值（默认 30 秒）
3. 开启 `auto_reconnect` 应对网络抖动

---

## 十二、超级表清单

| 类别 | DDL 文件 | 超级表数量 |
|------|---------|-----------|
| 股票行情数据 | `股票数据.sql` | ~60 |
| 指数专题数据 | `指数专题.sql` | ~10 |
| 期货数据 | `期货数据.sql` | ~10 |
| 期权数据 | `期权数据.sql` | ~10 |
| 港股数据 | `港股数据.sql` | ~15 |
| 美股数据 | `美股数据.sql` | ~10 |
| 宏观经济 | `宏观经济.sql` | ~10 |
| 现货数据 | `现货数据.sql` | ~10 |
| 外汇数据 | `外汇数据.sql` | ~10 |
| 公募基金 | `公募基金.sql` | ~15 |
| 债券专题 | `债券专题.sql` | ~10 |
| ETF 专题 | `ETF专题.sql` | ~10 |
| LLM 语料 | `大模型语料专题数据.sql` | ~5 |

---

## 十三、扩展开发规范

### 13.1 新增 TDengine 工具函数

1. 通用 TDengine 工具函数放在 `src/utils/td_utils.py` 中
2. 跨项目共用的工具函数应提升到 hetu-aether 的 `utils/` 中
3. 函数命名使用小写 + 下划线，如 `insert_dataframe_to_td()`

### 13.2 新增超级表流程

1. 在 `src/batch/sql/tdengine/` 对应 SQL 文件中添加 `CREATE STABLE IF NOT EXISTS` 语句
2. 在 `td_utils.py` 的 `_TD_COLUMNS_MAP` 中添加列定义
3. 在 `td_utils.py` 的 `_TD_FIELD_MAP` 中添加字段映射
4. 在 `td_utils.py` 的 `_TABLE_PREFIX` 中添加子表前缀
5. 编写对应的数据同步函数
6. 添加对应的 shell 脚本任务
7. 编写单元测试覆盖插入和查询场景

### 13.3 代码审查要点

1. 是否使用了 `get_tdengine()` 单例
2. 连接是否通过上下文管理器正确归还
3. SQL 是否使用参数化查询
4. 批量插入是否控制了批次大小
5. 错误处理是否完整（连接失败、插入失败）
6. 时间戳列是否命名为 `ts`
7. 是否复用了已有的 `td_utils` 方法
