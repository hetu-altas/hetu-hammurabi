# 宏观经济数据同步指南

> 更新日期：2026-05-18 | 同步模块：`src/data_sync/full_sync/sync_macro_data_bydate.py`

---

## 一、接口总览（18 个）

全部 18 个接口统一入 TDengine，按数据频率分为三类：

### 1.1 国内利率类（7 个，按日更新）

| 接口 | 中文名称 | 表名 | 同步策略 | ts 映射 | 数据量 | 最早日期 | 最晚日期 |
|------|---------|------|---------|---------|--------|---------|---------|
| shibor | Shibor利率 | shibor | 按 120 天区间循环 | date → ts | **4,873** | 2006-10-08 | 2026-05-14 |
| shibor_quote | Shibor报价数据 | shibor_quote | 按 120 天区间循环 | date → ts | **4,369** | 2006-10-08 | 2026-05-14 |
| shibor_lpr | LPR贷款基础利率 | shibor_lpr | 按 365 天区间循环 | date → ts | **1,527** | 2013-10-25 | 2026-03-20 |
| libor | Libor利率 | libor | 按货币×120天循环 | date → ts | **19,614** | 2005-01-03 | 2020-06-24 |
| hibor | Hibor利率 | hibor | 按 120 天区间循环 | date → ts | **3,522** | 2005-01-03 | 2020-06-24 |
| wz_index | 温州民间借贷利率 | wz_index | **单次全量** | date → ts | **2,324** | 2013-01-04 | 2023-03-08 |
| gz_index | 广州民间借贷利率 | gz_index | **单次全量** | date → ts | **1,181** | 2013-04-18 | 2019-03-04 |

### 1.2 国内宏观经济指标（6 个，按季/月更新）

| 接口 | 中文名称 | 表名 | 同步策略 | ts 映射 | 数据量 | 最早日期 | 最晚日期 |
|------|---------|------|---------|---------|--------|---------|---------|
| cn_gdp | 国内生产总值 | cn_gdp | **单次全量** | quarter → ts | **84** | 2005-01-01 | 2025-10-01 |
| cn_cpi | 居民消费价格指数 | cn_cpi | **单次全量** | month → ts | **256** | 2005-01-01 | 2026-04-01 |
| cn_ppi | 工业生产者出厂价格指数 | cn_ppi | **单次全量** | month → ts | **256** | 2005-01-01 | 2026-04-01 |
| cn_m | 货币供应量（月） | cn_m | **单次全量** | month → ts | **255** | 2005-01-01 | 2026-03-01 |
| sf_month | 社融增量（月度） | sf_month | **单次全量** | month → ts | **255** | 2005-01-01 | 2026-03-01 |
| cn_pmi | 采购经理指数 | cn_pmi | **单次全量** | month → ts | **255** | 2005-01-01 | 2026-03-01 |

### 1.3 美国国债利率类（5 个，按日更新）

| 接口 | 中文名称 | 表名 | 同步策略 | ts 映射 | 数据量 | 最早日期 | 最晚日期 |
|------|---------|------|---------|---------|--------|---------|---------|
| us_tycr | 国债收益率曲线利率 | us_tycr | 按 120 天区间循环 | date → ts | **5,344** | 2005-01-03 | 2026-05-13 |
| us_trycr | 国债实际收益率曲线利率 | us_trycr | 按 120 天区间循环 | date → ts | **5,342** | 2005-01-03 | 2026-05-13 |
| us_tbr | 短期国债利率 | us_tbr | 按 120 天区间循环 | date → ts | **5,345** | 2005-01-03 | 2026-05-13 |
| us_tltr | 国债长期利率 | us_tltr | 按 120 天区间循环 | date → ts | **5,343** | 2005-01-03 | 2026-05-13 |
| us_trltr | 国债长期利率平均值 | us_trltr | 按 120 天区间循环 | date → ts | **5,343** | 2005-01-03 | 2026-05-13 |

> **总计**：18 张表，**62,163 行**数据

---

## 二、执行方式

### 2.1 Shell 脚本

```bash
# 全量同步（含清理重建超级表）
bash scripts/sync_macro_data_all.sh

# 历史数据按日期同步（日常增量）
bash scripts/sync_macro_data.sh                            # 全量 (2005-01-01 至今)
bash scripts/sync_macro_data.sh 20260401                   # 从指定日期至今
bash scripts/sync_macro_data.sh 20260401 20260430          # 指定日期范围
bash scripts/sync_macro_data.sh 20260506 20260507          # 增量 (非交易日返回0行)
```

