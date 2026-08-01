# 美股数据同步指南

> 更新日期：2026-05-18 | 同步模块：`src/data_sync/full_sync/sync_usstock_data_bydate.py`

---

## 一、接口总览（9 个）

### TDengine 入库（3 个）

| 接口 | 中文名称 | 表名 | 同步策略 | ts 映射 | 数据量 | 最早日期 | 最晚日期 |
|------|---------|------|---------|---------|--------|---------|---------|
| us_daily | 美股日线行情 | us_daily | 按 ts_code 循环（50只/批） | trade_date → ts | 17,101,699 | 2020-01-02 | 2026-05-08 |
| us_daily_adj | 美股复权行情 | us_daily_adj | 按 ts_code 循环（50只/批） | trade_date → ts | 15,022,705 | 2020-01-02 | 2026-05-08 |
| us_adjfactor | 美股复权因子 | us_adjfactor | 按半月区间循环 | trade_date → ts | 2,277,344 | 2020-01-14 | 2026-05-08 |

### GreatSQL 入库（6 个）

| 接口 | 中文名称 | 表名 | 同步策略 | 数据量 | 最早日期 | 最晚日期 | 股票数 |
|------|---------|------|---------|--------|---------|---------|--------|
| us_basic | 美股基础信息 | us_basic | 全量分页拉取（5000/页） | 23,455 | 1925-12-31 | 2025-09-18 | 23,357 |
| us_tradecal | 美股交易日历 | us_tradecal | 按日期区间一次拉取 | 2,331 | 2020-01-01 | 2026-05-17 | — |
| us_income | 美股利润表 | us_income | 按 ts_code 循环（50只/批） | 3,192,245 | 2020-01-03 | 2026-04-05 | 5,524 |
| us_balancesheet | 美股资产负债表 | us_balancesheet | 按 ts_code 循环（50只/批） | 3,511,100 | 2020-01-03 | 2026-04-05 | 5,562 |
| us_cashflow | 美股现金流量表 | us_cashflow | 按 ts_code 循环（50只/批） | 2,949,512 | 2020-01-03 | 2026-04-05 | 5,549 |
| us_fina_indicator | 美股财务指标 | us_fina_indicator | 按 ts_code×2年窗口循环 | 118,956 | 2020-01-03 | 2026-04-05 | 5,536 |

> **总计**：TDengine 34,401,748 行 + GreatSQL 9,804,497 行 = **44,206,245 行**
>
> **说明**：
> - us_basic 包含 EQ（21,316）/ ADR（2,057）/ GDR（82）三类
> - 交易日历中交易日 1,599 天，休市日 723 天
> - 美股行情起始于 2020 年（Tushare 美股数据覆盖起点）

---

## 二、执行方式

### 2.1 Shell 脚本

```bash
# 基础数据全量（仅初次部署/数据重建，含全量清理）
# 说明：清理 us_basic 表 + 重新全量拉取
bash scripts/sync_usstock_data_all.sh

# 历史数据按日期同步（日常增量，含全部 8 个日期相关接口）
bash scripts/sync_usstock_data.sh                              # 全量 (2005-01-01 至今)
bash scripts/sync_usstock_data.sh 20260401                     # 从指定日期至今
bash scripts/sync_usstock_data.sh 20260401 20260430            # 指定日期范围
bash scripts/sync_usstock_data.sh 20260506 20260507            # 增量
```

### 2.2 Python 直接调用

```python
from sync_usstock_data_bydate import (
    # TDengine
    sync_us_daily, sync_us_daily_adj, sync_us_adjfactor,
    # GreatSQL
    sync_us_basic, sync_us_tradecal, sync_us_income,
    sync_us_balancesheet, sync_us_cashflow, sync_us_fina_indicator,
)

# 基础数据全量（不传参）
sync_us_basic()

# 日期接口全量同步（不传参使用默认起始日期 2005-01-01）
sync_us_tradecal()
sync_us_daily()
sync_us_daily_adj()
sync_us_adjfactor()
sync_us_income()
sync_us_balancesheet()
sync_us_cashflow()
sync_us_fina_indicator()

# 增量同步（传日期参数）
sync_us_daily(start_date="20260506", end_date="20260507")
sync_us_fina_indicator(start_date="20260501", end_date="20260507")
```

