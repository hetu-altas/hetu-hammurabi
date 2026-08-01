# 期权专题数据同步指南

> 更新日期：2026-05-18 | 同步模块：`src/data_sync/full_sync/sync_option_data_bydate.py`

---

## 一、接口总览（2 个）

### GreatSQL 入库（1 个）

| 接口 | 中文名称 | 表名 | 同步策略 | 数据量 | 最早日期 | 最晚日期 |
|------|---------|------|---------|--------|---------|---------|
| opt_basic | 期权合约信息 | opt_basic | 按 exchange × opt_code 分片，INSERT IGNORE 去重 | 66,378 | 2015-02-09 | 2026-05-15 |

**opt_basic 按交易所分布**：
| 交易所 | 数据量 | 占比 | 说明 |
|--------|--------|------|------|
| SHFE | 13,216 | 19.9% | ✓ |
| CZCE | 12,192 | 18.4% | ✓ |
| DCE | 12,056 | 18.2% | ✓ |
| SSE | 11,632 | 17.5% | ✓ |
| CFFEX | 9,744 | 14.7% | ✓ |
| SZSE | 7,538 | 11.4% | ✓ |

### TDengine 入库（1 个）

| 接口 | 中文名称 | 表名 | 同步策略 | 数据量 | 最早日期 | 最晚日期 |
|------|---------|------|---------|--------|---------|---------|
| opt_daily | 期权日线行情 | opt_daily | 按 exchange × month_ranges 循环（15000条/次限制） | 5,432,485 | 2020-01-02 | 2026-05-15 |

**opt_daily 按交易所分布**：
| 交易所 | 数据量 | 占比 |
|--------|--------|------|
| SHFE | 1,155,000 | 21.5% |
| DCE | 1,152,980 | 21.4% |
| CZCE | 1,152,170 | 21.4% |
| CFFEX | 761,154 | 14.2% |
| SSE | 645,141 | 12.0% |
| SZSE | 511,236 | 9.5% |

> **总计**：GreatSQL 66,378 行 + TDengine opt_daily 5,432,485 行

---

## 二、执行方式

### 2.1 Shell 脚本

```bash
# 基础数据全量（仅初次部署/数据重建，与日期无关）
bash scripts/sync_option_data_all.sh

# 历史行情按日期同步（日常增量）
bash scripts/sync_option_data.sh                            # 全量 (2005-01-01 至今)
bash scripts/sync_option_data.sh 20260401                   # 从指定日期至今
bash scripts/sync_option_data.sh 20260401 20260430          # 指定日期范围

# 全量重建（清表 + opt_basic 三重分片 + opt_daily 全量）
bash scripts/resync_option_rebuild.sh
```

### 2.2 Python 直接调用

```python
from sync_option_data_bydate import (
    sync_opt_basic, sync_opt_daily,
)

# GreatSQL 基础数据（全量拉取，不传参）
sync_opt_basic()

# TDengine 历史行情（全量）
sync_opt_daily()

# TDengine 增量（传日期参数）
sync_opt_daily(start_date="20260506", end_date="20260507")
```

> **全量 vs 增量**：
> - **不传参数** → 使用默认起始日期（2005-01-01）全量拉取
> - **传 start_date/end_date** → 不删已有数据，仅追加新数据
> - **TDengine 自动去重**：同子表+时间戳唯一，重复 INSERT 自动跳过
> - **opt_basic** → 全量拉取 + INSERT IGNORE 去重，不会重复插入

---

## 三、各接口起始日期与限制

| 接口 | 默认起始日期 | Tushare限制 | 说明 |
|------|-------------|------------|------|
| opt_basic | — | 需5000积分 | 按6个交易所(SSE/SZSE/CFFEX/DCE/SHFE/CZCE)分片拉取 |
| opt_daily | 2005-01-01 | **15000条/次**，按 exchange × month 循环 | 单日全市场数据达15000条上限，必须按交易所分片 |
| opt_mins | 2005-01-01 | **8000条/次**，按 ts_code × freq 循环 | 单合约月数据<1000条，月区间安全 |

> **重要发现**：opt_daily 单日全市场数据已达 14410 条，接近 15000 上限，必须按交易所分片拉取：
> - DCE: 7190条
> - CZCE: 4116条
> - SHFE: 1500条
> - CFFEX: 656条
> - SSE: 528条
> - SZSE: 420条