### 2.2 Python 直接调用

```python
from sync_macro_data_bydate import (
    # 国内利率类
    sync_shibor, sync_shibor_quote, sync_shibor_lpr,
    sync_libor, sync_hibor, sync_wz_index, sync_gz_index,
    # 国内宏观指标
    sync_cn_gdp, sync_cn_cpi, sync_cn_ppi, sync_cn_m,
    sync_sf_month, sync_cn_pmi,
    # 美国国债利率
    sync_us_tycr, sync_us_trycr, sync_us_tbr, sync_us_tltr, sync_us_trltr,
)

# 全量同步（不传参使用默认起始日期 2005-01-01）
sync_shibor()
sync_cn_gdp()
sync_us_tycr()

# 增量同步（传日期参数）
sync_shibor(start_date="20260506", end_date="20260507")
sync_cn_cpi(start_date="20260101", end_date="20260630")

# 并行执行所有18个接口
from sync_macro_data_bydate import run_all_sync
result = run_all_sync()
```

> **全量 vs 增量**：
> - **不传参数** → 使用默认起始日期（2005-01-01）全量拉取
> - **传 start_date/end_date** → 不删已有数据，仅追加新数据
> - **TDengine 自动去重**：同子表+时间戳唯一，重复 INSERT 自动跳过
> - 月度/季度接口同样支持 start_date/end_date（内部自动转为 YYYYMM/YYYYQn 格式）

---

## 三、各接口起始日期与限制

| 接口 | 默认起始日期 | Tushare 限制 | chunk 策略 | 说明 |
|------|-------------|------------|----------|------|
| shibor | 2005-01-01 | **2000条/次**，120积分 | 120天/区间 | 日均1条，120天≈85条，远低于上限 |
| shibor_quote | 2005-01-01 | **4000条/次**，120积分 | 120天/区间 | 日均~18条×(~85天)≈1500条，安全 |
| shibor_lpr | 2005-01-01 | **4000条/次**，120积分 | 365天/区间 | LPR非每日更新，年约20条 |
| libor | 2005-01-01 | **4000条/次**，120积分 | 120天×5币种 | **专用限速器 150/min** |
| hibor | 2005-01-01 | **4000条/次**，120积分 | 120天/区间 | 日均1条 |
| wz_index | 2005-01-01 | **不限量**，2000积分 | **单次全量** | 不限量接口，一次取全部 |
| gz_index | 2005-01-01 | **不限量**，2000积分 | **单次全量** | 不限量接口，一次取全部 |
| cn_gdp | 2005-01-01 | **10000条/次**，600积分 | **单次全量** | 仅84行/季度数据 |
| cn_cpi | 2005-01-01 | 未明确上限，120积分 | **单次全量** | 256行/月度数据，无风险 |
| cn_ppi | 2005-01-01 | 未明确上限，120积分 | **单次全量** | 256行，无风险 |
| cn_m | 2005-01-01 | 未明确上限，120积分 | **单次全量** | 255行，无风险 |
| sf_month | 2005-01-01 | 未明确上限，120积分 | **单次全量** | 255行，无风险 |
| cn_pmi | 2005-01-01 | 未明确上限，120积分 | **单次全量** | 255行，无风险 |
| us_tycr | 2005-01-01 | **2000条/次**，120积分 | 120天/区间 | 日均1条 |
| us_trycr | 2005-01-01 | **2000条/次**，120积分 | 120天/区间 | 日均1条 |
| us_tbr | 2005-01-01 | **2000条/次**，120积分 | 120天/区间 | 日均1条 |
| us_tltr | 2005-01-01 | **2000条/次**，120积分 | 120天/区间 | 日均1条 |
| us_trltr | 2005-01-01 | **2000条/次**，120积分 | 120天/区间 | 日均1条 |

---

## 四、速率限制

| 接口 | 限速器 | 频率 | 实际调用量（全量） | 预估耗时 |
|------|--------|------|-------------------|---------|
| libor | **专用** | **150/min** | ~325 次（65区间×5币） | ~2 分钟 |
| shibor | 全局 | 300/min | ~65 次（120天分区） | <1 分钟 |
| shibor_quote | 全局 | 300/min | ~65 次 | <1 分钟 |
| shibor_lpr | 全局 | 300/min | ~22 次（365天分区） | <1 分钟 |
| hibor | 全局 | 300/min | ~65 次 | <1 分钟 |
| us_* (5个) | 全局 | 300/min | ~65 次/接口 | <5 分钟 |
| wz_index | 全局 | 300/min | 1 次 | <1 秒 |
| gz_index | 全局 | 300/min | 1 次 | <1 秒 |
| cn_* (6个) | 全局 | 300/min | 1 次/接口 | <6 秒 |

