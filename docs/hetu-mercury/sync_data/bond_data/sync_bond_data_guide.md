# 债券数据同步指南

> 更新日期：2026-05-11 | 同步模块：`src/data_sync/full_sync/sync_bond_data_bydate.py`

---

## 一、接口总览（17 个）

### TDengine 入库（7 个）

| 接口 | 中文名称 | 表名 | 同步策略 | ts 映射 | 数据量 | 最早日期 | 最晚日期 |
|------|---------|------|---------|---------|--------|---------|---------|
| cb_daily | 可转债行情 | cb_daily | 按 3 天区间循环 | trade_date → ts | 660,500 | 2020-01-02 | 2026-05-08 |
| repo_daily | 债券回购日行情 | repo_daily | 按 15 天区间循环 | trade_date → ts | 191 | 2026-04-01 | 2026-04-07 |
| bc_otcqt | 柜台流通式债券报价 | bc_otcqt | 按 7 天 × 银行循环 | trade_date → ts | 255,101 | 2024-03-20 | 2026-05-10 |
| bc_bestotcqt | 柜台流通式债券最优报价 | bc_bestotcqt | 按 2 天区间循环 | trade_date → ts | 0 | — | — |
| bond_blk | 大宗交易 | bond_blk | 按 15 天区间循环 | trade_date → ts | 59,991 | 2020-01-02 | 2026-05-07 |
| bond_blk_detail | 大宗交易明细 | bond_blk_detail | 按 5 天区间循环 | trade_date → ts | 67,328 | 2020-01-02 | 2026-05-07 |
| yc_cb | 国债收益率曲线 | yc_cb | 按 15 天区间循环 | trade_date → ts | 42 | 2020-01-14 | 2026-04-07 |

### GreatSQL 入库（10 个）

| 接口 | 中文名称 | 表名 | 同步策略 | 数据量 | 最早日期 | 最晚日期 |
|------|---------|------|---------|--------|---------|---------|
| cb_basic | 可转债基础信息 | cb_basic | 全量拉取，INSERT IGNORE 去重 | 1,125 | 1993-02-10 | 2026-05-13 |
| cb_issue | 可转债发行 | cb_issue | 按 15 天区间循环 | 4 | 2026-04-14 | 2026-04-16 |
| cb_call | 可转债赎回信息 | cb_call | 按 15 天区间循环 | 62 | 2026-04-01 | 2026-04-30 |
| cb_rate | 可转债票面利率 | cb_rate | 按 ts_code 循环（100只/批） | 4,708 | — | — |
| cb_factor_pro | 可转债技术面因子 | cb_factor_pro | 按 15 天区间循环 | 27,961 | 2020-01-16 | 2026-04-29 |
| cb_price_chg | 可转债转股价变动 | cb_price_chg | 按 ts_code 循环（100只/批） | 5,718 | 1992-11-01 | 2026-05-09 |
| cb_share | 可转债转股结果 | cb_share | 按 ts_code × 15 天区间循环 | 0 | — | — |
| eco_cal | 全球财经事件 | eco_cal | 按 1 天区间循环（专用限速 18/min） | 124,478 | 2020-01-01 | 2026-05-10 |
| top10_cb_holders | 可转债十大持有人 | top10_cb_holders | 按 ts_code 批量（50只/批） × 15 天区间 | 0 | — | — |
| cb_rating | 可转债债券评级 | cb_rating | 按 ts_code 批量（50只/批） | 4,783 | 2001-05-24 | 2026-05-09 |

---

## 二、执行方式

### 2.1 Shell 脚本

```bash
# 基础数据全量（仅初次部署/数据重建，含全量清理）
bash scripts/sync_bond_data_all.sh

# 历史行情按日期同步（日常增量）
bash scripts/sync_bond_data.sh                            # 全量 (2005-01-01 至今)
bash scripts/sync_bond_data.sh 20260401                   # 从指定日期至今
bash scripts/sync_bond_data.sh 20260401 20260430          # 指定日期范围

# OTC及高频接口独立同步
bash scripts/sync_bond_otc.sh                             # bc_otcqt, yc_cb, eco_cal 等
bash scripts/sync_bond_otc.sh 20260401 20260430

# 全球财经事件独立同步（限速 18/min）
bash scripts/sync_eco_cal.sh                              # 全量
bash scripts/sync_eco_cal.sh 20260401 20260430
```