> **注意事项**：
> - `sync_us_basic` 必须先于其他接口执行（其他接口依赖 us_basic 表获取股票代码列表）
> - **不传参数** → 使用默认起始日期（2005-01-01）全量拉取
> - **传 start_date/end_date** → 不删已有数据，仅追加新数据
> - **TDengine 自动去重**：同子表+时间戳唯一，重复 INSERT 自动跳过

---

## 三、各接口起始日期与限制

| 接口 | 默认起始日期 | Tushare限制 | chunk策略 | 说明 |
|------|-------------|------------|----------|------|
| us_basic | — | 6000条/次，可分页 | 5000/页分页拉取 | 当前约 23k 只美股，5页完成 |
| us_tradecal | 2005-01-01 | 6000条/次 | 全量一次 | 4.5年×365天=1642天，约2322条交易日历 |
| us_daily | 2005-01-01 | 6000条/次 | ts_code 循环 | 单只约1300天，远低于上限 |
| us_daily_adj | 2005-01-01 | 8000条/次 | ts_code 循环 | 单只约1100天，远低于上限 |
| us_adjfactor | 2005-01-01 | 15000条/次 | 半月区间循环 | 单日约1.5万只股票，刚好不超上限 |
| us_income | 2005-01-01 | 10000条/次 | ts_code 循环 | 单只约600行，远低于上限 |
| us_balancesheet | 2005-01-01 | 10000条/次 | ts_code 循环 | 单只约630行，远低于上限 |
| us_cashflow | 2005-01-01 | 10000条/次 | ts_code 循环 | 单只约530行，远低于上限 |
| us_fina_indicator | 2005-01-01 | **200条/次** | ts_code×**2年**窗口 | 单只年约2-10条，2年窗口安全 |

---

## 四、速率限制

所有接口共享全局 `RateLimiter(300次/分钟)`。

| 接口 | API限制 | 实际调用量（全量） | 预估耗时 |
|------|--------|-------------------|---------|
| us_basic | 6000条/次 | 5 次（5页） | <5 秒 |
| us_tradecal | 6000条/次 | 1 次 | <1 秒 |
| us_daily | 6000条/次 | ~23,000 次（全量美股） | ~76 分钟 |
| us_daily_adj | 8000条/次 | ~23,000 次 | ~76 分钟 |
| us_adjfactor | 15000条/次 | ~217 次（半月区间） | ~1 分钟 |
| us_income | 10000条/次 | ~5,500 次 | ~18 分钟 |
| us_balancesheet | 10000条/次 | ~5,600 次 | ~19 分钟 |
| us_cashflow | 10000条/次 | ~5,500 次 | ~18 分钟 |
| us_fina_indicator | 200条/次 | ~39,000 次（5500×7区间） | **~130 分钟** |

---

## 五、TDengine 建表

### 5.1 超级表 DDL

**us_daily**（14列）：
```sql
CREATE STABLE us_daily (
  ts TIMESTAMP, open DOUBLE, high DOUBLE, low DOUBLE,
  close DOUBLE, pre_close DOUBLE, change DOUBLE, pct_chg DOUBLE,
  vol DOUBLE, amount DOUBLE, vwap DOUBLE, turnover_rate DOUBLE,
  pe DOUBLE, pb DOUBLE
) TAGS (ts_code NCHAR(20))
```

**us_daily_adj**（17列）：
```sql
CREATE STABLE us_daily_adj (
  ts TIMESTAMP, open DOUBLE, high DOUBLE, low DOUBLE,
  close DOUBLE, pre_close DOUBLE, change DOUBLE, pct_chg DOUBLE,
  vol DOUBLE, amount DOUBLE, vwap DOUBLE, adj_factor DOUBLE,
  turnover_rate DOUBLE, total_share DOUBLE, float_share DOUBLE,
  total_mv DOUBLE, float_mv DOUBLE
) TAGS (ts_code NCHAR(20))
```

**us_adjfactor**（3列）：
```sql
CREATE STABLE us_adjfactor (
  ts TIMESTAMP, cum_adjfactor DOUBLE, close_price DOUBLE
) TAGS (ts_code NCHAR(20))
```

### 5.2 字段映射（API → TDengine）

| API字段 | TDengine字段 | 说明 |
|---------|-------------|------|
| trade_date | ts | 交易日期 |
| pct_change | pct_chg | 涨跌幅（API用 pct_change，DDL用 pct_chg） |
| turnover_ratio | turnover_rate | 换手率 |
| free_share | float_share | 流通股本（仅 us_daily_adj） |
| free_mv | float_mv | 流通市值（仅 us_daily_adj） |

