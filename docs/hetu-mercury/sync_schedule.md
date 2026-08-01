# 数据同步调度说明

> 更新日期：2026-05-23

## 更新策略总览

| 频率 | 数据 | 脚本 | 时间 | 耗时 |
|------|------|------|------|------|
| **每日 18:30** | A股 行情/资金流/两融/基础/特色 | `daily_stock_sync.sh` | 盘后数据就绪 | ~15min |
| **每日 22:30** | A股 打板/热榜/九转/AH比价 | `daily_limitup_sync.sh` | 热榜 22:30 最终版 | ~5min |
| **每日** | ETF/指数/基金/期货/债券/外汇/港股/宏观/语料 | `daily_*.sh` | 全天候 | 均秒级 |
| **每周六 08:00** | 参考数据/指数重任务/基金重任务 | `weekly_*.sh` | 周末空闲 | ~2h |
| **每月 1 号** | A股+港股+美股财务 / 宏观月度 | `monthly_*.sh` | 月初 | ~8h |

---

## ✅ 高效单日方法（1 次 API = 全市场）

以下接口已实现 `fetch_xxx_daily()` 方法，仅传日期参数即可一次返回全市场数据，替代原来逐只股票循环（5,500 次 → 1 次）。

| 模块 | 接口 | 方法 | 上限 | 单日行数 | 余量 |
|------|------|------|------|---------|------|
| market | daily + adj_factor | `fetch_daily_with_adj()` | 6,000 | 5,491 | 8.5% |
| market | adj_factor | `fetch_adj_factor(trade_date)` | — | 5,491 | — |
| moneyflow | moneyflow | `fetch_moneyflow_daily()` | 6,000 | 5,180 | 13.7% |
| moneyflow | moneyflow_ths | `fetch_moneyflow_ths_daily()` | 6,000 | 5,191 | 13.5% |
| moneyflow | moneyflow_dc | `fetch_moneyflow_dc_daily()` | 6,000 | 5,954 | **0.7%** ⚠️ |
| special | ccass_hold | `fetch_ccass_hold_daily()` | — | 933 | — |
| special | stk_auction_o | `fetch_stk_auction_o_daily()` | 10,000 | 5,496 | 45% |
| special | stk_auction_c | `fetch_stk_auction_c_daily()` | 10,000 | 5,512 | 45% |
| special | stk_nineturn | `fetch_stk_nineturn_daily()` | 10,000 | 5,491 | 45% |
| reference | stk_shock | `fetch_stk_shock(trade_date)` | — | ~52 | — |
| reference | stk_high_shock | `fetch_stk_high_shock(trade_date)` | — | ~3 | — |
| reference | stk_alert | `fetch_stk_alert_daily()` | — | <10 | — |
| reference | stk_holdernumber | `fetch_stk_holdernumber_daily()` | — | 183 | — |
| reference | pledge_stat | `fetch_pledge_stat_daily()` | — | 3,000 | — |
| ETF | fund_daily | `fetch_fund_daily_daily()` | 5,000 | 1,971 | 60% |
| ETF | etf_share_size | `fetch_etf_share_size_daily()` | 5,000 | 1,504 | 70% |
| fund | fund_nav | `fetch_fund_nav_daily()` | — | 10,500 | — |
| fund | fund_div | `fetch_fund_div_daily()` | — | 49 | — |
| fund | fund_share | `fetch_fund_share_daily()` | — | 1,580 | — |
| futures | fut_daily | `fetch_fut_daily_daily()` | 8,000 | 1,074 | 87% |
| bond | cb_daily | `fetch_cb_daily_daily()` | 6,000 | 337 | 94% |
| HK | hk_daily | `fetch_hk_daily_daily()` | — | 2,289 | — |
| HK | hk_daily_adj | `fetch_hk_daily_adj_daily()` | — | 3,165 | — |
| HK | hk_adjfactor | `fetch_hk_adjfactor_daily()` | — | 4,297 | — |

> ⚠️ `moneyflow_dc` 余量仅 0.7%（46 行），随新股上市可能超限，需关注。

### 不能使用高效单日的接口

| 接口 | 原因 |
|------|------|
| fund_adj | 1,988/2,000 上限，余量 12 行 |
| us_daily/us_daily_adj/us_adjfactor | API 硬截断 8,000/15,000 行 |
| opt_daily | 15,000 超 6,000 上限 |
| cyq_perf | 5,491 超 5,000 上限 |
| share_float | 6,000 被 API 截断 |
| index_daily/stk_mins/pledge_detail/top10_holders | `ts_code` 参数必填 |

---

## 每日 18:30 — A 股核心数据

`scripts/sync_by_day/daily_stock_sync.sh`

### 基础数据
| 接口 | 库 | 说明 |
|------|-----|------|
| stock_basic/company/st/stk_rewards/bse_mapping | GreatSQL | 基础快照 |
| trade_cal/stk_premarket/stock_st/stock_hsgt/namechange/stk_managers/new_share/bak_basic | GreatSQL/TDengine | 按日增量 |

