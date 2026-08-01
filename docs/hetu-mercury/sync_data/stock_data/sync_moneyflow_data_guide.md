# 资金流向数据同步指南

> 更新日期：2026-05-05 | 同步模块：`src/data_sync/full_sync/stock_data/sync_moneyflow_data_bydate.py`

---

## 一、接口总览（8 个）

全部入 TDengine，每日盘后更新，`trade_date` 映射为 `ts`。

| # | 接口 | 中文名称 | 表名 | 同步策略 | 当前行数 | 最早日期 | 最晚日期 |
|---|------|---------|------|---------|---------|---------|---------|
| 1 | moneyflow | 个股资金流向 | moneyflow | 按 ts_code 循环 | 13,422,809 | 2010-02 | 2026-05-04 |
| 2 | moneyflow_ths | 个股资金流向（THS） | moneyflow_ths | 按 ts_code 循环 | 1,655,621 | -- | 2026-05-04 |
| 3 | moneyflow_dc | 个股资金流向（DC） | moneyflow_dc | 按 ts_code 循环 | 3,308,453 | 2023-09-11 | 2026-05-04 |
| 4 | moneyflow_cnt_ths | 板块资金流向（THS） | moneyflow_cnt_ths | 半月区间循环 | 148,284 | -- | 2026-05-04 |
| 5 | moneyflow_ind_ths | 行业资金流向（THS） | moneyflow_ind_ths | 半月区间循环 | 35,280 | ~2024-09 | 2026-05-04 |
| 6 | moneyflow_ind_dc | 板块资金流向（DC） | moneyflow_ind_dc | 按周区间循环 | 257,280 | -- | 2026-05-04 |
| 7 | moneyflow_mkt_dc | 大盘资金流向（DC） | moneyflow_mkt_dc | 半月区间循环 | 736 | 2016-02 | 2026-05-04 |
| 8 | moneyflow_hsgt | 沪深港通资金流向 | moneyflow_hsgt | 半月区间循环 | 2,696 | 2014-11-17 | 2026-05-04 |

> **总计**：**18,831,169 行**（全部入 TDengine）

---

## 二、执行方式

### 2.1 Shell 脚本（推荐）

```bash
# 全量同步（2005-01-01 至今）
bash scripts/sync_moneyflow_data.sh

# 从指定日期至今
bash scripts/sync_moneyflow_data.sh 20260401

# 指定日期范围（增量）
bash scripts/sync_moneyflow_data.sh 20260401 20260430
```

### 2.2 Python 直接调用

```python
from sync_moneyflow_data_bydate import (
    sync_moneyflow, sync_moneyflow_ths, sync_moneyflow_dc,
    sync_moneyflow_cnt_ths, sync_moneyflow_ind_ths,
    sync_moneyflow_ind_dc, sync_moneyflow_mkt_dc,
    sync_moneyflow_hsgt, run_all_sync,
)

# 全量：不传参
sync_moneyflow()
sync_moneyflow_hsgt()

# 增量：传 start_date/end_date（YYYYMMDD 格式）
sync_moneyflow_cnt_ths(start_date="20260501", end_date="20260504")
sync_moneyflow_ind_dc(start_date="20260501")

# 并行执行全部 8 个接口
run_all_sync()
```

> **全量 vs 增量**：
> - **不传参数** → 使用默认起始日期 `2005-01-01` 全量拉取
> - **传 start_date/end_date** → 仅拉取指定区间数据
> - **TDengine 超级表自动去重**：同子表+时间戳唯一，重复 INSERT 自动跳过

---

## 三、各接口限制与策略说明

| 接口 | 单次最大 | 积分要求 | 同步策略 | 策略原因 |
|------|---------|---------|---------|---------|
| moneyflow | 6000行 | 2000分 | 按 ts_code 循环 | 单股~3,750行(15年×250日)，<6000，无需日期分块 |
| moneyflow_ths | 6000行 | 6000分 | 按 ts_code 循环 | 同上，单股数据量在限额内 |
| moneyflow_dc | 6000行 | 5000分 | 按 ts_code 循环 | 数据从2023-09-11开始，单股~500行，远低于限额 |
| moneyflow_cnt_ths | 5000行 | 6000分 | **按周区间** | ~400板块×5交易日≈2,000行，<5000；半月可能超限(400×12=4800) |
| moneyflow_ind_ths | 5000行 | 6000分 | 半月区间 | ~90行业×11交易日≈990行，<5000；需额外传 `trade_date` 锚定参数 |
| moneyflow_ind_dc | 5000行 | 6000分 | **按周区间** | ~500板块×5交易日≈2,500行，<5000；DC板块数量多，缩小区间 |
| moneyflow_mkt_dc | 3000行 | 6000分 | 半月区间 | 每日仅1行，无超限风险；无 ts_code，用常量标识 "MKTDC" |
| moneyflow_hsgt | 300行 | 2000分 | 半月区间 | 每日仅1行，无超限风险；无 ts_code，用常量标识 "HSGT" |

