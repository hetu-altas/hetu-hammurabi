# 港股数据同步指南

> 更新日期：2026-05-18 | 同步模块：`src/data_sync/full_sync/stock_data/sync_hkstock_data_bydate.py`

---

## 一、接口总览（9 个）

### TDengine 入库（3 个）

| 接口 | 中文名称 | 表名 | 同步策略 | 数据量 | 子表数 | 最早日期 | 最晚日期 |
|------|---------|------|---------|--------|--------|---------|---------|
| hk_daily | 港股日线行情 | hk_daily | 按 ts_code × 1年窗口循环（5000条/次） | **2,999,748** | 2,729 | 2020-01-02 | 2026-05-08 |
| hk_daily_adj | 港股复权行情 | hk_daily_adj | 按 ts_code × 1年窗口循环（6000条/次） | **3,732,338** | 2,730 | 2020-01-02 | 2026-05-08 |
| hk_adjfactor | 港股复权因子 | hk_adjfactor | 按 ts_code × 1年窗口循环（6000条/次） | **3,677,438** | 2,695 | 2020-01-02 | 2026-05-08 |

### GreatSQL 入库（6 个）

| 接口 | 中文名称 | 表名 | 同步策略 | 数据量 | 最早日期 | 最晚日期 |
|------|---------|------|---------|--------|---------|---------|
| hk_basic | 港股基础信息 | hk_basic | 全量拉取，清表重建 | **2,739** | — | — |
| hk_tradecal | 港股交易日历 | hk_tradecal | 按3年区间循环（2000条/次） | **2,459** | 2020-01-01 | 2026-05-15 |
| hk_income | 港股利润表 | hk_income | 按 ts_code 循环（10000条/次） | **879,796** | 2020-01-31 | 2025-12-31 |
| hk_balancesheet | 港股资产负债表 | hk_balancesheet | 按 ts_code 循环（10000条/次） | **1,298,030** | 2020-01-31 | 2026-03-31 |
| hk_cashflow | 港股现金流量表 | hk_cashflow | 按 ts_code 循环（10000条/次） | **910,908** | 2020-01-31 | 2025-12-31 |
| hk_fina_indicator | 港股财务指标数据 | hk_fina_indicator | 按 ts_code × 3年窗口循环（200条/次） | **37,374** | 2020-01-31 | 2026-03-31 |

> **总计**：TDengine **10,409,524 行** + GreatSQL **3,131,160 行** = **13,540,684 行**
>
> **说明**：
> - hk_basic 覆盖 2,730 只港股（主板 2,422 + 创业板 308），全部为上市状态（L）
> - hk_daily_adj 缺失 1 只股票的子表（hk_daily 仅 2,729 个子表）
> - hk_adjfactor 约 2,695 个子表，部分股票可能无复权因子数据
> - 财务数据（income/balancesheet/cashflow）为长格式存储（每个指标一行）

---

## 二、执行方式

### 2.1 Shell 脚本

```bash
# 基础数据全量（仅初次部署/数据重建，与日期无关）
# 说明：清理 hk_basic 表数据 + 重新全量拉取
bash scripts/sync_hkstock_data_all.sh

# 全量同步（按日期区间，8 个接口）
bash scripts/sync_hkstock_data.sh                            # 全量 (2005-01-01 至今)

# 增量同步
bash scripts/sync_hkstock_data.sh 20260501                   # 从指定日期至今
bash scripts/sync_hkstock_data.sh 20260501 20260512          # 指定日期范围

# 仅 TDengine 三张行情表
bash scripts/sync_hkstock_td.sh                              # 全量
bash scripts/sync_hkstock_td.sh 20260501 20260512            # 增量

# 单表单独同步
bash scripts/sync_hk_daily_adj.sh 20200101                   # 仅 hk_daily_adj
bash scripts/sync_hk_adjfactor.sh 20200101                   # 仅 hk_adjfactor
```

### 2.2 Python 直接调用