### 2.2 Python 直接调用

```python
from sync_bond_data_bydate import (
    # TDengine
    sync_cb_daily, sync_repo_daily, sync_bc_otcqt, sync_bc_bestotcqt,
    sync_bond_blk, sync_bond_blk_detail, sync_yc_cb,
    # GreatSQL
    sync_cb_basic, sync_cb_issue, sync_cb_call, sync_cb_rate,
    sync_cb_factor_pro, sync_cb_price_chg, sync_cb_share, sync_eco_cal,
    sync_top10_cb_holders, sync_cb_rating,
)

# 全量同步（不传参使用默认起始日期 2005-01-01）
sync_cb_daily()
sync_repo_daily()
sync_eco_cal()

# 增量同步（传日期参数）
sync_cb_daily(start_date="20260506", end_date="20260507")
sync_eco_cal(start_date="20260506", end_date="20260507")

# 无日期接口（全量拉取，不传参）
sync_cb_basic()
sync_cb_rate()
sync_cb_price_chg()
sync_cb_rating()
```

> **全量 vs 增量**：
> - **不传参数** → 使用默认起始日期（2005-01-01）全量拉取
> - **传 start_date/end_date** → 不删已有数据，仅追加新数据
> - **TDengine 自动去重**：同子表+时间戳唯一，重复 INSERT 自动跳过

---

## 三、各接口起始日期与限制

| 接口 | 默认起始日期 | Tushare限制 | chunk策略 | 说明 |
|------|-------------|------------|----------|------|
| cb_basic | — | 2000条/次 | 全量一次 | 当前约 1125 只可转债，未触及上限 |
| cb_issue | 2005-01-01 | 2000条/次 | 15天/区间 | 发行事件稀少，安全 |
| cb_call | 2005-01-01 | 2000条/次 | 15天/区间 | 赎回事件稀少，安全 |
| cb_rate | — | 2000条/次 | ts_code 循环 | 每只转债 3-5 行，远低于上限 |
| cb_daily | 2005-01-01 | 2000条/次 | **3天/区间** | ~500CB×3d≈1500，低于上限 |
| cb_factor_pro | 2005-01-01 | 10000条/次 | 15天/区间 | 上限10000，15天约5000-9000，安全 |
| cb_price_chg | — | 2000条/次 | ts_code 循环 | 每只转债 1-5 行 |
| cb_share | 2005-01-01 | 2000条/次 | ts_code×15天 | 每只转债 1-2 条/区间 |
| repo_daily | 2005-01-01 | 2000条/次 | 15天/区间 | 30品种×15d≈450，远低于上限 |
| bc_otcqt | 2005-01-01 | 2000条/次 | **7天×19银行** | 单日即达2000上限，按银行分片避免截断 |
| bc_bestotcqt | 2005-01-01 | 2000条/次 | **2天/区间** | 日均600-700条，2d≈1200-1400 |
| bond_blk | 2005-01-01 | 未明确 | 15天/区间 | 日约5-15条 |
| bond_blk_detail | 2005-01-01 | 1000条/次 | 5天/区间 | 日约1-15条，远低于上限 |
| yc_cb | 2005-01-01 | 2000条/次 | 15天/区间 | 曲线点×天≈440条 |
| eco_cal | 2005-01-01 | 100条/次 | **1天/区间** | 日约30-80条，2天即超100上限 |
| top10_cb_holders | 2005-01-01 | 3000条/次 | ts_code批×15天 | 50码批×15d≈750条 |
| cb_rating | — | 3000条/次 | ts_code批50个 | 每码1-10条 |

---

## 四、速率限制

| 接口 | 限速器 | 频率 | 实际调用量（全量） | 预估耗时 |
|------|--------|------|-------------------|---------|
| cb_basic | 全局 | 300/min | 1 次 | <1 秒 |
| cb_daily | 全局 | 300/min | ~774 次（3天分区） | ~3 分钟 |
| bc_otcqt | 全局 | 300/min | ~4,500 次（7d×19银行） | ~15 分钟 |
| eco_cal | **专用** | **18/min** | ~2,300 次（1天分区） | ~130 分钟 |
| cb_rate | 全局 | 300/min | ~12 次（1125/100） | <1 分钟 |
| cb_price_chg | 全局 | 300/min | ~12 次 | <1 分钟 |
| cb_rating | 全局 | 300/min | ~23 次（1125/50） | <1 分钟 |
| top10_cb_holders | 全局 | 300/min | ~1,350 次（23批×30区间） | ~5 分钟 |
| 其余接口 | 全局 | 300/min | 较少 | — |