---

## 四、速率限制

所有接口共享全局 `RateLimiter(300次/分钟)`。

| 接口 | API 频率限制 | 实际调用量（全量） | 预估耗时 |
|------|------------|-------------------|------|
| moneyflow | 2000分起 | ~5,500次 (1次/股) | ~18分钟 |
| moneyflow_ths | 6000分 | ~5,500次 (1次/股) | ~18分钟 |
| moneyflow_dc | 5000分 | ~5,500次 (1次/股) | ~18分钟 |
| moneyflow_cnt_ths | 6000分 | ~513次 (半月区间×21年) | ~2分钟 |
| moneyflow_ind_ths | 6000分 | ~513次 (半月区间×21年) | ~2分钟 |
| moneyflow_ind_dc | 6000分 | ~1,092次 (周区间×21年) | ~4分钟 |
| moneyflow_mkt_dc | 6000分 | ~513次 (半月区间×21年) | ~2分钟 |
| moneyflow_hsgt | 2000分 | ~513次 (半月区间×21年) | ~2分钟 |

> 8接口全量预估总耗时约 **3~5小时**（ts_code循环3个接口各~18分钟为瓶颈，其余5个各~2-4分钟）

---

## 五、TDengine 表结构

### 5.1 超级表（有 ts_code，6 个）

| 超级表 | 前缀 | ts 来源 | 子表示例 |
|--------|------|---------|---------|
| moneyflow | mf_ | trade_date → ts | mf_000001_SZ |
| moneyflow_ths | mt_ | trade_date → ts | mt_000001_SZ |
| moneyflow_dc | mw_ | trade_date → ts | mw_000001_SZ |
| moneyflow_cnt_ths | mb_ | trade_date → ts | mb_886041_TI |
| moneyflow_ind_ths | mi_ | trade_date → ts | mi_881267_TI |
| moneyflow_ind_dc | mj_ | trade_date → ts | mj_xxx_TI |

### 5.2 常量标识表（无 ts_code，2 个）

以下 2 个接口原始数据无 `ts_code` 列，同步脚本添加常量 `ts_code` 后按超级表写入：

| 超级表 | 前缀 | ts 来源 | 常量标识 | 子表 |
|--------|------|---------|---------|------|
| moneyflow_mkt_dc | mk_ | trade_date → ts | ts_code="MKTDC" | mk_MKTDC |
| moneyflow_hsgt | mh_ | trade_date → ts | ts_code="HSGT" | mh_HSGT |

### 5.3 列映射说明

- 所有表 `trade_date` 映射为 `ts`（TDengine 时间戳列）
- `ts_code` 列用作超级表 tag，不纳入数据列
- Tushare API 输出日期格式为 YYYY-MM-DD，`insert_dataframe_to_td` 自动转换为 TDengine TIMESTAMP

---

## 六、特殊说明

### 6.1 数据起始时间

- `moneyflow`：Tushare 数据从 **2010年** 开始
- `moneyflow_dc`：数据从 **2023-09-11** 开始
- `moneyflow_ind_ths`：实际数据从 **2024年9月** 左右开始
- `moneyflow_hsgt`：沪深港通数据从 **2014-11-17** 开始
- 2005-01-01 到数据起始日之间的区间 API 返回空，同步脚本自动跳过

### 6.2 moneyflow_ind_dc 按周循环

`moneyflow_ind_dc`（东方财富板块资金流向）同时包含行业、概念、地域三大类板块，每个交易日约 500 条记录。若用半月区间（11 交易日 × 500 ≈ 5,500 行），会超出 5,000 条限制。因此采用**按周区间**循环（5 交易日 × 500 ≈ 2,500 行），确保数据不丢失。