---

## 四、速率限制

所有接口共享全局 `RateLimiter(300次/分钟)`，确保 Tushare API 不超限。

| 接口 | API限制 | 实际调用量（全量） | 预估耗时 |
|------|--------|-------------------|---------|
| opt_basic | 无明确限制 | 6次（6个交易所） | ~6秒 |
| opt_daily | 15000条/次 | 6交易所 × 月份数 | ~5分钟 |
| opt_mins | 8000条/次 | 合约数 × 1频率 × 月份数 | ~10分钟 |

---

## 五、TDengine 插入机制

### 5.1 子表+时间戳唯一

TDengine 超级表中，同一子表的相同时间戳 INSERT 会自动去重，**不会产生重复行**。增量更新无需先删后插。

### 5.2 批量插入优化

```python
# td_utils.insert_dataframe_to_td()
# 每个 ts_code 生成一条 INSERT ... USING ... TAGS (...) VALUES (...)
# 格式: INSERT INTO qmt_ai.od_10001313_SH USING opt_daily TAGS ('10001313.SH') (ts, ...) VALUES (...)

# td_utils.insert_dataframe_to_td_multi_tags()
# 多TAG表（如opt_mins包含ts_code和freq两个TAG）
# 格式: INSERT INTO qmt_ai.om_10001313_SH_15min USING opt_mins TAGS ('10001313.SH', '15min') VALUES (...)
```

### 5.3 子表命名规则

| 超级表 | 前缀 | TAG | 示例 |
|--------|------|-----|------|
| opt_daily | od_ | ts_code | od_10001313_SH |
| opt_mins | om_ | ts_code, freq | om_10001313_SH_15min |

### 5.4 时间字段映射

| 接口 | API字段 | TDengine ts | 格式处理 |
|------|---------|-------------|---------|
| opt_daily | trade_date | ts | YYYYMMDD → YYYY-MM-DD 00:00:00 |
| opt_mins | trade_time | ts | 直接使用（YYYY-MM-DD HH:MM:SS） |

### 5.5 列类型说明

| 表 | 特殊列 | 类型 | 说明 |
|----|--------|------|------|
| opt_daily | vol, amount | DOUBLE | 成交量(手)、成交额(万元) |
| opt_daily | oi | DOUBLE | 持仓量(手) |
| opt_mins | vol | BIGINT | 成交量可能超INT上限 |
| opt_mins | oi | DOUBLE | 持仓量 |

---

## 六、特殊说明

### 6.1 opt_daily — 按交易所分片

**关键策略**：单日全市场期权数据已达 14410 条，接近 API 15000 条上限，必须按交易所分片拉取。

```python
# 错误方式（会截断）
fetch_opt_daily(trade_date='20240102')  # 返回15000条，截断数据

# 正确方式
for exchange in ['SSE', 'SZSE', 'CFFEX', 'DCE', 'SHFE', 'CZCE']:
    fetch_opt_daily(exchange=exchange, trade_date='20240102')  # 每个交易所<8000条
```

### 6.2 opt_mins — 仅同步15分钟频率

默认只同步 `freq='15min'` 数据，降低 API 调用量：

```python
_FREQS: List[str] = ["15min"]  # 仅15分钟频率
```

**数据量分析**：
- 理论最大值：16个时间点/天 × 22天 = 352条/月
- 实际数据量：单合约月数据 < 1000条
- API上限：8000条
- **结论**：月区间策略安全，不会超限

### 6.3 opt_mins — 双TAG机制

opt_mins 超级表包含两个 TAG：
- `ts_code`：期权合约代码
- `freq`：分钟频度（15min）

使用 `insert_dataframe_to_td_multi_tags()` 函数处理多TAG插入：

```python
insert_dataframe_to_td_multi_tags("opt_mins", df, ["ts_code", "freq"])
```

### 6.4 空时间戳过滤

**防止 TDengine 报错**：过滤掉 trade_date/trade_time 为空的行：

```python
# opt_daily
df = df.dropna(subset=['trade_date'])

# opt_mins
df = df.dropna(subset=['trade_time'])
```