### 5.3 子表命名

| 超级表 | 前缀 | 示例 |
|--------|------|------|
| us_daily | ud_ | ud_AAPL |
| us_daily_adj | ua_ | ua_AAPL |
| us_adjfactor | uf_ | uf_AAPL |

---

## 六、GreatSQL 建表

### 6.1 基础信息表

**us_basic**（6列）：
```sql
CREATE TABLE us_basic (
  id INT AUTO_INCREMENT PRIMARY KEY,
  ts_code VARCHAR(20),     -- 股票代码
  name VARCHAR(100),       -- 中文名称
  enname VARCHAR(200),     -- 英文名称
  classify VARCHAR(10),    -- 分类 ADR/GDR/EQ
  list_date VARCHAR(20),   -- 上市日期
  delist_date VARCHAR(20), -- 退市日期
  KEY idx_ts_code (ts_code)
)
```

### 6.2 交易日历表

**us_tradecal**（3列）：
```sql
CREATE TABLE us_tradecal (
  id INT AUTO_INCREMENT PRIMARY KEY,
  cal_date DATE,           -- 日历日期
  is_open INT,             -- 是否交易 0休市 1交易
  pretrade_date DATE,      -- 上一个交易日
  KEY idx_cal_date (cal_date)
)
```

### 6.3 财务数据表（利润表/资产负债表/现金流量表）

**us_income / us_balancesheet / us_cashflow**（7列，结构相同）：
```sql
CREATE TABLE us_income (   -- / us_balancesheet / us_cashflow
  id INT AUTO_INCREMENT PRIMARY KEY,
  ts_code VARCHAR(20),     -- 股票代码
  end_date VARCHAR(20),    -- 报告期
  ind_type VARCHAR(20),    -- 报告类型 Q1/Q2/Q3/Q4
  name VARCHAR(100),       -- 股票名称
  ind_name VARCHAR(200),   -- 财务科目名称
  ind_value DOUBLE,        -- 财务科目值
  report_type VARCHAR(20), -- 报告类型
  KEY idx_ts_code (ts_code),
  KEY idx_end_date (end_date)
)
```

> **注意**：这三个表采用 ind_name / ind_value 键值对结构，与 Tushare API 返回格式一致。

### 6.4 财务指标表

**us_fina_indicator**（67列）：
```sql
CREATE TABLE us_fina_indicator (
  id INT AUTO_INCREMENT PRIMARY KEY,
  ts_code VARCHAR(20), end_date VARCHAR(20), ind_type VARCHAR(20),
  security_name_abbr VARCHAR(100), accounting_standards VARCHAR(50),
  notice_date VARCHAR(20), start_date VARCHAR(20), std_report_date VARCHAR(20),
  financial_date VARCHAR(20), currency VARCHAR(10), date_type VARCHAR(20),
  report_type VARCHAR(20),
  -- 盈利能力指标
  operate_income DOUBLE, operate_income_yoy DOUBLE,
  gross_profit DOUBLE, gross_profit_yoy DOUBLE,
  parent_holder_netprofit DOUBLE, parent_holder_netprofit_yoy DOUBLE,
  basic_eps DOUBLE, diluted_eps DOUBLE,
  gross_profit_ratio DOUBLE, net_profit_ratio DOUBLE,
  roe_avg DOUBLE, roa DOUBLE, roe DOUBLE, roe_yoy DOUBLE,
  -- 运营效率指标
  accounts_rece_tr DOUBLE, inventory_tr DOUBLE, total_assets_tr DOUBLE,
  accounts_rece_tdays DOUBLE, inventory_tdays DOUBLE, total_assets_tdays DOUBLE,
  -- 偿债能力指标
  current_ratio DOUBLE, speed_ratio DOUBLE, ocf_liqdebt DOUBLE,
  debt_asset_ratio DOUBLE, equity_ratio DOUBLE,
  debt_ratio DOUBLE, debt_ratio_yoy DOUBLE,
  -- 同比增长指标
  basic_eps_yoy DOUBLE, gross_profit_ratio_yoy DOUBLE,
  net_profit_ratio_yoy DOUBLE, roe_avg_yoy DOUBLE,
  roa_yoy DOUBLE, debt_asset_ratio_yoy DOUBLE,
  current_ratio_yoy DOUBLE, speed_ratio_yoy DOUBLE,
  -- 金融行业指标
  total_income DOUBLE, total_income_yoy DOUBLE,
  premium_income DOUBLE, premium_income_yoy DOUBLE,
  basic_eps_cs DOUBLE, basic_eps_cs_yoy DOUBLE,
  diluted_eps_cs DOUBLE, diluted_eps_cs_yoy DOUBLE,
  payout_ratio DOUBLE, capitial_ratio DOUBLE,
  currency_abbr VARCHAR(10),
  net_interest_income DOUBLE, net_interest_income_yoy DOUBLE,
  loan_loss_provision DOUBLE, loan_loss_provision_yoy DOUBLE,
  loan_deposit DOUBLE, loan_equity DOUBLE, loan_assets DOUBLE,
  deposit_equity DOUBLE, deposit_assets DOUBLE,
  rol DOUBLE, rod DOUBLE,
  KEY idx_ts_code (ts_code), KEY idx_end_date (end_date),
  KEY idx_ts_code_end_date (ts_code, end_date)
)
```

