# 指数专题数据同步指南

> 更新日期：2026-05-18 | 同步模块：`src/data_sync/full_sync/stock_data/sync_index_data_bydate.py`

---

## 一、接口总览（19 个）

### GreatSQL 入库（5 个）

| 接口 | 中文名称 | 表名 | 同步策略 | 单次限制 |
|------|---------|------|---------|---------|
| index_basic | 指数基本信息 | index_basic | 按 market 分批（7个市场），INSERT IGNORE 去重 | 5000条/次 |
| index_weight | 指数成分和权重 | index_weight | 按月末日期拉取 + 14个大指数 index_code 补拉 | 5000条/次 |
| index_classify | 申万行业分类 | sw_index | 全量拉取（默认 SW2014，L1+L2+L3=359条） | — |
| index_member_all | 申万行业成分 | index_member_all | 全量拉取，≥2000条时按 l1_code 补拉 | 2000条/次 |
| ci_index_member | 中信行业成分 | ci_index_member | 全量拉取，≥5000条时按 l1_code 补拉 | 5000条/次 |

### TDengine 入库（14 个）

| 接口 | 中文名称 | STABLE | 同步策略 | 单次限制 |
|------|---------|--------|---------|---------|
| index_daily | 指数日线行情 | index_daily | 按 ts_code 循环，50只/批（21年约5250行<8000） | 8000条/次 |
| index_weekly | 指数周线行情 | index_weekly | 按 ts_code 循环，3年分块（≤156行<1000） | 1000条/次 |
| index_monthly | 指数月线行情 | index_monthly | 按 ts_code 循环，50只/批 | 1000条/次 |
| index_dailybasic | 大盘指数每日指标 | index_dailybasic | 按 ts_code 循环，3年分块（≤750行<3000） | 3000条/次 |
| sw_daily | 申万行业日行情 | sw_daily | 按行业代码循环，3年分块（≤750行<4000） | 4000条/次 |
| ci_daily | 中信行业日行情 | ci_daily | 按行业代码循环，3年分块（≤750行<4000） | 4000条/次 |
| daily_info | 沪深市场交易统计 | daily_info | 按半月区间拉取 | 4000条/次 |
| sz_daily_info | 深圳市场交易情况 | sz_daily_info | 按半月区间拉取 | 2000条/次 |
| idx_mins | 指数历史分钟 | idx_mins | 15个主要指数 × 15min × 按月循环 | 8000条/次 |
| index_global | 国际主要指数日线 | index_global_daily | 按半月区间拉取（20+国际指数） | 4000条/次 |
| idx_factor_pro | 指数技术面因子 | idx_factor_pro | 按 ts_code 循环 | 8000条/次 |
| rt_idx_k | 指数实时日线 | index_rt_daily | 通配符拉取（0*.SH/3*.SZ），实时接口 | — |
| rt_idx_min | 指数实时分钟 | index_rt_min | 按freq+多代码，实时接口 | 1000条/次 |
| rt_sw_k | 申万实时行情 | rt_sw_k | 通配符拉取（80*.SI/85*.SI），实时接口 | — |

---

## 二、执行方式

### 2.1 Shell 脚本

```bash
# 基础数据全量（初次部署：GreatSQL 5张表 + TDengine 国际指数）
bash scripts/sync_index_data_all.sh

# 历史行情按日期同步（日常增量）
bash scripts/sync_index_data.sh                            # 全量 (2005-01-01 至今)
bash scripts/sync_index_data.sh 20260401                   # 从指定日期至今
bash scripts/sync_index_data.sh 20260401 20260430          # 指定日期范围

# 修复接口单独重跑（之前的 Bug 修复后）
bash scripts/sync_index_data_fix.sh                        # index_weight + classify + member 等
bash scripts/sync_index_weight_mins.sh                     # index_weight + idx_mins
bash scripts/sync_idx_mins.sh                              # idx_mins(15min) 单独同步

# 实时接口（手工执行，不放 shell）
python -c "
from sync_index_data_bydate import sync_rt_idx_k, sync_rt_idx_min, sync_rt_sw_k
sync_rt_idx_k(); sync_rt_idx_min(freq='5MIN'); sync_rt_sw_k()
"
```

### 2.2 Python 直接调用