```python
from sync_hkstock_data_bydate import (
    sync_hk_basic, sync_hk_tradecal,
    sync_hk_daily, sync_hk_daily_adj, sync_hk_adjfactor,
    sync_hk_income, sync_hk_balancesheet, sync_hk_cashflow,
    sync_hk_fina_indicator,
)

# GreatSQL 基础数据（全量拉取，不传参）
sync_hk_basic()

# GreatSQL 财务数据（全量）
sync_hk_income()
sync_hk_balancesheet()
sync_hk_cashflow()
sync_hk_fina_indicator()

# TDengine 历史行情（全量）
sync_hk_daily()
sync_hk_daily_adj()
sync_hk_adjfactor()

# TDengine 增量（传日期参数）
sync_hk_daily(start_date="20260512", end_date="20260513")
sync_hk_daily_adj(start_date="20260512", end_date="20260513")
```

> **全量 vs 增量**：
> - **不传参数** → 使用默认起始日期（2005-01-01）全量拉取
> - **传 start_date/end_date** → 不删已有数据，仅追加新数据
> - **TDengine 自动去重**：同子表+时间戳唯一，重复 INSERT 自动跳过
> - **hk_basic** → 全量拉取覆盖写入（先清表后插入）

---

## 三、各接口起始日期与限制

| 接口 | 默认起始日期 | Tushare 限制 | 分块策略 |
|------|-------------|------------|---------|
| hk_basic | — | 单次提取全部，需2000积分 | 不分块，一次拉取 |
| hk_tradecal | 2005-01-01 | **2000条/次** | 按3年窗口分批 |
| hk_daily | 2005-01-01 | **5000条/次**，需单独开权限 | 按 ts_code × 1年窗口循环 |
| hk_daily_adj | 2005-01-01 | **6000条/次**，需单独开权限 | 按 ts_code × 1年窗口循环 |
| hk_adjfactor | 2005-01-01 | **6000条/次**，需单独开权限 | 按 ts_code × 1年窗口循环 |
| hk_income | 2005-01-01 | **10000条/次**，需15000积分或单独开权限 | 按 ts_code 循环 (20年×~30指标×4季≈2400行，不超限) |
| hk_balancesheet | 2005-01-01 | **10000条/次**，需15000积分或单独开权限 | 按 ts_code 循环 |
| hk_cashflow | 2005-01-01 | **10000条/次**，需15000积分或单独开权限 | 按 ts_code 循环 |
| hk_fina_indicator | 2005-01-01 | **200条/次**，需15000积分或单独开权限 | 按 ts_code × 3年窗口循环 |

---

## 四、速率限制

所有接口共享全局 `RateLimiter(300次/分钟)`，确保 Tushare API 不超限。

| 接口 | API 单次限制 | 预估调用量（全量） | 预估耗时 |
|------|------------|-------------------|---------|
| hk_basic | 单次全部 | 1次 | ~1秒 |
| hk_tradecal | 2000条/次 | ~7次（20年 ÷ 3年窗口） | ~2秒 |
| hk_daily | 5000条/次 | ~54,600次（2730股 × 20年窗口） | ~3小时 |
| hk_daily_adj | 6000条/次 | ~54,600次 | ~3小时 |
| hk_adjfactor | 6000条/次 | ~54,600次 | ~3小时 |
| hk_income | 10000条/次 | ~2,730次 | ~9分钟 |
| hk_balancesheet | 10000条/次 | ~2,730次 | ~9分钟 |
| hk_cashflow | 10000条/次 | ~2,730次 | ~9分钟 |
| hk_fina_indicator | 200条/次 | ~21,840次（2730股 × 8个3年窗口） | ~73分钟 |

---

## 五、TDengine 插入机制

### 5.1 子表+时间戳唯一

TDengine 超级表中，同一子表的相同时间戳 INSERT 会自动去重，**不会产生重复行**。增量更新无需先删后插。

### 5.2 批量插入优化

```python
# td_utils.insert_dataframe_to_td()
# 每个 ts_code 生成一条 INSERT ... USING ... TAGS (...) VALUES (...)
# 每批最多 500 行
# 格式: INSERT INTO qmt_ai.hd_00001_hk USING qmt_ai.hk_daily TAGS ('00001.HK') VALUES (...)
```