> **说明**：us_fina_indicator 采用宽表结构（一个指标一列），与 Tushare API 返回格式一致（每行是一只股票一个报告期的完整指标）。与其他三张财务表（us_income/us_balancesheet/us_cashflow）的窄表结构（ind_name + ind_value 键值对）不同。

---

## 七、特殊说明

### 7.1 us_basic — 其他接口的前置依赖

`sync_us_basic` 必须最先执行。其他 8 个接口依赖 us_basic 表获取美股代码列表（`_get_us_stock_codes()` 从 us_basic 查询）。若 us_basic 表为空，其他接口将返回 0 行。

### 7.2 us_fina_indicator — 200条/次限制

us_fina_indicator 是所有接口中限制最严格的（单次仅 200 条），因此采用 **2 年窗口分块** 策略，每只股票约需 6-8 次调用覆盖 2005 年至今。全量同步约 39,000 次 API 调用，耗时 ~130 分钟。

### 7.3 财务表结构差异

| 表 | 结构 | 单只股票行数 | 说明 |
|----|------|------------|------|
| us_income | 窄表（ind_name + ind_value） | ~600 | 7列，每个财务科目一行 |
| us_balancesheet | 窄表（ind_name + ind_value） | ~630 | 同上 |
| us_cashflow | 窄表（ind_name + ind_value） | ~530 | 同上 |
| us_fina_indicator | 宽表（一指标一列） | ~20 | 67列，每个报告期一行 |

### 7.4 日期格式

- API 输入：YYYYMMDD（8位数字字符串）
- API 输出日期：YYYY-MM-DD 或 YYYYMMDD（因接口而异）
- GreatSQL 日期列：VARCHAR(20)（兼容 API 原始格式）
- TDengine ts 列：TIMESTAMP（td_utils 自动将 YYYYMMDD → YYYY-MM-DD 00:00:00）

### 7.5 美股代码列表

当前 us_basic 表包含 **23,455 只美股**（23,357 个独立 ts_code）：
- EQ（普通股）：21,316 只
- ADR（美国存托凭证）：2,057 只
- GDR（全球存托凭证）：82 只

数据跨度从 1925 年至 2025 年（含已退市股票）。

### 7.6 DDL 修正记录

初始 DDL 与实际 API 返回字段不匹配，已全部重建：

| 表 | 问题 | 修正 |
|----|------|------|
| us_basic | 旧DDL有 10 列（fullname/market/list_status/exchange/curr_type），API 只返回 6 列 | 重写为 6 列（ts_code/name/enname/classify/list_date/delist_date） |
| us_income | 旧DDL有 12 列（ann_date/f_ann_date/act_method/comp_type/amount 等），API 返回 ind_value 非 amount | 重写为 7 列窄表结构 |
| us_balancesheet | 同上 | 重写为 7 列 |
| us_cashflow | 同上 | 重写为 7 列 |
| us_fina_indicator | 旧DDL仅 8 列，API 实际返回 67 列 | 重写为 67 列宽表 |
| us_daily | DDL 缺少 vwap 列 | 新增 vwap 列（14列） |
| us_daily_adj | DDL 缺少 vwap、adj_factor 列 | 新增 2 列（17列） |

---

## 八、依赖模块