```python
from sync_index_data_bydate import (
    # GreatSQL (5个)
    sync_index_basic, sync_index_weight, sync_index_classify,
    sync_index_member_all, sync_ci_index_member,
    # TDengine (14个)
    sync_index_daily, sync_index_weekly, sync_index_monthly,
    sync_index_dailybasic, sync_sw_daily, sync_ci_daily,
    sync_daily_info, sync_sz_daily_info, sync_idx_mins,
    sync_index_global, sync_idx_factor_pro,
    sync_rt_idx_k, sync_rt_idx_min, sync_rt_sw_k,
)

# GreatSQL — 全量拉取（不传参）
sync_index_basic()
sync_index_classify()
sync_index_member_all()
sync_ci_index_member()

# TDengine — 全量
sync_index_daily()
sync_index_weekly()
sync_index_monthly()
sync_index_dailybasic()
sync_sw_daily()
sync_ci_daily()
sync_daily_info()
sync_sz_daily_info()
sync_idx_mins()                              # 默认 15min × 15个主要指数
sync_index_global()
sync_idx_factor_pro()

# TDengine — 增量（传日期参数）
sync_index_daily(start_date="20260506", end_date="20260508")
sync_index_weight(start_date="20260401", end_date="20260430")

# TDengine — 实时（不传日期）
sync_rt_idx_k(ts_code="0*.SH,3*.SZ")
sync_rt_idx_min(freq="5MIN")
sync_rt_sw_k(ts_code="80*.SI,85*.SI")
```

---

## 三、同步策略详解

### 3.1 按 ts_code 循环（从 index_basic 获取代码）

**index_daily / index_weekly / index_monthly / index_dailybasic / idx_factor_pro**

50只/批，每批 ts_code × 日期范围调用 API。对超限接口使用 `year_chunk` 分块：

| 接口 | year_chunk | 原因 |
|------|-----------|------|
| index_weekly | 3年 | 21年×52=1092行 > 1000限制 |
| index_dailybasic | 3年 | 21年×250=5250行 > 3000限制 |
| sw_daily / ci_daily | 3年 | 21年×250=5250行 > 4000限制 |

### 3.2 按行业代码循环

**sw_daily** 从 `sw_index` 表获取代码，**ci_daily** 从 `ci_index_member` 表获取三级行业代码。

### 3.3 按日期区间拉取

**daily_info / sz_daily_info / index_global** 使用半月区间拆分请求，避免单次超限。

### 3.4 按月末日期拉取

**index_weight** 先按月末日期获取全部指数成分（每次约6000行），再对14个大指数用 `index_code` + 3年分块补拉完整数据。

### 3.5 index_basic — 按 market 分批

全市场约8000+指数，API单次5000。按 SSE/SZSE/CSI/SW/MSCI/CICC/OTH 7个市场分批拉取。

### 3.6 实时接口

**rt_idx_k / rt_idx_min / rt_sw_k** 使用通配符拉取实时快照，API 不返回历史日期字段，入库时自动补当前时间作为 ts。

---

## 四、td_utils.py STABLE 映射

| 代码中表名 | TDengine STABLE | 前缀 | ts来源 |
|-----------|----------------|------|--------|
| index_daily | index_daily | id_ | trade_date |
| index_weekly | index_weekly | iw_ | trade_date |
| index_monthly | index_monthly | io_ | trade_date |
| index_dailybasic | index_dailybasic | ib_ | trade_date |
| sw_daily | sw_daily | sw_ | trade_date |
| ci_daily | ci_daily | cd_ | trade_date |
| daily_info | daily_info | di_ | trade_date |
| sz_daily_info | sz_daily_info | si_ | trade_date |
| idx_mins | idx_mins | in_ | trade_time |
| index_global | index_global_daily | ig_ | trade_date |
| idx_factor_pro | idx_factor_pro | if_ | trade_date |
| rt_idx_k | index_rt_daily | ir_ | trade_date(自动补) |
| rt_idx_min | index_rt_min | im_ | time(自动补) |
| rt_sw_k | rt_sw_k | sk_ | trade_date(自动补) |

---

## 五、关键 Bug 修复记录（2026-05-07 ~ 05-09）