### 行情数据
| 接口 | 库 | 方式 |
|------|-----|------|
| daily + adj_factor | TDengine | ✅ 高效单日（替代 pro_bar） |
| daily_basic/stk_limit/suspend_d | TDengine | 日期区间 |
| weekly/monthly/stk_weekly_monthly/stk_week_month_adj | TDengine | 日期区间 |
| hsgt_top10/ggt_top10/ggt_daily/ggt_monthly | TDengine | 日期区间 |
| stk_mins | TDengine | 日期区间 |

### 两融
| 接口 | 库 | 说明 |
|------|-----|------|
| margin/margin_detail/margin_secs/slb_len | TDengine | 日期区间 |

### 资金流向
| 接口 | 库 | 方式 |
|------|-----|------|
| moneyflow/ths/dc | TDengine | ✅ 高效单日 |
| cnt_ths/ind_ths/ind_dc/mkt_dc/hsgt | TDengine | 日期区间 |

### 特色数据
| 接口 | 库 | 方式 |
|------|-----|------|
| ccass_hold | TDengine | ✅ 高效单日 |
| stk_auction_o/c | TDengine | ✅ 高效单日 |
| cyq_perf | TDengine | 逐股（超 5,000 限） |
| cyq_chips | TDengine | 逐股（price TAG） |
| report_rc | GreatSQL | REPLACE 日期区间 |
| stk_surv | GreatSQL | REPLACE 逐股 |

---

## 每日 22:30 — 打板专题

`scripts/sync_by_day/daily_limitup_sync.sh`

### 打板专题
| 接口 | 库 |
|------|-----|
| top_list/top_inst/limit_list_ths/limit_list_d/limit_step | TDengine |
| ths_daily/dc_daily/tdx_daily/kpl_list | TDengine |
| stk_auction/hm_detail | TDengine |
| limit_cpt_list/ths_index/ths_member/dc_index/dc_member/dc_concept | GreatSQL |
| ths_hot/dc_hot/tdx_index/tdx_member/hm_list/kpl_concept_cons | GreatSQL |

### 晚间更新（21 点后）
| 接口 | 库 | 方式 |
|------|-----|------|
| stk_nineturn | TDengine | ✅ 高效单日 |
| stk_ah_comparison | TDengine | 日期区间 |

---

## 每日 — 其他板块（均秒级完成）

| 脚本 | 涵盖 |
|------|------|
| `daily_etf_sync.sh` | ETF 基础 + fund_daily/etf_share（高效单日） |
| `daily_index_sync.sh` | 指数基础 + weekly/dailybasic/sw/ci/global 等 8 个快速接口 |
| `daily_fund_sync.sh` | 基金基础 + nav/div/share（高效单日） |
| `daily_futures_sync.sh` | 期货基础 + fut_daily（高效单日） + 持仓/结算 |
| `daily_bond_sync.sh` | 债券基础 + cb_daily（高效单日） + 回购/大宗 |
| `daily_forex_sync.sh` | 外汇基础 + 日线 |
| `daily_hkstock_sync.sh` | 港股基础 + 日线/复权/因子（高效单日） |
| `daily_macro_sync.sh` | Shibor/Libor/国债等 12 个利率接口 |
| `daily_llmcorpus_sync.sh` | 新闻/公告/研报/政策等 8 个接口 |
| `daily_commodity_sync.sh` | 黄金现货 |
| `daily_option_sync.sh` | 期权日线 |
| `daily_usstock_sync.sh` | 美股日线/复权/因子（不可高效，8K 截断） |

---

## 每周 — 重任务

### 参考数据 `weekly_reference_sync.sh`
| 接口 | 库 | 方式 |
|------|-----|------|
| stk_shock/high_shock/alert | TDengine | ✅ 高效逐日遍历 |
| stk_holdernumber | GreatSQL | ✅ 高效 REPLACE |
| pledge_stat | GreatSQL | ✅ 高效 REPLACE |
| block_trade/stk_holdertrade | TDengine | 日期区间 |
| share_float/repurchase | GreatSQL | 日期区间 |
| top10_holders/floatholders | GreatSQL | 逐股 |
| pledge_detail | GreatSQL | 逐股 |

### 指数重任务 `weekly_index_sync.sh`
| 接口 | 说明 |
|------|------|
| index_daily | 12,456 代码逐股（80min），日更放不动 |
| idx_mins | 分钟线逐股 |
| idx_factor_pro | 技术因子逐股 |

### 基金重任务 `weekly_fund_sync.sh`
| 接口 | 说明 |
|------|------|
| fund_manager | 22,288 基金逐只（2min+），日更浪费 |
| fund_portfolio | 季度数据，每月跑即可 |

---