### 5.3 子表命名规则

| 超级表 | 前缀 | 示例 |
|--------|------|------|
| hk_daily | hd_ | hd_00001_hk, hd_00700_hk |
| hk_daily_adj | ha_ | ha_00001_hk, ha_00700_hk |
| hk_adjfactor | hf_ | hf_00001_hk, hf_00700_hk |

> **特殊字符处理**：港股代码中的 `.` 替换为 `_`

### 5.4 时间字段映射

| 接口 | API 字段 | TDengine ts | 格式处理 |
|------|---------|-------------|---------|
| hk_daily | trade_date | ts | YYYYMMDD → YYYY-MM-DD 00:00:00 |
| hk_daily_adj | trade_date | ts | YYYYMMDD → YYYY-MM-DD 00:00:00 |
| hk_adjfactor | trade_date | ts | YYYYMMDD → YYYY-MM-DD 00:00:00 |

> **注意**：API 输出的日期格式为 YYYY-MM-DD，入库时转换为 TDengine 时间戳格式

---

## 六、字段映射说明

### 6.1 hk_daily 字段映射

| API 字段 | TDengine 字段 | 类型 | 说明 |
|---------|-------------|------|------|
| trade_date | ts | TIMESTAMP | 交易日期 |
| open | open | DOUBLE | 开盘价 |
| high | high | DOUBLE | 最高价 |
| low | low | DOUBLE | 最低价 |
| close | close | DOUBLE | 收盘价 |
| pre_close | pre_close | DOUBLE | 昨收价 |
| change | change | DOUBLE | 涨跌额 |
| pct_chg | pct_chg | DOUBLE | 涨跌幅(%) |
| vol | vol | BIGINT | 成交量(股) |
| amount | amount | DOUBLE | 成交额(元) |

### 6.2 hk_daily_adj 字段映射（含列名重映射）

API 返回列名与 STABLE 列名不一致，`_TD_FIELD_MAP` 已配置映射：

| API 字段 | TDengine 字段 | 类型 | 说明 |
|---------|-------------|------|------|
| trade_date | ts | TIMESTAMP | 交易日期 |
| open | open | DOUBLE | 开盘价 |
| high | high | DOUBLE | 最高价 |
| low | low | DOUBLE | 最低价 |
| close | close | DOUBLE | 收盘价 |
| pre_close | pre_close | DOUBLE | 昨收价 |
| change | change | DOUBLE | 涨跌额 |
| **pct_change** | **pct_chg** | DOUBLE | 涨跌幅(%) |
| vol | vol | BIGINT | 成交量(股) |
| amount | amount | DOUBLE | 成交额(元) |
| vwap | vwap | DOUBLE | 平均价 |
| adj_factor | adj_factor | DOUBLE | 复权因子 |
| **turnover_ratio** | **turnover_rate** | DOUBLE | 换手率(%) |
| total_share | total_share | DOUBLE | 总股本(股) |
| **free_share** | **float_share** | DOUBLE | 流通股本(股) |
| total_mv | total_mv | DOUBLE | 总市值(元) |
| **free_mv** | **float_mv** | DOUBLE | 流通市值(元) |

> **注意**：`pct_change`/`turnover_ratio`/`free_share`/`free_mv` 四个字段的 API 列名与 DDL 列名不一致，已在 `td_utils._TD_FIELD_MAP` 中配置自动重映射

### 6.3 hk_adjfactor 字段映射

| API 字段 | TDengine 字段 | 类型 | 说明 |
|---------|-------------|------|------|
| trade_date | ts | TIMESTAMP | 交易日期 |
| cum_adjfactor | cum_adjfactor | DOUBLE | 累计复权因子 |
| close_price | close_price | DOUBLE | 收盘价 |

### 6.4 hk_income / hk_balancesheet / hk_cashflow 字段映射

三个财务接口 API 返回相同长格式结构：