| 日期 | 问题 | 修复 |
|------|------|------|
| 05-07 | `index_basic` DDL `weight` → API `weight_rule`，缺 `index_type` | ALTER TABLE |
| 05-07 | `index_dailybasic` DDL 多余字段 `close/volume_ratio/circ_mv` | DROP STABLE 重建 |
| 05-07 | `sw_daily` DDL 缺 `name/pe/pb/float_mv/total_mv`；`pct_chg`→API用`pct_change` | DROP STABLE 重建 |
| 05-07 | `ci_daily` `pct_chg` → API用 `pct_change` | DROP STABLE 重建 |
| 05-07 | `daily_info` DDL 字段与API不匹配（`count`→`com_count+trans_count`） | DROP STABLE 重建 |
| 05-07 | `rt_idx_k` DDL 多 `num/ask_volume1/bid_volume1`(API不返)；缺 `name` | DROP STABLE 重建 |
| 05-07 | `index_global` / `idx_factor_pro` 错放 GreatSQL | 迁至TDengine |
| 05-07 | `index_weekly` 21年超1000限制 | 加 `year_chunk=3` |
| 05-07 | `idx_mins` 全日期范围一次请求，数据量远超8000 | 改为按月循环 |
| 05-08 | `index_weight` fetch 参数 `ts_code`→应为 `index_code`，永远返回0行 | 修复参数名 |
| 05-08 | `index_classify` 传 `src="SW"` 返回0行 | 不传 src，默认 SW2014 |
| 05-08 | `idx_mins` STABLE 名不一致 (`index_min` vs `idx_mins`) | 重建STABLE |
| 05-08 | `rt_idx_k`/`rt_idx_min` STABLE 名与代码中不一致 | td_utils 加映射 |
| 05-09 | `idx_mins` `freq` 作为 TAG 导致 INSERT 语法错误 | `freq` 改为普通列 |
| 05-09 | `idx_mins` 12456指数×5频率卡死 | 改为15个主要指数×15min |

---

## 六、依赖模块

```
src/utils/sync_utils.py                      # GreatSQL 工具（RateLimiter, insert_dataframe）
src/utils/td_utils.py                        # TDengine 批量插入（insert_dataframe_to_td）
src/fetch_tushare_data/index/                # 19个 fetch 接口实现
src/data_sync/full_sync/stock_data/
└── sync_index_data_bydate.py                # 19个指数接口同步脚本
scripts/
├── sync_index_data_all.sh                   # 基础数据全量同步
├── sync_index_data.sh                       # 历史行情按日期同步
├── sync_index_data_fix.sh                   # Bug修复后重新同步
├── sync_index_weight_mins.sh                # index_weight + idx_mins
├── sync_idx_mins.sh                         # idx_mins(15min) 单独同步
└── resync_index_fix.sh                      # 修复重跑（index_basic/sz_daily_info/index_global/idx_factor_pro）
```

---

## 七、数据库分类原则

| 数据库 | 适用场景 | 指数数据中的体现 |
|--------|---------|----------------|
| **GreatSQL** | 基础信息、映射关系、不频繁变动的参考数据 | index_basic（基本信息）、index_weight（成分权重）、sw_index（行业分类）、index_member_all/ci_index_member（成分映射） |
| **TDengine** | 时序数据、按时间轴查询、高频更新的行情/指标 | index_daily/weekly/monthly（日周月线）、sw_daily/ci_daily（行业行情）、idx_mins（分钟）、idx_factor_pro（技术因子）等 |

---

## 八、数据质量（2026-05-17 探查 & 修复）

### 8.1 数据概况

#### GreatSQL

| 表 | 行数 | 说明 |
|----|------|------|
| index_basic | 12,456 | 7 个市场：CSI 4,879 / MSCI 3,298 / OTH 2,380 / SW 796 / SSE 594 / SZSE 447 / CICC 62 |
| index_weight | 1,173,300 | 4,176 只指数，510 个月末日期，2005-05-31 ~ 2026-05-06 |
| sw_index | 359 | L1:28 / L2:104 / L3:227（SW2014） |
| index_member_all | 5,847 | 申万行业成分，L1:31 / L2:131 / L3:337 |
| ci_index_member | 5,764 | 中信行业成分，30 个一级行业 |

#### TDengine

| 表 | 行数 | 子表数 | 时间范围 |
|----|------|--------|---------|
| index_daily | 13,880,155 | 4,295 | 2005-01-03 ~ 2026-05-08 |
| index_weekly | 1,182,789 | 2,902 | 2005-01-07 ~ 2026-04-30 |
| index_monthly | 277,202 | 2,944 | 2005-01-31 ~ 2026-04-30 |
| index_dailybasic | 56,329 | 12 | 2005-01-04 ~ 2026-05-07 |
| sw_daily | 1,007,022 | 359 | 2012-08-01 ~ 2026-05-07 |
| ci_daily | 794,858 | 279 | 2010-01-04 ~ 2026-05-07 |
| daily_info | 103,864 | 34 | 2005-01-04 ~ 2026-05-07 |
| sz_daily_info | 68,007 | 24 | 2008-01-02 ~ 2026-05-15 |
| idx_mins | 868,751 | 14 | 2009-01-05 ~ 2026-05-08 |
| index_global_daily | 93,271 | 24 | 2005-01-03 ~ 2026-05-15 |
| idx_factor_pro | 5,511,117 | 1,812 | 2005-01-03 ~ 2026-05-15 |
| index_rt_daily | 0 | — | 实时快照表 |
| index_rt_min | 0 | — | 实时快照表 |
| rt_sw_k | 0 | — | 实时快照表 |