## 每月 — 财务 + 宏观

### `monthly_stock_sync.sh`
| 接口 | 说明 |
|------|------|
| income/balancesheet/cashflow | A股三大报表（report_type 1~12 循环） |
| forecast/express/dividend/fina_indicator | 业绩预告/快报/分红/财务指标 |
| fina_audit/fina_mainbz/disclosure_date | 审计/主营/披露日期 |
| hkstock_financial | 港股利润表/资产负债/现金流/财务指标 |
| usstock_financial | 美股利润表/资产负债/现金流/财务指标 |

### `monthly_macro_sync.sh`
| 接口 | 说明 |
|------|------|
| cn_gdp/cn_cpi/cn_ppi | GDP/CPI/PPI |
| cn_m/sf_month/cn_pmi | 货币/社融/PMI |

---

## 脚本目录

```
scripts/
├── sync_by_day/         # 每日（14 个脚本）
│   ├── daily_stock_sync.sh       18:30  A股核心
│   ├── daily_limitup_sync.sh     22:30  打板/热榜
│   ├── daily_etf_sync.sh               ETF
│   ├── daily_index_sync.sh             指数（秒级快速接口）
│   ├── daily_fund_sync.sh              基金（秒级）
│   ├── daily_futures_sync.sh           期货
│   ├── daily_bond_sync.sh              债券
│   ├── daily_forex_sync.sh             外汇
│   ├── daily_hkstock_sync.sh           港股
│   ├── daily_usstock_sync.sh           美股
│   ├── daily_macro_sync.sh             宏观利率
│   ├── daily_llmcorpus_sync.sh         大模型语料
│   ├── daily_commodity_sync.sh         现货
│   └── daily_option_sync.sh            期权
├── sync_by_week/        # 每周（3 个脚本）
│   ├── weekly_reference_sync.sh        参考数据
│   ├── weekly_index_sync.sh            指数重任务
│   └── weekly_fund_sync.sh             基金重任务
└── sync_by_month/       # 每月（2 个脚本）
    ├── monthly_stock_sync.sh           A股+港股+美股财务
    └── monthly_macro_sync.sh           宏观月度指标
```

---

## Cron 配置

```bash
# ========== 每日 18:30 — A 股核心 ==========
30 18 * * 1-5 cd ~/prod/hetu-altas/hetu-mercury && bash scripts/sync_by_day/daily_stock_sync.sh

# ========== 每日 22:30 — 打板/热榜/九转 ==========
30 22 * * 1-5 cd ~/prod/hetu-altas/hetu-mercury && bash scripts/sync_by_day/daily_limitup_sync.sh

# ========== 每日 19:00 — 其他板块 ==========
0 19 * * 1-5 cd ~/prod/hetu-altas/hetu-mercury && bash scripts/sync_by_day/daily_etf_sync.sh
2 19 * * 1-5 cd ~/prod/hetu-altas/hetu-mercury && bash scripts/sync_by_day/daily_index_sync.sh
4 19 * * 1-5 cd ~/prod/hetu-altas/hetu-mercury && bash scripts/sync_by_day/daily_fund_sync.sh
6 19 * * 1-5 cd ~/prod/hetu-altas/hetu-mercury && bash scripts/sync_by_day/daily_futures_sync.sh
8 19 * * 1-5 cd ~/prod/hetu-altas/hetu-mercury && bash scripts/sync_by_day/daily_bond_sync.sh
10 19 * * 1-5 cd ~/prod/hetu-altas/hetu-mercury && bash scripts/sync_by_day/daily_forex_sync.sh
12 19 * * 1-5 cd ~/prod/hetu-altas/hetu-mercury && bash scripts/sync_by_day/daily_hkstock_sync.sh
14 19 * * 1-5 cd ~/prod/hetu-altas/hetu-mercury && bash scripts/sync_by_day/daily_macro_sync.sh
16 19 * * 1-5 cd ~/prod/hetu-altas/hetu-mercury && bash scripts/sync_by_day/daily_llmcorpus_sync.sh

# ========== 每周六 08:00 — 参考数据 + 重任务 ==========
0 8 * * 6 cd ~/prod/hetu-altas/hetu-mercury && bash scripts/sync_by_week/weekly_reference_sync.sh
30 8 * * 6 cd ~/prod/hetu-altas/hetu-mercury && bash scripts/sync_by_week/weekly_index_sync.sh
0 9 * * 6 cd ~/prod/hetu-altas/hetu-mercury && bash scripts/sync_by_week/weekly_fund_sync.sh

# ========== 每月 1 号 — 财务 + 宏观 ==========
0 2 1 * * cd ~/prod/hetu-altas/hetu-mercury && bash scripts/sync_by_month/monthly_stock_sync.sh
0 4 1 * * cd ~/prod/hetu-altas/hetu-mercury && bash scripts/sync_by_month/monthly_macro_sync.sh
```