> **eco_cal 频率限制**：Tushare eco_cal 接口单独限速 20次/分钟，代码中使用专用 `_ECO_CAL_LIMITER`（18/min）避免超限。

---

## 五、TDengine 建表注意事项

### 5.1 列映射修正记录

原有的 `td_utils.py` 中 bc_otcqt、repo_daily、bond_blk、bond_blk_detail、bc_bestotcqt、yc_cb 六个表的列映射与 DDL 不符，已统一修正：

| 表 | 旧映射（错误） | 新映射（正确） |
|----|-------------|-------------|
| repo_daily | open/high/low/close/change/pct_chg/vol/amount | repo_maturity/pre_close/open/high/low/close/weight/weight_r/amount/num |
| bc_otcqt | quote_type/open/high/low/close/vol/amount | qt_time/bank/name/maturity/remain_maturity/bond_type/coupon_rate/buy_price/sell_price/buy_yield/sell_yield |
| bc_bestotcqt | quote_type/open/high/low/close/vol/amount | name/remain_maturity/bond_type/best_buy_bank/best_buy_yield/best_buy_price/best_sell_bank/best_sell_yield/best_sell_price |
| bond_blk | trade_type/pre_close/open/high/low/close/vol/amount | name/price/vol/amount |
| bond_blk_detail | trade_type/pre_close/open/high/low/close/vol/amount | name/price/vol/amount/buy_dp/sell_dp |
| yc_cb | curve_type/curve_name/curve/y1~y30 | curve_name/curve_type/curve_term/yield |

### 5.2 子表命名

| 超级表 | 前缀 | 示例 |
|--------|------|------|
| cb_daily | cb_ | cb_110059_SH |
| repo_daily | rp_ | rp_204001_SH |
| bc_otcqt | bo_ | bo_2105773_BC |
| bc_bestotcqt | bb_ | bb_2105773_BC |
| bond_blk | bl_ | bl_122004_SZ |
| bond_blk_detail | bd_ | bd_122004_SZ |
| yc_cb | yc_ | yc_1001_CB |

### 5.3 大写列名处理

Tushare bc_otcqt/bond_blk_detail 等接口返回大写列名（如 `BID_BANK`、`TS_CODE`），同步脚本在 `insert_dataframe_to_td` 前统一执行 `df.columns = [c.lower() for c in df.columns]` 转换。

---

## 六、特殊说明

### 6.1 bc_otcqt — 银行分片策略

单日数据量即达 2000 上限，简单按日期切分无法避免截断。改为「7 天日期区间 × 19 家银行」双重循环，每次请求约 100-400 条，安全低于 2000 上限。银行列表从最近交易日动态获取，自动回退到前一天（处理周末/节假日）。7 天数据量从截断的 ~14,000 提升到完整的 ~26,500 条。

### 6.2 cb_basic — cb_type 列

Tushare API 在 cb_basic 中返回 `cb_type` 字段（CB-可转债 / EB-可交换债），但原始 DDL 未包含此列。已通过 `ALTER TABLE cb_basic ADD COLUMN cb_type VARCHAR(10)` 补全。

### 6.3 yc_cb — DDL 归属调整

yc_cb（国债收益率曲线）原始 DDL 在 GreatSQL 中，但数据为时序型（trade_date + ts_code），已移至 TDengine 超级表。旧 GreatSQL 建表语句已注释保留。

### 6.4 cb_factor_pro — DDL 归属调整

cb_factor_pro（可转债技术面因子）原始 DDL 在 TDengine 中，现改入 GreatSQL。数据量大（89 列，单次 10000 条），采用 15 天区间循环。

### 6.5 GreatSQL 保留字处理

cb_factor_pro 表中 `open`、`high`、`low`、`close`、`change`、`pre_close`、`vol`、`amount` 等列为 MySQL 保留字，DDL 需使用反引号包裹（如 `\`open\``）。sync 代码中 columns 列表使用纯字符串即可，`insert_dataframe` 内部自动加反引号。