### 8.2 总体结论

| 检查项 | 结果 |
|--------|------|
| 数据连续性 | ✓ 大盘指数（000001.SH / 399001.SZ / 000300.SH / 000905.SH / 399006.SZ）与交易日历完美对齐，零缺失 |
| API 截断 | ✓ 所有表均未发现行数恰好等于 API limit 的子表 |
| 数据重复 | ✓ 已修复，三张表均已去重并加唯一索引 |
| 字段 NULL | 见下方明细（均为正常业务数据） |
| 日期格式 | ✓ GreatSQL 为 DATE 类型，TDengine 为 TIMESTAMP 类型，格式统一 |
| 同一日期 | ✓ 无异常 |

### 8.3 已修复问题记录（2026-05-17）

| 问题 | 根因 | 修复方式 |
|------|------|---------|
| idx_factor_pro 仅 1 行 | 12,456 只指数循环过慢，同步未跑完 | 通过 `resync_index_fix.sh` 全量重跑，最终：1,812 子表 / 5,511,117 行 |
| sz_daily_info 空表 | API 返回中文 ts_code（`股票`/`ETF`等），生成 TDengine 子表名非法 | `td_utils.py` 增加非 ASCII ts_code 的 hashlib 哈希处理 |
| index_global_daily 停在 2025-03-14 | 增量同步中断 | 从 2025-03-15 补跑 |
| index_weight 10,557 组重复 | 月末拉取与大指数补拉重叠，表无唯一索引 | swap 表去重 + `UNIQUE KEY(index_code, con_code, trade_date)` |
| index_member_all 3,000 组重复 | INSERT IGNORE 无唯一索引兜底 | swap 表去重 + `UNIQUE KEY(l3_code, ts_code)` |
| ci_index_member 5,000 组重复 | 同上 | swap 表去重 + `UNIQUE KEY(l3_code, ts_code)` |
| index_basic fullname/weight_rule/desc 100% NULL | API 非默认输出字段，fetch 未传 `fields` 参数 | `fetch_index_basic.py` 添加显式 `fields` 参数，TRUNCATE 重跑 |

### 8.4 字段 NULL 明细（正常业务数据）

**GreatSQL:**

| 表 | 字段 | NULL 率 | 说明 |
|----|------|---------|------|
| index_basic | index_type | 100% | API 本身不返回该字段 |
| index_basic | exp_date | 92.6% | 大多数指数不过期 |
| index_basic | desc | 30.3% | MSCI/OTH 等部分市场指数无描述 |
| sw_index | is_pub | 100% | API 不返回该字段 |
| index_member_all / ci_index_member | out_date | 100% | 当前成分股无退出日期 |

**TDengine:**

| 表 | 字段 | NULL 率 | 说明 |
|----|------|---------|------|
| index_daily | open, high, low | 65% | MSCI/OTH 等非 A 股指数 API 仅返回 close，无 OHLC |
| index_daily | vol, amount | 17% | 部分指数无成交量数据 |
| index_weekly / index_monthly | vol, amount | 13% | 同上 |
| ci_daily | open, high, low 等 | 16% | 部分中信行业指数缺 OHLC |
| daily_info | total_share, float_share | 52% | 早期数据及部分市场类型不提供 |
| daily_info | trans_count | 66% | 多数市场类型不返回笔数 |
| daily_info | pe, tr | 69%~80% | 仅部分市场类型有估值/换手率 |
| sz_daily_info | total_share, float_share | 35% | 部分市场类型不提供 |
| index_global_daily | amount | 100% | 国际指数 API 不提供成交额 |
| index_global_daily | vol | 40% | 部分国际指数无成交量 |
| idx_factor_pro | ma_bfq_250 | 6.23% | 新指数上市不足 250 天无法计算 |
| idx_mins | — | 0% | 所有字段零 NULL；14 只指数，每交易日恰好 17 条（15min）。API 数据源缺失 4 天（2009-05-05、2009-06-05、2009-12-04、2025-07-11），无法补跑 |
