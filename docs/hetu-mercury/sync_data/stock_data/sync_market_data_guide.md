# 股票行情数据同步指南

> 更新日期：2026-05-15 | 同步模块：`src/data_sync/full_sync/stock_data/sync_market_data_bydate.py`

---

## 一、接口总览（15 个）

### TDengine 入库（12 个）

| 接口 | 中文名称 | 表名 | 同步策略 | 当前行数 | 最早日期 | 最晚日期 |
|------|---------|------|---------|---------|---------|---------|
| daily | 历史日线 | daily | 按交易日逐日拉取，200日/批聚合插入 | 15,544,648 | 2005-01-04 | 2026-05-15 |
| weekly | 周线行情 | weekly | 按周末最后交易日拉取，200天/批 | 3,120,316 | 2005-01-07 | 2026-05-15 |
| monthly | 月线行情 | monthly | 按月最后交易日拉取，50天/批 | 740,770 | 2005-01-31 | 2026-04-30 |
| adj_factor | 复权因子 | adj_factor | 按交易日逐日，200天/批 | 16,329,519 | 2005-01-04 | 2026-05-15 |
| daily_basic | 每日指标 | daily_basic | 按交易日逐日，200天/批 | 15,453,148 | 2005-01-04 | 2026-05-15 |
| stk_limit | 每日涨跌停 | stk_limit | 按交易日逐日，200天/批 | 17,441,905 | 2007-01-04 | 2026-05-15 |
| stk_weekly_monthly | 周/月线(每日更新) | stk_weekly_monthly | 按周末交易日，freq=week | **未执行** | — | — |
| stk_week_month_adj | 周/月复权(每日更新) | stk_weekly_monthly | 按周末交易日，freq=week，暂入 stk_weekly_monthly | **未执行** | — | — |
| stk_mins | 历史分钟(15min) | stk_mins | 按股票×年份分段（每年<8000行），50只/批 | 230,551,310 | 2010-01-04 | 2026-05-15 |
| hsgt_top10 | 沪深股通十大成交 | hsgt_top10 | 按月范围查询（月初至月末），200天/批 | 39,610 | 2014-11-17 | 2026-05-15 |
| ggt_top10 | 港股通十大成交 | ggt_top10 | 按交易日逐日（不支持范围查询） | 35,369 | 2014-11-17 | 2026-05-15 |
| ggt_daily | 港股通每日成交 | ggt_daily | 按月范围查询（月初至月末），普通表逐行插入 | 2,618 | 2015-01-04 | 2026-05-15 |
| ggt_monthly | 港股通每月成交 | ggt_monthly | 按年范围查询，普通表逐行插入 | 74 | 2014-11-01 | **2020-11-30** ⚠️ |

### GreatSQL 入库（1 个）

| 接口 | 中文名称 | 表名 | 同步策略 | 当前行数 | 最早日期 | 最晚日期 |
|------|---------|------|---------|---------|---------|---------|
| suspend_d | 每日停复牌 | suspend_d | 按交易日逐日，200天/批批入库 | 594,851 | 2005-01-04 | 2026-05-15 |

### 通用行情接口（1 个）

| 接口 | 中文名称 | 入表 | 同步策略 |
|------|---------|------|---------|
| pro_bar | 通用行情(日线复权) | daily | 按 ts_code 循环拉取，入 daily 表 |

> **总计**：TDengine 约 299,259,287 行 + GreatSQL 594,851 行（2026-05-15 数据探查核对）

---

## 二、执行方式

### 2.1 Shell 脚本（推荐）

```bash
# 全量同步 — 所有 15 个接口
bash scripts/stock_data/sync_market_data.sh

# 从指定日期至今
bash scripts/stock_data/sync_market_data.sh 20260401

# 指定日期范围（增量）
bash scripts/stock_data/sync_market_data.sh 20260401 20260430

# 日常增量（最近3天，非交易日自动返回0行）
bash scripts/stock_data/sync_market_data.sh 20260430 20260503

# 仅重跑修复接口（suspend_d / hsgt_top10 / ggt_daily / ggt_monthly）
bash scripts/stock_data/sync_market_data_fix.sh
```

### 2.2 Python 直接调用

```python
from sync_market_data_bydate import sync_daily, sync_weekly, sync_stk_mins

# 全量（2005年至今）：不传参
sync_daily()
sync_weekly()

# 增量（仅追加，不删已有数据）：传 start_date/end_date
sync_daily(start_date="20260430", end_date="20260503")
sync_weekly(start_date="20260401", end_date="20260503")

# stk_mins 分阶段同步
sync_stk_mins(start_date="20150101", end_date="20260503")   # 2015年至今
sync_stk_mins(start_date="20050101", end_date="20141231")   # 2005-2014年
```

> **全量 vs 增量**：
> - **不传参数** → 使用默认起始日期全量拉取
> - **传 start_date/end_date** → 不删已有数据，仅追加新数据
> - **TDengine 自动去重**：同子表+时间戳唯一，重复 INSERT 自动跳过
> - **suspend_d 全量时清表**：仅当 start_date == 默认值(20050101)时清表，增量走 INSERT IGNORE

---

## 三、各接口起始日期参考

| 接口 | 默认起始日期 | 说明 |
|------|-------------|------|
| daily | 2005-01-01 | A股日线最早数据 |
| weekly | 2005-01-01 | 按周末交易日 |
| monthly | 2005-01-01 | 按月最后交易日 |
| adj_factor | 2005-01-01 | 复权因子 |
| daily_basic | 2005-01-01 | 每日基本面指标 |
| stk_limit | 2005-01-01 | 每日涨跌停 |
| suspend_d | 2005-01-01 | 每日停复牌 |
| stk_mins | 2015-01-01 | 分钟数据，建议分两段执行 |
| hsgt_top10 | 2014-11-17 | 沪港通开通日 |
| ggt_top10 | 2014-11-17 | 港股通开通日 |
| ggt_daily | 2015-01-01 | 2014年底数据不稳定 |
| ggt_monthly | 2014-11-01 | 最早数据2014年11月 |