| API 字段 | GreatSQL 字段 | 类型 | 说明 |
|---------|-------------|------|------|
| ts_code | ts_code | VARCHAR(20) | 股票代码 |
| end_date | end_date | DATE | 报告期 |
| name | name | VARCHAR(200) | 股票名称 |
| ind_name | ind_name | VARCHAR(500) | 财务科目名称 |
| ind_value | ind_value | DECIMAL(36,4) | 财务科目值 |

> **注意**：HK 财务接口返回长格式（每行一个指标），与 A 股财务接口的宽格式不同。`ind_value` 覆盖范围可达 6.5e11（腾讯2024营业额），故使用 DECIMAL(36,4)

### 6.5 hk_fina_indicator 字段映射（宽格式）

hk_fina_indicator 返回宽格式（每行一个报告期，80+ 个指标列），直接映射到 GreatSQL 同名字段：

| 类别 | 列数 | 示例字段 |
|------|------|---------|
| 基础信息 | 6 | ts_code, name, end_date, ind_type, report_type, std_report_date |
| 盈利能力 | 16 | basic_eps, diluted_eps, operate_income, gross_profit, holder_profit, roe_avg, roa 等 |
| 现金流 | 4 | netcash_operate, netcash_invest, netcash_finance, end_cash |
| 资产负债 | 8 | total_assets, total_liabilities, total_parent_equity, debt_asset_ratio 等 |
| 估值指标 | 9 | total_market_cap, hksk_market_cap, pe_ttm, pb_ttm, pe_ttm_sq, pb_ttm_sq 等 |
| 行业特色 | 17 | premium_income, net_interest_income, fee_commission_income, loan_deposit 等 |
| 营运效率 | 4 | accounts_rece_tdays, inventory_tdays, current_assets_tdays, total_assets_tdays |
| 季报数据 | 12 | report_date_sq, operate_income_sq, holder_profit_sq, roe_avg_sq 等 |
| 股息 | 4 | dps_hkd, dps_hkd_ly, divi_ratio, dividend_rate |
| 其他 | 8 | currency, is_cny_code, org_type, fiscal_year, equity_multiplier, equity_ratio 等 |

---

## 七、特殊说明

### 7.1 hk_basic — 不支持日期参数

`sync_hk_basic` 全量拉取所有港股基础信息，**不支持 start_date/end_date 参数**。hk_basic 作为基础查表，需包含所有港股代码，其后再按日期参数同步各股票的历史行情。

### 7.2 数据依赖链

```
hk_basic（基础代码） → hk_daily / hk_daily_adj / hk_adjfactor / hk_income / ...
                      ↑ 各接口依赖 hk_basic 获取 ts_code 列表
```

- 若 hk_basic 表无数据，其他 sync 函数返回 0（无法获取股票代码）
- **部署顺序**：先执行 `sync_hkstock_data_all.sh`，再执行 `sync_hkstock_data.sh`

### 7.3 hk_daily_adj 列名重映射

hk_daily_adj API 返回的列名与 STABLE 列名存在差异，已在 `td_utils.py` 中配置：

| API | STABLE | 原因 |
|-----|--------|------|
| pct_change | pct_chg | 统一 A 股命名风格 |
| turnover_ratio | turnover_rate | 统一 A 股命名风格 |
| free_share | float_share | 统一 A 股命名风格 |
| free_mv | float_mv | 统一 A 股命名风格 |

### 7.4 HK 财务接口按 ts_code 循环

HK 财务接口（income/balancesheet/cashflow/fina_indicator）**ts_code 为必传参数**，不支持仅按日期查询。同步策略为遍历 hk_basic 中所有港股代码，对每只股票按日期区间拉取历史财务数据。

### 7.5 hk_fina_indicator 200条/次限制

hk_fina_indicator 接口限制极严（200条/次），采用 **3年窗口** 分块策略：
- 2005-2007、2008-2010、2011-2013、...、2026-
- 每只股票约8个窗口 × 2730只股票 ≈ 21,840次调用
- 预计耗时约73分钟（全量）

### 7.6 日期格式注意事项

