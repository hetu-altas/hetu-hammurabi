# 股票基础数据同步指南

> 更新日期：2026-05-15 | 同步模块：`src/data_sync/full_sync/stock_data/`

---

## 一、接口总览（13 个）

### 与日期无关（sync_basic_data_all.py）

| 接口 | 中文名称 | 表名 | 数据库 | 同步策略 | 当前行数 | 最早日期 | 最晚日期 |
|------|---------|------|--------|---------|---------|---------|---------|
| stock_basic | 股票列表 | stock_basic | GreatSQL | 全量一次拉取 | 5,517 | 1990-12-01 | 2026-05-15 |
| stock_company | 上市公司基本信息 | stock_company | GreatSQL | 按交易所分段（SSE/SZSE/BSE） | 6,271 | 1955-10-01 | 2021-04-15 |
| st_risk_board | ST风险警示板 | st_risk_board | GreatSQL | 从 stock_st 筛选代码循环（~750个），300次/分钟 | 2,841 | 1998-04-28 | 2026-05-15 |
| stk_rewards | 管理层薪酬和持股 | stk_rewards | GreatSQL | 按 ts_code 分批（50个/批） | 441,539 | 2023-12-31 | 2026-03-31 |
| bse_mapping | 北交所新旧代码对照 | bse_mapping | GreatSQL | 全量一次拉取 | 248 | 2020-07-27 | 2024-04-08 |

### 按日期循环（sync_basic_data_bydate.py）

| 接口 | 中文名称 | 表名 | 数据库 | 同步策略 | 当前行数 | 最早日期 | 最晚日期 |
|------|---------|------|--------|---------|---------|---------|---------|
| trade_cal | 交易日历 | trade_cal | GreatSQL | 半个月分批（SSE/SZSE），300次/分钟 | 15,610 | 2005-01-01 | 2026-05-15 |
| stk_premarket | 每日股本（盘前） | stk_premarket | **TDengine** | 逐交易日拉取，300次/分钟，永不清表 | 2,709,757 | 2024-04-10 | 2026-05-15 |
| stock_st | ST股票列表 | stock_st | GreatSQL | 10天分批，300次/分钟 | 284,011 | 2016-08-09 | 2026-05-15 |
| stock_hsgt | 沪深港通股票列表 | stock_hsgt | GreatSQL | 逐日 × 4种type，**180次/分钟独立限速** | 729,003 | 2025-08-12 | 2026-05-15 |
| namechange | 股票曾用名 | namechange | GreatSQL | 半个月分批，300次/分钟，**已加去重** | 6,371 | 2010-06-29 | 2026-05-19 |
| stk_managers | 上市公司管理层 | stk_managers | GreatSQL | 半个月分批，300次/分钟 | 361,913 | 2020-01-01 | 2025-12-30 |
| new_share | IPO新股上市 | new_share | GreatSQL | 半个月分批，300次/分钟 | 1,995 | 2020-01-02 | 2026-05-13 |
| bak_basic | 股票历史列表 | bak_basic | GreatSQL | 按交易日逐日，300次/分钟 | 27,613 | 2026-05-11 | 2026-05-15 |

> **总计**：GreatSQL 1,882,932 行 + TDengine 2,709,757 行 = **4,592,689 行**

---

## 二、执行方式

### 2.1 Shell 脚本（推荐）

```bash
# 与日期无关的 5 个接口全量同步
bash scripts/sync_basic_data_all.sh

# 按日期循环的全量同步（从默认起始到今天）
bash scripts/sync_basic_data_bydate.sh

# 按日期循环的增量更新
bash scripts/sync_basic_data_bydate.sh 20260401              # 从指定日期到今天
bash scripts/sync_basic_data_bydate.sh 20260401 20260430     # 指定日期区间

# 问题数据修复（全量清表重拉有质量问题的接口）
bash scripts/stock_data/sync_fix_data.sh                    # 全量：清表 + 重新同步4个问题接口
bash scripts/stock_data/sync_fix_data.sh 20260501           # 增量：从指定日期到今天
```

### 2.2 Python 直接调用

```python
from sync_basic_data_all import sync_stock_basic, sync_stock_company

# 全量（清表重拉）
sync_stock_basic()
sync_stock_company()
```