### 6.3 moneyflow_cnt_ths 按周循环

THS概念板块约 400~500 个，半月区间（12 交易日 × 400 ≈ 4,800 行）**接近或超出 5,000 上限**，存在数据截断风险。已改为**按周区间**循环（5 交易日 × 400 ≈ 2,000 行），完全安全。

### 6.4 moneyflow_ind_ths 需 trade_date 锚定参数

该接口在仅传 `start_date`/`end_date` 时可能返回空结果，需额外传递 `trade_date` 作为锚定参数（`use_trade_date=True`）。已验证传递双参数不会导致数据截断，完整返回日期范围内全部数据。

### 6.5 mkt_dc / hsgt 无 ts_code

`moneyflow_mkt_dc`（大盘资金流向）和 `moneyflow_hsgt`（沪深港通资金流向）是市场级别数据，原始返回无 `ts_code` 列。同步脚本自动添加常量标识（"MKTDC" / "HSGT"），使其兼容 `insert_dataframe_to_td` 的超级表写入机制。

### 6.6 mkt_dc 表结构修复

`moneyflow_mkt_dc` 超级表最初创建时缺少 `close_sh`、`pct_change_sh`、`close_sz`、`pct_change_sz`、`net_amount_rate` 等 9 个列，导致 `insert_dataframe_to_td` 插入全部失败（数据为0）。已通过 `DROP STABLE` + `CREATE STABLE` 重建，并重新同步。

### 6.7 异常日志

`_sync_mf_tscode` 和 `_sync_mf_date_range` 模板中，API 调用异常会被捕获且记录首条 WARNING 日志，避免静默失败。后续同类型异常不再重复记录。

---

## 七、依赖模块

```
src/utils/sync_utils.py                              # 通用工具（RateLimiter, get_db, get_logger_instance）
src/utils/td_utils.py                                # TDengine 批量插入工具（insert_dataframe_to_td）
src/fetch_tushare_data/stock_data/moneyflow_data/
├── fetch_moneyflow.py                               # 个股资金流向
├── fetch_moneyflow_ths.py                           # 个股资金流向（THS）
├── fetch_moneyflow_dc.py                            # 个股资金流向（DC）
├── fetch_moneyflow_cnt_ths.py                       # 板块资金流向（THS）
├── fetch_moneyflow_ind_ths.py                       # 行业资金流向（THS）
├── fetch_moneyflow_ind_dc.py                        # 板块资金流向（DC）
├── fetch_moneyflow_mkt_dc.py                        # 大盘资金流向（DC）
└── fetch_moneyflow_hsgt.py                          # 沪深港通资金流向
src/data_sync/full_sync/stock_data/
└── sync_moneyflow_data_bydate.py                    # 8个资金流向接口同步脚本
scripts/
└── sync_moneyflow_data.sh                           # Shell 脚本（全量/增量）
unit_test/
├── test_sync_moneyflow_data.py                      # 33个单元测试用例
└── test/
    └── test_sync_moneyflow_data_result.txt           # 测试结果（33/33 通过）
```

---

## 八、Tushare 积分权限要求

| 接口 | 积分要求 | 频率限制 | 备注 |
|------|---------|---------|------|
| moneyflow | 2,000 | — | 个股资金流向，数据从2010年开始 |
| moneyflow_ths | 6,000 | — | 同花顺个股资金流向 |
| moneyflow_dc | 5,000 | — | 东方财富个股资金流向，数据从2023-09-11开始 |
| moneyflow_cnt_ths | 6,000 | — | 同花顺概念板块资金流向 |
| moneyflow_ind_ths | 6,000 | — | 同花顺行业资金流向 |
| moneyflow_ind_dc | 6,000 | — | 东方财富板块资金流向（行业/概念/地域） |
| moneyflow_mkt_dc | 6,000 (120试用) | — | 东方财富大盘资金流向 |
| moneyflow_hsgt | 2,000 | 5000分:500次/分钟 | 沪深港通资金流向，单次最大仅300条 |

> 注意：`moneyflow_ths`、`moneyflow_cnt_ths`、`moneyflow_ind_ths`、`moneyflow_ind_dc`、`moneyflow_mkt_dc` 均需 5,000~6,000 积分方可正常调取。