> **报错示例**：`[0x0216]: Primary timestamp column should not be null`

### 6.5 opt_basic — 按交易所循环

opt_basic 不支持日期参数，按6个交易所分片全量拉取：

```python
_EXCHANGES: List[str] = ["SSE", "SZSE", "CFFEX", "DCE", "SHFE", "CZCE"]

for exchange in _EXCHANGES:
    df = fetch_opt_basic(exchange=exchange)
    insert_dataframe("opt_basic", df, columns)
```

---

## 七、依赖模块

```
src/utils/sync_utils.py                      # GreatSQL 工具（RateLimiter, insert_dataframe 等）
src/utils/td_utils.py                        # TDengine 批量插入工具（insert_dataframe_to_td, insert_dataframe_to_td_multi_tags）
src/fetch_tushare_data/option/                # 3个 fetch 接口实现
├── fetch_opt_basic.py
├── fetch_opt_daily.py
└── fetch_opt_mins.py
src/data_sync/full_sync/
└── sync_option_data_bydate.py                # 3个期权接口同步脚本
scripts/
├── sync_option_data_all.sh                   # 基础数据全量同步
├── sync_option_data.sh                       # 历史行情按日期同步
└── resync_option_rebuild.sh                  # 全量重建（opt_basic三重分片 + opt_daily全量）
```

---

## 八、Tushare 积分权限要求

| 接口 | 积分要求 | 备注 |
|------|---------|------|
| opt_basic | 5,000 | 需5000积分可调取 |
| opt_daily | 2,000+ | 需2000积分可调取，5000分以上频次更高 |

---

## 九、数据库分类原则

| 数据库 | 适用场景 | 期权数据中的体现 |
|--------|---------|----------------|
| **GreatSQL** | 基础信息、映射关系、不频繁变动的参考数据 | opt_basic（合约信息、交易所、行权价、到期日等） |
| **TDengine** | 时序数据、按时间轴查询、高频更新的行情/指标 | opt_daily（日线行情）、opt_mins（分钟行情） |

---

## 十、数据库表结构

### 10.1 GreatSQL - opt_basic

```sql
CREATE TABLE `opt_basic` (
  `id` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `ts_code` VARCHAR(30) COMMENT 'TS代码',
  `exchange` VARCHAR(20) COMMENT '交易市场',
  `name` VARCHAR(100) COMMENT '合约名称',
  `per_unit` VARCHAR(50) COMMENT '合约单位',
  `opt_code` VARCHAR(30) COMMENT '标的合约代码',
  `opt_type` VARCHAR(50) COMMENT '合约类型',
  `call_put` VARCHAR(10) COMMENT '期权类型',
  `exercise_type` VARCHAR(20) COMMENT '行权方式',
  `exercise_price` DECIMAL(18,4) COMMENT '行权价格',
  `s_month` VARCHAR(20) COMMENT '结算月',
  `maturity_date` DATE COMMENT '到期日',
  `list_price` DECIMAL(18,4) COMMENT '挂牌基准价',
  `list_date` DATE COMMENT '开始交易日期',
  `delist_date` DATE COMMENT '最后交易日期',
  `last_edate` DATE COMMENT '最后行权日期',
  `last_ddate` DATE COMMENT '最后交割日期',
  `quote_unit` VARCHAR(50) COMMENT '报价单位',
  `min_price_chg` VARCHAR(50) COMMENT '最小价格波幅',
  KEY `idx_ts_code` (`ts_code`),
  KEY `idx_exchange` (`exchange`)
);
```

### 10.2 TDengine - opt_daily

```sql
CREATE STABLE `opt_daily` (
  `ts` TIMESTAMP COMMENT '交易日期',
  `exchange` NCHAR(20) COMMENT '交易市场',
  `pre_settle` DOUBLE COMMENT '昨结算价',
  `pre_close` DOUBLE COMMENT '前收盘价',
  `open` DOUBLE COMMENT '开盘价',
  `high` DOUBLE COMMENT '最高价',
  `low` DOUBLE COMMENT '最低价',
  `close` DOUBLE COMMENT '收盘价',
  `settle` DOUBLE COMMENT '结算价',
  `vol` DOUBLE COMMENT '成交量(手)',
  `amount` DOUBLE COMMENT '成交金额(万元)',
  `oi` DOUBLE COMMENT '持仓量(手)'
) TAGS (
  `ts_code` NCHAR(30) COMMENT 'TS合约代码'
);
```