```python
from sync_basic_data_bydate import sync_trade_cal, sync_namechange

# 全量（清表重拉）：不传参
sync_trade_cal()

# 增量（仅追加，不清表）：传 start_date/end_date
sync_trade_cal(start_date="20260401", end_date="20260430")
sync_namechange(start_date="20260401", end_date="20260430")
```

> **全量 vs 增量**：
> - **不传参数** → 清空整表后全量拉取（适用于首次加载）
> - **传 start_date/end_date** → 不删已有数据，仅追加新数据（适用于日常增量）

---

## 三、各接口起始日期参考

| 接口 | 默认起始日期 | 说明 |
|------|-------------|------|
| stock_st | 20160101 | Tushare 接口最早支持 20160101 |
| stock_hsgt | 20250812 | 沪深港通数据起始 |
| stk_premarket | 20200101 | 每日股本盘前数据 |
| trade_cal | 20200101 | 交易日历 |
| namechange | 20200101 | 股票曾用名 |
| stk_managers | 20200101 | 上市公司管理层 |
| new_share | 20200101 | IPO 新股 |
| bak_basic | 20200101 | 股票历史列表 |

### st_risk_board 智能筛选

`st_risk_board` 不再遍历全部 5512 个 ts_code，而是先从 `stock_st` 表获取出现过 ST 的代码（约 750 个），仅对这些代码逐一调用 API。回退逻辑：若 `stock_st` 表为空，则回退到 `stock_basic` 全量驱动。

---

## 四、速率限制

所有按日期循环的接口共享一个全局 `RateLimiter(300次/分钟)`，确保 Tushare API 不超限。

`stock_hsgt` 使用独立 `RateLimiter(180次/分钟)`（API 限制 200次/分钟，留有余量），避免与其他接口共享限速器时超限。

`st_risk_board` 使用独立速率限制器（300次/分钟），单线程逐批执行（~750 个代码，约 2.5 分钟完成）。

---

## 五、特殊说明

### 5.1 stk_premarket — TDengine 超级表

该接口写入 TDengine 的 `qmt_ai.stk_premarket` 超级表，按 `ts_code` 为 tag 分表。子表名格式：`stk_premarket_{ts_code}`（`.` 替换为 `_`）。

### 5.2 bak_basic — 需 5000 积分

该接口需要 Tushare **5000 积分**权限。当前已开通，增量同步正常（2026-05-11 起有数据）。

### 5.3 new_share — Tushare API 限制

`new_share` 接口有 **100次/分钟** 的限制，增量时注意不要超越。

### 5.4 日期字段补全

Tushare 部分日期字段返回 `2015`（4位年份）或 `201506`（6位年月），`sync_utils.safe_db_value()` 自动补全为 `YYYYMMDD` 格式（`20150101` / `20150601`）。

### 5.5 API 数据截断问题

三个接口因 API 单次返回行数限制，缩小了日期区间防止截断：

| 接口 | API限制 | 原区间 | 现区间 | 说明 |
|------|--------|--------|--------|------|
| stock_st | 1000行/次 | 半月 | **10天** | 高峰期单月超 2000 行，半月区间约 1100 行→截断 |
| stock_hsgt | 2000行/次 | 半月 | **逐日** | 单 type 单日约 1730 行 < 2000，7天批次约 12000→严重截断 |
| stk_premarket | 8000行/次 | 半月 | **逐交易日** | 单天约 5500 行 < 8000，半月约 82,500→严重截断 |

> ⚠️ `stk_premarket` 写入 TDengine，永不清表。REST API 插入性能随数据量增长而降级，全量同步耗时较长（~90分钟/1535天），增量更新效率正常。

---

## 六、依赖模块

```
src/utils/sync_utils.py          # 通用工具（RateLimiter, insert_dataframe, safe_db_value 等）
src/data_sync/full_sync/stock_data/
├── sync_basic_data_all.py       # 5 个与日期无关的接口
└── sync_basic_data_bydate.py    # 8 个按日期循环的接口
scripts/
├── sync_basic_data_all.sh       # all 全量 shell 脚本
├── sync_basic_data_bydate.sh    # bydate shell 脚本（支持日期参数）
└── sync_fix_data.sh             # 问题数据修复脚本（支持全量/增量）
```