- **API 入参**：YYYYMMDD 格式（如 `20200101`）
- **API 输出**：YYYY-MM-DD 格式（如 `2020-01-01`）
- **TDengine ts**：YYYY-MM-DD HH:MM:SS 格式（如 `2020-01-01 00:00:00`）
- 代码中 `td_utils.py` 自动处理格式转换

---

## 八、依赖模块

```
src/utils/sync_utils.py                          # GreatSQL 工具（RateLimiter, insert_dataframe 等）
src/utils/td_utils.py                            # TDengine 批量插入工具（insert_dataframe_to_td）
src/fetch_tushare_data/hk_stock/                 # 9 个 fetch 接口实现
├── fetch_hk_basic.py                             # 港股基础信息
├── fetch_hk_tradecal.py                          # 港股交易日历
├── fetch_hk_daily.py                             # 港股日线行情
├── fetch_hk_daily_adj.py                         # 港股复权行情
├── fetch_hk_adjfactor.py                         # 港股复权因子
├── fetch_hk_income.py                            # 港股利润表
├── fetch_hk_balancesheet.py                      # 港股资产负债表
├── fetch_hk_cashflow.py                          # 港股现金流量表
└── fetch_hk_fina_indicator.py                    # 港股财务指标数据
src/data_sync/full_sync/stock_data/
└── sync_hkstock_data_bydate.py                   # 9 个港股接口同步脚本
scripts/
├── sync_hkstock_data_all.sh                      # 基础数据全量同步
├── sync_hkstock_data.sh                          # 按日期同步（8 个接口）
├── sync_hkstock_td.sh                            # TDengine 行情表同步
├── sync_hk_daily_adj.sh                          # 仅 hk_daily_adj
└── sync_hk_adjfactor.sh                          # 仅 hk_adjfactor
src/batch/sql/
├── tdengine/港股数据.sql                          # hk_daily / hk_daily_adj / hk_adjfactor DDL
└── greatsql/港股数据.sql                          # 6 个 GreatSQL 表 DDL
unit_test/
└── test_sync_hkstock_data.py                     # 单元测试（33 个用例）
```

---

## 九、Tushare 积分权限要求

| 接口 | 积分要求 | 备注 |
|------|---------|------|
| hk_basic | 2,000 | 单次可提取全部，约2,730只港股 |
| hk_tradecal | 2,000 | 2000条/次 |
| hk_daily | 需单独开权限 | 5000条/次 |
| hk_daily_adj | 需单独开权限（120积分可试用） | 6000条/次 |
| hk_adjfactor | 自动随 hk_daily 开通 | 6000条/次 |
| hk_income | 15,000 或单独开权限 | 10000条/次 |
| hk_balancesheet | 15,000 或单独开权限 | 10000条/次 |
| hk_cashflow | 15,000 或单独开权限 | 10000条/次 |
| hk_fina_indicator | 15,000 或单独开权限 | 200条/次 |

---

## 十、数据库分类原则

| 数据库 | 适用场景 | 港股数据中的体现 |
|--------|---------|----------------|
| **TDengine** | 时序数据、按时间轴查询、高频更新的行情 | hk_daily（日线）、hk_daily_adj（复权日线）、hk_adjfactor（复权因子） |
| **GreatSQL** | 基础信息、财务数据、参考数据 | hk_basic（代码/名称）、hk_tradecal（交易日历）、hk_income/balancesheet/cashflow/fina_indicator（财务数据） |

---

## 十一、数据量详细统计

### 11.1 TDengine 行情数据 TOP 5（按子表数据量）

| 子表 | 对应股票 | hk_daily | hk_daily_adj | hk_adjfactor |
|------|---------|----------|-------------|-------------|
| hd_06881_hk | 06881.HK | 1,560 | 1,559 | — |
| hd_00874_hk | 00874.HK | 1,560 | 1,558 | — |
| ha_00261_hk | 00261.HK | 1,554 | 1,561 | — |
| ha_08293_hk | 08293.HK | 1,550 | 1,561 | — |
| hf_00486_hk | 00486.HK | — | — | 1,561 |