```
src/utils/sync_utils.py                      # GreatSQL 工具（RateLimiter, insert_dataframe, clear_table 等）
src/utils/td_utils.py                        # TDengine 批量插入工具（insert_dataframe_to_td）
src/fetch_tushare_data/us_stock/             # 9 个 fetch 接口实现
├── fetch_us_basic.py
├── fetch_us_tradecal.py
├── fetch_us_daily.py
├── fetch_us_daily_adj.py
├── fetch_us_adjfactor.py
├── fetch_us_income.py
├── fetch_us_balancesheet.py
├── fetch_us_cashflow.py
└── fetch_us_fina_indicator.py
src/data_sync/full_sync/
└── sync_usstock_data_bydate.py             # 9 个美股接口同步脚本
scripts/
├── sync_usstock_data_all.sh                # 基础数据全量同步（含清理）
└── sync_usstock_data.sh                    # 历史数据按日期同步
src/batch/sql/
├── tdengine/美股数据.sql                    # 3 个超级表 DDL
└── greatsql/美股数据.sql                    # 6 个表 DDL
unit_test/
└── test_sync_usstock_data.py               # 31 个单元测试
```

---

## 九、Tushare 积分权限要求

| 接口 | 积分要求 | 备注 |
|------|---------|------|
| us_basic | 5,000+ | 120积分可试用 |
| us_tradecal | — | 无特殊要求 |
| us_daily | 5,000+ | 120积分可试用 |
| us_daily_adj | 5,000+ | 120积分可试用 |
| us_adjfactor | 5,000+ | 跟随美股日线权限 |
| us_income | 15,000+ | 需单独开权限 |
| us_balancesheet | 15,000+ | 需单独开权限 |
| us_cashflow | 15,000+ | 需单独开权限 |
| us_fina_indicator | 15,000+ | 单次200条，需单独开权限 |


## 十、数据质量（2026-05-18 探查 & 修复）

### 数据概况

| 表 | 行数 | 子表数 | 时间范围 | 状态 |
|----|------|--------|---------|------|
| us_basic | 23,455 | — | 1925-12-31 ~ 2025-09-18 | ✓ |
| us_tradecal | 2,331 | — | 2020-01-01 ~ 2026-05-17 | ✓ |
| us_daily | 17,105,177 | 22,664 | 2020-01-02 ~ 2026-05-15 | ✓ |
| us_daily_adj | 15,022,705 | 22,944 | 2020-01-02 ~ 2026-05-08 | ✓ |
| us_adjfactor | 2,277,344 | 29,459 | 2020-01-14 ~ 2026-05-08 | ✓ |
| us_income | 3,192,245 | — | 2020-01-03 ~ 2026-04-05 | ✓ (已去重) |
| us_balancesheet | 3,511,100 | — | 2020-01-03 ~ 2026-04-05 | ✓ (已去重) |
| us_cashflow | 2,949,512 | — | 2020-01-03 ~ 2026-04-05 | ✓ (已去重) |
| us_fina_indicator | 118,956 | — | 2020-01-03 ~ 2026-04-05 | ✓ (已去重) |

### 总体结论

| 检查项 | 结果 |
|--------|------|
| 数据连续性 | ✓ TDengine 三表 22K+ 子表，2020~2026 连续 |
| API 截断 | ✓ 无截断（us_daily/adj 按 ts_code 循环；us_adjfactor 半月区间≤ 21K 单日股票 < 15K 上限） |
| 数据重复 | ✓ 已去重 6,907 条（us_income 3,078 + balancesheet 2,067 + cashflow 1,691 + fina 71），已加唯一索引 |
| 字段 NULL | us_basic delist_date 91.9% NULL（正常）；fina 行业字段 90%+ NULL（正常） |
| 日期格式 | ✓ 统一正确，无 1970-01-01 等异常占位日期 |
| 同一日期 | ✓ 无异常 |

### 已修复

| 表 | 修复前 | 修复后 | 减少 | 索引 |
|----|--------|--------|------|------|
| us_income | 3,195,323 | 3,192,245 | -3,078 | UNIQUE(ts_code,end_date,ind_name) |
| us_balancesheet | 3,513,167 | 3,511,100 | -2,067 | 同上 |
| us_cashflow | 2,951,203 | 2,949,512 | -1,691 | 同上 |
| us_fina_indicator | 119,027 | 118,956 | -71 | UNIQUE(ts_code,end_date) |