---

## 七、Tushare 积分权限要求

| 接口 | 积分要求 | 备注 |
|------|---------|------|
| stock_basic | 2,000 | 每分钟 50 次 |
| trade_cal | 2,000 | — |
| stock_st | 3,000 | — |
| stock_hsgt | 3,000 | 200次/分钟 |
| st | 6,000 | st_risk_board |
| stk_managers | 2,000 | — |
| stk_rewards | 2,000 | — |
| bak_basic | 5,000 | 已开通 |
| stock_company | 120 | — |
| bse_mapping | 120 | — |
| new_share | 120 | 100次/分钟 |
| stk_premarket | 在线开通 | — |
| namechange | — | 基础权限 |

---

## 八、数据质量探查报告（2026-05-15）

### 8.1 修复状态总览

| 表名 | 问题 | 状态 | 修复方式 |
|------|------|------|---------|
| stock_basic | 7 字段 100% NULL | ✅ 已修复 | `fetch_stock_basic()` 显式传入 fields 参数 |
| trade_cal | SSE/SZSE 仅 5 行，期货交易所残留 | ✅ 已修复 | 全量清表重跑，SSE/SZSE 各 7,805 行，0 重复 |
| stock_hsgt | 7天批次 API 截断 | ✅ 已修复 | 改为 `interval_days=1` 逐日查询 + 独立 180/min 限速 |
| stk_rewards | 54.6% 全行重复 | ✅ 代码已修复 | 已加 `df.drop_duplicates()`，下次全量重跑生效 |
| namechange | 54.5% 全行重复 | ✅ 代码已修复 | 已加 `df.drop_duplicates()`，下次全量重跑生效 |

### 8.2 仍存在的已知问题

| # | 表名 | 问题 | 详情 |
|---|------|------|------|
| 1 | **stk_premarket** | 5 天数据异常偏低 | 2024-05-10(21行)、05-17(22行)、05-23(17行)、07-15(33行)、09-24(20行)，正常日均 5,345 行 |
| 2 | **stk_managers** | `resume` 字段 100% NULL | Tushare API 中该字段标记为非默认显示(N)，未显式请求 |
| 3 | **stk_rewards** | `reward` 字段 15.9% NULL | Tushare 半年报公告时薪酬数据本身缺失，属于数据源特性 |

### 8.3 正常项确认

| 检查维度 | 结论 |
|---------|------|
| 日期格式 | 全部 13 张表日期格式正常 ✓ |
| stk_premarket 连续性 | 0 缺失交易日 ✓ |
| trade_cal 准确性 | SSE 5,186 / SZSE 5,186 交易日，2005~2026，0 重复 ✓ |
| stock_hsgt 截断 | 单日单 type 最高 1,731 < 2,000，0 截断 0 重复 ✓ |
| stock_basic NULL | 仅 `delist_date` 100% NULL（仅同步上市股票，正常）✓ |
| bak_basic | 5 天数据，每日 5,522~5,523 行 ✓ |
| stock_basic/stock_company/st_risk_board/bse_mapping/new_share | 0 重复 ✓ |

### 8.4 各接口 API 单次返回行数限制

| 接口 | API 上限 | 同步批次 | 当前最大单批行数 | 触顶 |
|------|---------|---------|----------------|------|
| stock_basic | 6,000 | 全量 | 5,517 | 否 |
| stock_company | 4,500 | 按交易所 | ~2,300 | 否 |
| st (st_risk_board) | 1,000/ts_code | 逐代码 | — | 否 |
| stk_rewards | 无明确限制 | 50个/批 | — | 否 |
| bse_mapping | 1,000 | 全量 | 248 | 否 |
| trade_cal | 无明确限制 | 半月 | — | 否 |
| stock_st | 1,000 | 10天 | 532 | 否 |
| stock_hsgt | 2,000 | **逐日** | 1,731 | 否 ✓ |
| stk_premarket | 8,000 | 逐交易日 | 5,499 | 否 |
| namechange | 无明确限制 | 半月 | — | 否 |
| stk_managers | 无明确限制 | 半月 | — | 否 |
| new_share | 2,000 | 半月 | — | 否 |
| bak_basic | 7,000 | 逐交易日 | 5,523 | 否 |