> **libor 频率说明**：libor 按 5 种货币循环拉取，调用量是其他利率接口的 5 倍（全量约 325 次），使用专用 `_LIBOR_LIMITER`（150/min）避免抢占全局配额。其余接口共享全局 `_RATE_LIMITER`（300/min）。

---

## 五、TDengine 建表注意事项

### 5.1 表结构总览

| 超级表 | 前缀 | 列数 | TAG | TAG长度 | 示例子表 |
|--------|------|------|-----|---------|---------|
| shibor | sb_ | 9 | type | NCHAR(20) | sb_SHIBOR |
| shibor_quote | sq_ | 18 | type | NCHAR(20) | sq_QUOTE |
| shibor_lpr | sl_ | 3 | type | NCHAR(20) | sl_LPR |
| libor | lb_ | 9 | curr_type | NCHAR(20) | lb_USD |
| hibor | hb_ | 9 | currency | NCHAR(20) | hb_HKD |
| wz_index | wz_ | 13 | type | NCHAR(20) | wz_WZ |
| gz_index | gz_ | 7 | type | NCHAR(20) | gz_GZ |
| cn_gdp | cg_ | 9 | type | NCHAR(20) | cg_GDP |
| cn_cpi | cc_ | 13 | type | NCHAR(20) | cc_CPI |
| cn_ppi | cp_ | 31 | type | NCHAR(20) | cp_PPI |
| cn_m | cm_ | 10 | type | NCHAR(20) | cm_M |
| sf_month | sf_ | 4 | type | NCHAR(20) | sf_SF |
| cn_pmi | pm_ | 60 | type | NCHAR(20) | pm_PMI |
| us_tycr | uy_ | 14 | type | NCHAR(20) | uy_TYCR |
| us_trycr | ur_ | 6 | type | NCHAR(20) | ur_TRYCR |
| us_tbr | ub_ | 13 | type | NCHAR(20) | ub_TBR |
| us_tltr | ul_ | 4 | type | NCHAR(20) | ul_TLTR |
| us_trltr | uu_ | 2 | type | NCHAR(20) | uu_TRLTR |

### 5.2 列映射修正记录

| 表 | 修正项 | 旧值（错误） | 新值（正确） |
|----|--------|------------|------------|
| libor | _TD_COLUMNS_MAP | 含 `curr_type` 列 | 移除（`curr_type` 为 TAG） |
| libor | _TD_COLUMNS_MAP | 缺 `2w` 列 | 补回 `2w` |
| libor | TAG 长度 | NCHAR(10) | NCHAR(20) |
| hibor | TAG 长度 | NCHAR(10) | NCHAR(20) |
| shibor_quote | 表结构 | `bank` 为 TAG | `bank` 为普通列，`type` 为 TAG |

### 5.3 旧表名清理

以下旧名称表已删除（结构与新 DDL 不兼容）：

| 旧表名 | 新表名 | 说明 |
|--------|--------|------|
| wz_interest | wz_index | 重命名 |
| gz_interest | gz_index | 重命名 |
| tb_rate | us_tbr | 结构完全不同，已废弃 |
| tb_rate_long | us_tltr | 结构完全不同，已废弃 |
| tb_rate_long_avg | us_trltr | 结构完全不同，已废弃 |

### 5.4 时间字段映射

三类不同的 API 时间格式，`td_utils.py` 均已处理：

| 格式 | 示例 | 来源接口 | TS转换结果 |
|------|------|---------|-----------|
| YYYYMMDD（8位） | `20250101` | shibor/libor/us_* 等 | `2025-01-01 00:00:00` |
| YYYYMM（6位） | `202501` | cn_cpi/cn_ppi/cn_m/sf_month/cn_pmi | `2025-01-01 00:00:00` |
| YYYYQn（季度） | `2024Q1` | cn_gdp | `2024-01-01 00:00:00` |

> **修复记录**：初版 `td_utils.py` 仅支持 YYYYMMDD 格式，月度(YYYYMM)和季度(YYYYQn)格式会输出 NULL。已在 `insert_dataframe_to_td` 和 `insert_dataframe_to_td_multi_tags` 中新增 6 位数字和 YYYYQn 格式转换逻辑。

### 5.5 大写列名处理

同步模板对所有 DataFrame 统一执行 `df.columns = [c.lower() for c in df.columns]` 确保匹配 `_TD_FIELD_MAP` 中的小写映射。