> 单只股票约 1,560 条日线数据（约6.7年交易日），日线数据量最多的股票覆盖了更多历史

### 11.2 GreatSQL 财务数据概况

| 表 | 行数 | 特点 |
|------|------|------|
| hk_income | 879,796 | 每只股票约322行（~80个指标 × 4季度） |
| hk_balancesheet | 1,298,030 | 每只股票约475行（~118个指标 × 4季度） |
| hk_cashflow | 910,908 | 每只股票约334行（~83个指标 × 4季度） |
| hk_fina_indicator | 37,374 | 每只股票约14行（~80个指标宽格式，1行/季度） |

### 11.3 数据时间范围

| 类别 | 最早时间 | 最晚时间 | 跨度 |
|------|---------|---------|------|
| TDengine 行情 | 2020-01-02 00:00:00 | 2026-05-08 00:00:00 | 约6.3年 |
| GreatSQL 财务 | 2020-01-31 | 2026-03-31 | 约6.2年 |
| GreatSQL 交易日历 | 2020-01-01 | 2026-05-10 | 约6.3年 |
| GreatSQL 基础信息 | list_date: 1921-01-01 | 2026-04-17 | — |

> **说明**：行情和财务数据实际起始于2020年（Tushare平台数据起点），hk_basic 中的 list_date 包含更早上市日期

---

## 十二、数据示例

### 12.1 hk_basic 数据示例

```
ts_code      name         fullname              market    list_status  list_date   curr_type
00001.HK     长和          长江和记实业有限公司       主板      L            1978-01-01  HKD
00700.HK     腾讯控股       腾讯控股有限公司          主板      L            2004-06-16  HKD
00123.HK     YUEXIU PROP   越秀地产股份有限公司       主板      L            1992-12-15  HKD
08001.HK     ORIENT SEC    东方汇财证券             创业板    L            2014-01-15  HKD
```

### 12.2 hk_daily 数据示例

```
ts_code      trade_date    open    high    low     close   pre_close  change  pct_chg  vol         amount
00700.HK     20260508      488.0   495.0   486.0   493.8   485.0      8.8     1.8144   18500000.0  9.05e+09
00700.HK     20260507      482.0   488.0   480.0   485.0   490.0      -5.0    -1.0204  15200000.0  7.38e+09
```

### 12.3 hk_income 数据示例（长格式）

```
ts_code      end_date    name      ind_name    ind_value
00700.HK     20241231    腾讯控股    营业额      6.524980e+11
00700.HK     20241231    腾讯控股    毛利        3.492460e+11
00700.HK     20241231    腾讯控股    经营溢利    2.080990e+11
00700.HK     20241231    腾讯控股    股东应占溢利 1.940730e+11
```

### 12.4 hk_fina_indicator 数据示例（宽格式）

```
ts_code   name    end_date    basic_eps  operate_income    roe_avg  pe_ttm  pb_ttm  total_assets
00700.HK  腾讯控股  20241231    20.94      6.524980e+11     19.33    21.5    4.1     1.780995e+12
00700.HK  腾讯控股  20240630    9.46       3.206380e+11     9.52     23.8    4.5     1.654319e+12
```

---

## 十三、常见问题

### Q1: 为什么 hk_daily_adj 同步报 "Illegal number of columns"？

hk_daily_adj STABLE 的列数必须与 `td_utils._TD_COLUMNS_MAP` 完全一致（17列）。若 STABLE 是旧版DDL创建的（15列），需 DROP 后重建：
```sql
DROP STABLE IF EXISTS qmt_ai.hk_daily_adj;
-- 然后用 src/batch/sql/tdengine/港股数据.sql 中的最新 DDL 重建
```

### Q2: TDengine 表查询语句应该怎么写？

查询用 `td.query()`（非 `td.execute()`）：
```python
td = get_tdengine('conf/taos_conf.json')
# 正确：查询用 query()
cnt = td.query('SELECT COUNT(*) FROM qmt_ai.hk_daily')
rng = td.query('SELECT FIRST(ts), LAST(ts) FROM qmt_ai.hk_daily')
# 错误：execute() 对查询返回 None
```