### 6.6 API 返回大写列名

bc_otcqt 返回 `BID_BANK`/`TS_CODE` 等大写列名，`_TD_FIELD_MAP` 配置了 `"bid_bank": "bank"` 映射关系。同步模板对所有 DataFrame 统一执行 `df.columns.lower()` 确保匹配。

### 6.7 cb_share — ann_date 必传

cb_share API 要求 `ts_code` + `ann_date` 均为必传参数。同步函数自定义实现，按 `ts_code × 日期区间` 循环，`ann_date` 传区间起始日。

---

## 七、依赖模块

```
src/utils/sync_utils.py                      # GreatSQL 工具（RateLimiter, insert_dataframe, clear_table 等）
src/utils/td_utils.py                        # TDengine 批量插入工具（insert_dataframe_to_td）
src/fetch_tushare_data/bond/                 # 17 个 fetch 接口实现
src/data_sync/full_sync/
└── sync_bond_data_bydate.py                 # 17 个债券接口同步脚本
scripts/
├── sync_bond_data_all.sh                    # 基础数据全量同步（含清理）
├── sync_bond_data.sh                        # 历史行情按日期同步
├── sync_bond_otc.sh                         # OTC 及高频接口独立同步
└── sync_eco_cal.sh                          # 全球财经事件独立同步
src/batch/sql/greatsql/债券专题.sql           # GreatSQL 建表语句
src/batch/sql/tdengine/债券专题.sql           # TDengine 建表语句
interface/bond/                              # 17 个接口 JSON 配置
unit_test/
└── test_sync_bond_data.py                   # 13 个单元测试
```

---

## 八、Tushare 积分权限要求

| 接口 | 积分要求 | 备注 |
|------|---------|------|
| cb_basic | 2,000+ | 有流量控制，5000分以上频次更高 |
| cb_issue | 无 | — |
| cb_call | 5,000+ | — |
| cb_rate | 5,000+ | — |
| cb_daily | 无 | — |
| cb_factor_pro | 无 | 10000条/次 |
| cb_price_chg | 单独权限 | 不绑定积分 |
| cb_share | 2,000+ | 有流量控制 |
| repo_daily | 2,000+ | — |
| bc_otcqt | 无 | 2000条/次 |
| bc_bestotcqt | 无 | 2000条/次 |
| bond_blk | 5,000+ | — |
| bond_blk_detail | 5,000+ | 1000条/次 |
| yc_cb | 单独权限 | 联系管理员开通 |
| eco_cal | 无 | 100条/次，**限速 20/min** |
| top10_cb_holders | 5,000+ | 3000条/次 |
| cb_rating | 2,000+ | 3000条/次 |

---

## 九、踩坑记录

| 问题 | 现象 | 修复 |
|------|------|------|
| TDengine 列映射错误 | bc_otcqt 等 6 个表插入语法错 | 修正 `_TD_COLUMNS_MAP` 与 DDL 对齐，重建 STABLE |
| bc_otcqt 截断 | 单日返回精确 2000 条 | 增加 bank 维度分片（7天×19银行） |
| eco_cal 截断 | 2天区间 >100 上限 | chunk_days 缩至 1 天 |
| eco_cal 频率超限 | 错误 "频率超限(20次/分钟)" | 新增专用 `_ECO_CAL_LIMITER`（18/min） |
| cb_daily 截断 | 15天区间远超 2000 | chunk_days 缩至 3 天 |
| bc_bestotcqt 截断 | 5天区间 >2000 | chunk_days 缩至 2 天 |
| yc_cb DDL 归属错误 | 建在 GreatSQL 中 | 移至 TDengine 超级表 |
| cb_factor_pro DDL 归属错误 | 建在 TDengine 中 | 移至 GreatSQL |
| cb_basic 缺 cb_type 列 | 列不存在 | ALTER TABLE 补全 |
| bc_otcqt BID_BANK 映射 | 字段不匹配 | `_TD_FIELD_MAP` 配置 bid_bank→bank |
| bc_otcqt qt_time 为 NULL | 时间戳缺失 | ts 改用 trade_date 映射 |
| repo_daily 列不匹配 | weight 等列缺失 | 修正 `_TD_COLUMNS_MAP` |
| cb_share ann_date 必传 | API 参数校验失败 | 自定义同步函数传 ann_date=s |