### 10.3 TDengine - opt_mins

```sql
CREATE STABLE `opt_mins` (
  `ts` TIMESTAMP COMMENT '交易时间',
  `open` DOUBLE COMMENT '开盘价',
  `close` DOUBLE COMMENT '收盘价',
  `high` DOUBLE COMMENT '最高价',
  `low` DOUBLE COMMENT '最低价',
  `vol` BIGINT COMMENT '成交量',
  `amount` DOUBLE COMMENT '成交金额',
  `oi` DOUBLE COMMENT '持仓量'
) TAGS (
  `ts_code` NCHAR(30) COMMENT '期权代码',
  `freq` NCHAR(10) COMMENT '分钟频度(15min)'
);
```

---

## 十一、常见问题

### Q1: opt_daily 为什么按交易所分片？

**答**：单日全市场期权数据已达 14410 条，接近 API 15000 条上限。如果直接按日期拉取，会返回 15000 条截断数据。按交易所分片后，每个交易所单日数据量 < 8000 条，不会截断。

### Q2: opt_mins 为什么只用15分钟频率？

**答**：
1. **数据量安全**：单合约月数据 < 1000条，远低于8000上限
2. **降低调用量**：减少80% API调用（从5个频率改为1个）
3. **实用性**：15分钟频率满足大部分分析需求

### Q3: opt_mins 双TAG如何处理？

**答**：使用 `insert_dataframe_to_td_multi_tags()` 函数，传入 tag_cols 参数 `["ts_code", "freq"]`，自动生成包含两个TAG的INSERT语句。

### Q4: 遇到 "Primary timestamp column should not be null" 报错怎么办？

**答**：这是数据中 trade_date/trade_time 为空导致的。已在代码中添加过滤：
```python
df = df.dropna(subset=['trade_date'])  # opt_daily
df = df.dropna(subset=['trade_time'])  # opt_mins
```

---

## 十二、版本记录

| 日期 | 版本 | 变更内容 |
|------|------|---------|
| 2026-05-10 | v1.0 | 初版：3个接口同步模块，按交易所分片策略，双TAG支持，空值过滤 |
| 2026-05-18 | v1.1 | 数据探查：确认 CZCE/DCE/SHFE opt_basic 12,000 上限截断，opt_daily 健康 |

---

## 十三、数据质量（2026-05-18 探查）

### 数据概况

| 表 | 行数 | 子表数 | 时间范围 | 状态 |
|----|------|--------|---------|------|
| opt_basic | 66,378 | — | — | ✓ 已修复截断 |
| opt_daily | 5,432,485 | 183,805 | 2020-01-02 ~ 2026-05-15 | ✓ 健康 |

### 总体结论

| 检查项 | 结果 |
|--------|------|
| 数据连续性 | ✓ opt_daily 183K 子表，2020~2026 连续 |
| API 截断 | ✓ 已修复：opt_basic 改为 exchange × opt_code 分片（540 opt_codes，每片 < 200 条） |
| 数据重复 | ✓ GreatSQL 零重复；TDengine 同子表+时间戳零重复 |
| 字段 NULL | opt_daily 仅 open/high/low 11.5% NULL（已到期/非交易日） |
| 日期格式 | ✓ 统一正确 |
| 同一日期 | ✓ 无异常 |

### 修复记录

| 修复 | 变更 |
|------|------|
| opt_basic 截断 | `sync_opt_basic` 改为 exchange × opt_code 双重分片，从 6 次 API 调用增至 540 次，每片 < 200 条 |
| opt_mins 移除 | `sync_option_data.sh` 移除 opt_mins（后续不再使用），总接口数从 3 减至 2 |

### 字段 NULL（正常业务）

| 表 | 字段 | NULL率 | 说明 |
|----|------|--------|------|
| opt_basic | list_price | 18.5% | 大量合约无挂牌基准价 |
| opt_basic | last_ddate | 52.5% | 仅已到期合约有最后交割日 |
| opt_daily | open/high/low | 11.5% | 到期合约及非交易日 |