---

## 六、字段映射说明

### 6.1 GDP 季度映射

GDP 接口返回 `quarter` 字段（YYYYQn 格式），ts 映射规则：

| quarter | ts 结果 | 季度首日 |
|---------|---------|---------|
| 2024Q1 | 2024-01-01 | 1月1日 |
| 2024Q2 | 2024-04-01 | 4月1日 |
| 2024Q3 | 2024-07-01 | 7月1日 |
| 2024Q4 | 2024-10-01 | 10月1日 |

### 6.2 libor 币种标签

libor 按 5 种货币分子表存储，TAG 为 `curr_type`：

| 货币代码 | 子表名 | 说明 |
|---------|--------|------|
| USD | lb_USD | 美元 |
| EUR | lb_EUR | 欧元 |
| JPY | lb_JPY | 日元 |
| GBP | lb_GBP | 英镑 |
| CHF | lb_CHF | 瑞士法郎 |

### 6.3 shibor_quote 报价银行

`bank` 字段存储报价银行中文名称（如 工商银行、建设银行），`NCHAR(50)` 列。该字段在 API 中每行不同，必须为普通列而非 TAG。

---

## 七、特殊说明

### 7.1 libor/hibor 数据截止

libor 和 hibor 的 Tushare 数据截止于 2020-06-24。2020 年中以后 LIBOR 逐步退出历史舞台，替代利率（如 SOFR）Tushare 尚未接入。

### 7.2 wz_index/gz_index 数据范围

- wz_index（温州民间借贷利率）：2013-01-04 至 2023-03-08，Tushare 以不定期频率更新
- gz_index（广州民间借贷利率）：2013-04-18 至 2019-03-04，数据相对稀疏

### 7.3 LPR 非日频更新

shibor_lpr（LPR贷款基础利率）并非每日更新，Tushare 数据起始于 2013-10-25。使用 365 天 chunk 策略，单次返回约 20 行，远低于 4000 上限。

### 7.4 cn_gdp 积分要求较高

cn_gdp 需 600 积分，高于其他利率类接口的 120 积分，可能是限制因素。

### 7.5 wz_index/gz_index 积分要求

wz_index 和 gz_index 需 2000 积分，为 18 个接口中最高。首次同步前请确认 Tushare 账户积分达标。

---

## 八、依赖模块

```
src/utils/sync_utils.py                          # RateLimiter, get_logger_instance 等
src/utils/td_utils.py                            # TDengine 批量插入工具（insert_dataframe_to_td）
src/fetch_tushare_data/macro/                    # 18 个 fetch 接口实现
src/data_sync/full_sync/
└── sync_macro_data_bydate.py                    # 18 个宏观经济接口同步脚本
scripts/
├── sync_macro_data_all.sh                       # 全量同步（含清理重建）
└── sync_macro_data.sh                           # 按日期区间同步
src/batch/sql/tdengine/宏观经济.sql                # 18 个超级表 DDL
unit_test/
└── test_sync_macro_data.py                      # 24 个单元测试
```

---

## 九、Tushare 积分权限要求

| 接口 | 积分要求 | 单次最大 | 备注 |
|------|---------|---------|------|
| shibor | 120 | 2,000 条 | — |
| shibor_quote | 120 | 4,000 条 | — |
| shibor_lpr | 120 | 4,000 条 | — |
| libor | 120 | 4,000 条 | 2020年后停更 |
| hibor | 120 | 4,000 条 | 2020年后停更 |
| wz_index | **2,000** | 不限量 | 需要更高积分 |
| gz_index | **2,000** | 不限量 | 需要更高积分 |
| cn_gdp | 600 | 10,000 条 | 积分高于利率类 |
| cn_cpi | 120 | 未明确 | — |
| cn_ppi | 120 | 未明确 | — |
| cn_m | 120 | 未明确 | — |
| sf_month | 120 | 未明确 | — |
| cn_pmi | 120 | 未明确 | — |
| us_tycr | 120 | 2,000 条 | — |
| us_trycr | 120 | 2,000 条 | — |
| us_tbr | 120 | 2,000 条 | — |
| us_tltr | 120 | 2,000 条 | — |
| us_trltr | 120 | 2,000 条 | — |

---

## 十、踩坑记录