### Q3: 为什么某些港股没有复权因子数据？

hk_adjfactor 约 2,695 个子表（少于 hk_basic 的 2,730），说明部分股票（约35只）Tushare 未提供复权因子数据。

### Q4: 同步返回 0 行怎么办？

检查以下几点：
1. Tushare 积分是否达到对应接口门槛
2. hk_basic 表是否有数据（先执行 `sync_hkstock_data_all.sh`）
3. 日期范围是否有效（非交易日返回0行）
4. 部分接口（hk_income 等）需单独开通权限

### Q5: 子表名包含特殊字符怎么办？

`insert_dataframe_to_td` 已自动处理：`.` → `_`（如 00001.HK → hd_00001_hk）

### Q6: 为什么 hk_income 和 hk_cashflow 数据止于2025-12-31？

部分财务接口的最新数据可能滞后于行情数据。hk_balancesheet 和 hk_fina_indicator 已更新至2026-03-31，hk_income 和 hk_cashflow 的最新一期年报尚未发布。

---

## 十四、更新记录

| 日期 | 更新内容 |
|------|---------|
| 2026-05-13 | 初版：完成 9 个港股接口同步模块开发、DDL 建表（修正）、td_utils 字段映射注册、单元测试（33用例）、Shell 脚本 |
| 2026-05-18 | 数据探查：确认 TDengine 三表健康、金融表有少量重复、hk_daily_adj ~20% NULL |


## 十五、数据质量（2026-05-18 探查）

### 数据概况

| 表 | 行数 | 子表数 | 时间范围 |
|----|------|--------|---------|
| hk_basic | 2,739 | — | — |
| hk_tradecal | 2,459 | — | 2020-01-01 ~ 2026-05-15 |
| hk_income | 879,796 | — | — |
| hk_balancesheet | 1,298,030 | — | — |
| hk_cashflow | 910,908 | — | — |
| hk_fina_indicator | 37,374 | — | — |
| hk_daily | 2,999,748 | 2,729 | 2020 ~ 2026, 按年均匀 |
| hk_daily_adj | 3,732,338 | 2,730 | 2020 ~ 2026, 按年增长 |
| hk_adjfactor | 3,677,438 | 2,695 | 2020 ~ 2026, 按年增长 |

### 总体结论

| 检查项 | 结果 |
|--------|------|
| 数据连续性 | ✓ TDengine 三表 2020~2026 连续，2700+ 子表 |
| API 截断 | ✓ 1 年窗口 + 单股~260 行/年，远小于 5000/6000 上限 |
| 数据重复 | ⚠ hk_income 221组 / balancesheet 23组 / cashflow 73组 / fina_indicator 4组 |
| 字段 NULL | hk_daily_adj OHLC ~20% NULL（正常业务）；fina_indicator 行业字段 60-99% NULL |
| 日期格式 | ✓ 统一正确 |
| 同一日期 | ✓ 无异常 |

### 需修复

| 表 | 问题 | 方案 |
|----|------|------|
| hk_income | 221 组 (ts_code,end_date,ind_name) 重复，221 条多余行 | 去重 + UNIQUE KEY |
| hk_balancesheet | 23 组重复，23 条多余行 | 同上 |
| hk_cashflow | 73 组重复，73 条多余行 | 同上 |
| hk_fina_indicator | 4 组 (ts_code,end_date) 重复 | 同上 |

### 正常业务 NULL

| 表 | 字段 | NULL率 | 说明 |
|----|------|--------|------|
| hk_daily_adj | open/high/low/vol/amount | ~20% | 部分股票无复权行情数据，均匀分布各日期 |
| hk_fina_indicator | premium_income/loan_* 等 | 95-99% | 行业特色字段（保险/银行），非该行业不返回 |
| hk_fina_indicator | dps_hkd/divi_ratio 等 | 61-62% | 仅部分公司有股息数据 |
| hk_basic | delist_date | 100% | 所有股票仍在上市中 |