---

## 四、速率限制

所有接口共享全局 `RateLimiter(300次/分钟)`，确保 Tushare API 不超限。

| 接口 | API限制 | 实际调用量（全量） | 预估耗时 |
|------|--------|-------------------|---------|
| daily | 500次/分, 6000条/次 | ~5,565次 (逐日) | ~20分钟 |
| stk_mins | 8000条/次 | ~66,144次 (5512股×12年) | ~4小时 |
| ggt_top10 | 不支持范围查询 | ~2,990次 (逐日) | ~11分钟 |
| 其他 | — | 数百次 (按月/按年范围) | ~数分钟 |

---

## 五、TDengine 插入机制

### 5.1 子表+时间戳唯一

TDengine 超级表中，同一子表的相同时间戳 INSERT 会自动去重，**不会产生重复行**。增量更新无需先删后插。

### 5.2 批量插入优化

```python
# td_utils.insert_dataframe_to_td()
# 每个 stock 生成一条 INSERT ... USING ... TAGS (...) VALUES (...)
# 格式: INSERT INTO qmt_ai.d_000001_sz USING daily TAGS ('000001.SZ') (ts, ...) VALUES (...)
```

### 5.3 子表命名规则

| 超级表 | 前缀 | 示例 |
|--------|------|------|
| daily | d_ | d_000001_sz |
| weekly | w_ | w_000001_sz |
| monthly | m_ | m_000001_sz |
| adj_factor | a_ | a_000001_sz |
| daily_basic | b_ | b_000001_sz |
| stk_limit | l_ | l_000001_sz |
| stk_mins | n_ | n_000001_sz |
| stk_weekly_monthly | s_ | s_000001_sz |
| hsgt_top10 | h_ | h_000001_sz |
| ggt_top10 | g_ | g_000001_sz |

### 5.4 普通表

ggt_daily 和 ggt_monthly 为普通表（非超级表），无 ts_code 分组，通过 `insert_plain_table()` 逐行插入。

---

## 六、特殊说明

### 6.1 weekly / monthly — 仅支持 trade_date

Tushare 的 weekly 和 monthly 接口**不支持**仅传 start_date/end_date（必须搭配 ts_code）。因此改为按 `trade_date`（周末/月末最后交易日）逐日调用，返回当日全市场数据。

### 6.2 ggt_top10 — 不支持范围查询

该接口仅支持 `trade_date` 参数，无法使用 start_date/end_date 批量查询，必须逐日调用。

### 6.3 stk_mins — 分年分段

每只股票每年 15min 数据约 4000 行，Tushare 单次限制 8000 行，因此按年分段拉取。**建议分两阶段**：
1. 2015-2026（12年，约 4 小时）
2. 2005-2014（10年，约 3 小时）

### 6.4 suspend_d — 全量清表

该表入 GreatSQL，全量同步时 `clear_table()` 清空重拉。增量时走 `INSERT IGNORE` + UNIQUE KEY 去重。

### 6.5 daily 分块处理

daily 数据量大（15M+ 行），采用 200 天/批的分块处理：
1. 拉取 200 天数据 → 按股票聚合
2. 批量 INSERT 到 TDengine → 释放内存
3. 下一批

### 6.6 hsgt_top10 / ggt_daily — end_date 取月末

hsgt_top10 和 ggt_daily 使用 `_generate_month_ranges()` 生成月份列表后，通过 `_month_last_day(em)` 计算月末日期作为 `end_date`，而非固定取 01 或 28 号，避免漏掉月中交易数据。

### 6.7 daily_basic 北交所覆盖

Tushare `daily_basic` 接口在 2023 年之前未覆盖北交所(BJ)股票的指标数据（PE/PB/股息率等），导致 daily_basic 比 daily 少约 91,500 条记录。此差异为上游 API 数据限制，非同步异常。

### 6.8 ggt_monthly 数据截止

Tushare `ggt_monthly` 接口自 2020-12 月起停止返回数据（上游停更），当前数据截止于 2020-11-30。

---

## 七、依赖模块

```
src/utils/sync_utils.py          # GreatSQL 工具（RateLimiter, insert_dataframe 等）
src/utils/td_utils.py            # TDengine 批量插入工具（insert_dataframe_to_td）
src/data_sync/full_sync/stock_data/
└── sync_market_data_bydate.py   # 15个行情接口同步脚本
scripts/stock_data/
├── sync_market_data.sh          # Shell 脚本（全量/增量）
└── sync_market_data_fix.sh      # Shell 脚本（单独重跑修复接口）
```

---

## 八、Tushare 积分权限要求

| 接口 | 积分要求 | 备注 |
|------|---------|------|
| daily | 2,000 | 500次/分钟 |
| weekly | 2,000 | — |
| monthly | 2,000 | — |
| adj_factor | 2,000 | — |
| daily_basic | 2,000 | — |
| stk_limit | 2,000 | — |
| suspend_d | 2,000 | — |
| stk_mins | 在线开通 | 分钟权限需单独开通 |
| stk_weekly_monthly | 2,000 | — |
| stk_week_month_adj | 2,000 | — |
| hsgt_top10 | 3,000 | — |
| ggt_top10 | 3,000 | — |
| ggt_daily | 3,000 | — |
| ggt_monthly | 3,000 | — |
| pro_bar | 2,000 | — |