| 问题 | 现象 | 修复 |
|------|------|------|
| **itertuples 列名重命名** | shibor/libor/hibor 等表中 `1w`/`1m`/`3m` 等字段全部为 NULL | `td_utils.py` 三处 `getattr(row, name)` 改为 `row[pos]` 位置索引 |
| **月度/季度 ts 转换缺失** | cn_cpi/cn_gdp 等 6 张表 ts 列为 NULL | `td_utils.py` 新增 YYYYMM(6位)→YYYY-MM-01 和 YYYYQn→季度首日 转换 |
| **shibor_quote bank 错误为 TAG** | TDengine 表结构中 `bank` 列为 TAG，`type` TAG 缺失 | DROP 旧表，按 DDL 重建 |
| **libor 缺 2w 列** | `_TD_COLUMNS_MAP` 中的 `2w` 列被误删 | 补回 `2w` 到列映射 |
| **libor/hibor TAG NCHAR(10)** | NCHAR(10) 对插入代码生成的 19 字符日期串可能超长 | 改为 NCHAR(20) |
| **shibor 调用量过大** | chunk_days=15 导致 shibor 全量 ~521 次调用 | 扩至 chunk_days=120，调用降至 ~65 次 |
| **wz_index/gz_index 无效分片** | 不限量接口按 30 天分片，浪费 ~520 次调用 | 改为单次全量拉取 |
| **月度数据无效分片** | cn_cpi 等按 5 年窗口，浪费 ~5 次调用 | 改为单次全量拉取 |
| **旧表命名不统一** | wz_interest/gz_interest/tb_rate 与 DDL 命名不一致 | 删除旧表，按 DDL 命名重新创建 |


## 十一、数据质量（2026-05-18 探查）

### 数据概况

| 表 | 行数 | 子表数 | 时间范围 | 状态 |
|----|------|--------|---------|------|
| shibor | 4,873 | 1 | 2006-10-08 ~ 2026-05-14 | ✓ |
| shibor_quote | 4,369 | 1 | 2006-10-08 ~ 2026-05-14 | ✓ |
| shibor_lpr | 1,527 | 1 | 2013-10-25 ~ 2026-03-20 | ✓ |
| libor | 19,614 | 5 | 2005-01-03 ~ 2020-06-24 | ✓ (API 2020 年停更) |
| hibor | 3,522 | 1 | 2005-01-03 ~ 2020-06-24 | ✓ (API 2020 年停更) |
| wz_index | 2,324 | 1 | 2013-01-04 ~ 2023-03-08 | ✓ (不定期更新) |
| gz_index | 1,181 | 1 | 2013-04-18 ~ 2019-03-04 | ✓ (不定期更新) |
| cn_gdp | 84 | 1 | 2005-01-01 ~ 2025-10-01 | ✓ (季度) |
| cn_cpi | 256 | 1 | 2005-01-01 ~ 2026-04-01 | ✓ (月度) |
| cn_ppi | 256 | 1 | 2005-01-01 ~ 2026-04-01 | ✓ (月度) |
| cn_m | 255 | 1 | 2005-01-01 ~ 2026-03-01 | ✓ (月度) |
| sf_month | 255 | 1 | 2005-01-01 ~ 2026-03-01 | ✓ (月度) |
| cn_pmi | 255 | 1 | 2005-01-01 ~ 2026-03-01 | ✓ (月度) |
| us_tycr | 5,344 | 1 | 2005-01-03 ~ 2026-05-13 | ✓ |
| us_trycr | 5,342 | 1 | 2005-01-03 ~ 2026-05-13 | ✓ |
| us_tbr | 5,345 | 1 | 2005-01-03 ~ 2026-05-13 | ✓ |
| us_tltr | 5,343 | 1 | 2005-01-03 ~ 2026-05-13 | ✓ |
| us_trltr | 5,343 | 1 | 2005-01-03 ~ 2026-05-13 | ✓ |

### 总体结论

| 检查项 | 结果 |
|--------|------|
| 数据连续性 | ✓ 18 张表全部有数据，时间轴连续 |
| API 截断 | ✓ 日频接口 120 天一区间（~85条）远小于 2000 上限；月度/季度单次全量 |
| 数据重复 | ✓ TDengine 同子表+时间戳自动去重 |
| 字段 NULL | 未见大面积 NULL |
| 日期格式 | ✓ 统一正确（YMD/M/Q 三种格式均已适配） |
| 同一日期 | ✓ 无异常 |

### 已知限制（API 侧）

| 表 | 现象 | 说明 |
|----|------|------|
| libor | 停于 2020-06-24 | LIBOR 2020 年中退出，Tushare 未接入 SOFR |
| hibor | 停于 2020-06-24 | 同上 |
| wz_index | 停于 2023-03-08 | Tushare 不定期更新 |
| gz_index | 停于 2019-03-04 | Tushare 不定期更新 |
