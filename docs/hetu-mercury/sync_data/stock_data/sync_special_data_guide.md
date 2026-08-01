# 股票特色数据同步指南

> 更新日期：2026-05-06 | 同步模块：`src/data_sync/full_sync/stock_data/sync_special_data_bydate.py`

---

## 一、接口总览（12 个）

### TDengine 入库（7 个）

| 接口 | 中文名称 | 表名 | 同步策略 | 入库行数 | 数据起始 | 耗时 |
|------|---------|------|---------|---------|---------|------|
| cyq_perf | 每日筹码及胜率 | cyq_perf | ts_code × 3年窗口，100只/批 | 8,905,925 | 2018 | 156分 |
| cyq_chips | 每日筹码分布 | cyq_chips | ts_code × 3月区间，逐只入库，price 为 TAG | 581,122,785 | 2018 | 390分 |
| ccass_hold | 中央结算系统持股统计 | ccass_hold | ts_code × 5年窗口，100只/批 | 2,063,556 | 2020 | 18分 |
| stk_auction_o | 股票开盘集合竞价 | stk_auction_o | ts_code × 2年窗口，100只/批 | 6,601,654 | 2020 | 41分 |
| stk_auction_c | 股票收盘集合竞价 | stk_auction_c | ts_code × 2年窗口，100只/批 | 6,326,469 | 2020 | 39分 |
| stk_nineturn | 神奇九转指标 | stk_nineturn | ts_code 循环，100只/批 | 7,122,585 | 2023 | 17分 |
| stk_ah_comparison | AH股比价 | stk_ah_comparison | ts_code × 5年窗口，100只/批 | 17,345 | 2025 | 16分 |

### GreatSQL 入库（5 个）

| 接口 | 中文名称 | 表名 | 同步策略 | 入库行数 | 数据起始 | 耗时 |
|------|---------|------|---------|---------|---------|------|
| report_rc | 券商盈利预测 | report_rc | 半月日期区间循环，REPLACE INTO | 372,151 | 2020 | 2分 |
| stk_factor_pro | 股票技术面因子(专业版) | stk_factor_pro | ts_code × 1年窗口，50只/批 | 7,347,628 | 2020 | — |
| ccass_hold_detail | 中央结算系统持股明细 | ccass_hold_detail | ts_code × 1年窗口，100只/批 | 49,146,471 | 2020 | 109分 |
| stk_surv | 机构调研数据 | stk_surv | ts_code × 1年窗口，REPLACE INTO | 187,617 | 2020 | 50分 |
| broker_recommend | 券商月度金股 | broker_recommend | 按月逐月循环 | 17,006 | 2020 | 0.1分 |

> **总计**：TDengine 612,159,052 行 + GreatSQL 57,070,873 行 = **669,229,925 行**
>
> 数据统一从 2020-01-01 开始同步。部分接口数据实际起始较晚（cyq_perf/chips 始于2018，stk_nineturn 始于2023，stk_ah_comparison 始于2025）。

---

## 二、执行方式

### 2.1 Shell 脚本

```bash
# 全量同步（2020-01-01 至今，全部13个接口）
bash scripts/sync_special_data.sh

# 指定日期范围
bash scripts/sync_special_data.sh 20240101 20260506

# 跳过已完成接口的增量脚本
bash scripts/sync_special_data_remain.sh
bash scripts/sync_special_data_v2.sh
bash scripts/sync_special_data_v3.sh
bash scripts/sync_special_data_v4.sh
```

### 2.2 Python 直接调用

```python
from sync_special_data_bydate import (
    sync_cyq_perf, sync_cyq_chips, sync_ccass_hold,
    sync_stk_auction_o, sync_stk_auction_c,
    sync_stk_nineturn, sync_stk_ah_comparison,
    sync_report_rc, sync_stk_factor_pro,
    sync_ccass_hold_detail, sync_stk_surv, sync_broker_recommend,
    run_all_sync,
)

# 全量（2020年至今）：不传参
sync_cyq_chips()

# 增量：传 start_date/end_date
sync_cyq_chips(start_date="20260501", end_date="20260506")
sync_broker_recommend(start_date="20260501")

# 并行执行全部 13 个接口
run_all_sync()
```

> **全量 vs 增量**：
> - **不传参数** → 使用默认起始日期（2020-01-01）全量拉取
> - **传 start_date/end_date** → 仅拉取指定区间数据
> - **GreatSQL 未做去重**：增量需注意避免重复插入
> - **TDengine 自动去重**：同子表+时间戳唯一，重复 INSERT 自动跳过

---

## 三、各接口限制与策略说明

| 接口 | 单次最大 | 积分要求 | 日期区间策略 | 策略原因 |
|------|---------|---------|-------------|---------|
| cyq_perf | 5000条 | 5000分 | **3年窗口** | 1行/只/天，3年≈750行，<5000 |
| cyq_chips | ~6000条(实测) | 5000分 | **3月窗口**，逐只入库 | ~75行/只/天，3月≈4500行，<6000。数据量极大需逐只释放内存 |
| ccass_hold | 5000条 | 8000分 | **5年窗口** | 1行/只/天，5年≈1250行，<5000 |
| ccass_hold_detail | 6000条 | 8000分 | **1年窗口** | 每只每天多行(席位级)，1年≈1500行，<6000 |
| stk_auction_o | 10000条 | 分钟权限 | **2年窗口** | 1行/只/天，2年≈500行，<10000 |
| stk_auction_c | 10000条 | 分钟权限 | **2年窗口** | 同上 |
| stk_nineturn | 10000条 | 6000分 | 不分块 | 1行/只/天，数据始于2023，总量≈750行，<10000 |
| stk_ah_comparison | 1000条 | 5000分 | **5年窗口** | 数据始于20250812，总量≈170行/只，<1000 |
| report_rc | 3000条 | 8000分 | **半月区间** | 按日期跨度(非ts_code)拉取，半月研报量<3000 |
| stk_factor_pro | 10000条 | 5000分 | **1年窗口** | 1行/只/天，261列宽表，1年≈250行，<10000 |
| stk_surv | 100条 | 5000分 | **1年窗口** | 每只调研记录少，活跃股年调研<100次 |
| broker_recommend | 1000条 | 6000分 | **逐月循环** | 仅支持 month(YYYYMM) 参数，每月≈300行 |

---

## 四、速率限制

全局 `RateLimiter(2000次/分钟)`，适用于高积分用户。

| 接口 | 单次返回 | 每只调用次数 | 全量调用量 | 预估耗时 |
|------|---------|------------|-----------|---------|
| cyq_perf | 5000 | 1次/只(3年) | ~5,500次 | 156分 |
| cyq_chips | 6000 | 32次/只(3月) | ~176,000次 | 390分 |
| ccass_hold | 5000 | 1次/只(5年) | ~5,500次 | 18分 |
| stk_auction_o | 10000 | 3次/只(2年) | ~16,500次 | 41分 |
| stk_auction_c | 10000 | 3次/只(2年) | ~16,500次 | 39分 |
| stk_nineturn | 10000 | 1次/只 | ~5,500次 | 17分 |
| stk_ah_comparison | 1000 | 1次/只(5年) | ~5,500次 | 16分 |
| stk_factor_pro | 10000 | 6次/只(1年) | ~33,000次 | — |
| ccass_hold_detail | 6000 | 6次/只(1年) | ~33,000次 | 109分 |
| stk_surv | 100 | 6次/只(1年) | ~33,000次 | 50分 |
| broker_recommend | 1000 | 1次/月 | ~75次 | <1分 |
| report_rc | 3000 | 1次/半月 | ~157次 | 2分 |

---

## 五、特殊说明

### 5.1 cyq_chips — 数据量极大，逐只入库防止 OOM

`cyq_chips` 接口返回每只股票每天的筹码分布（每个价位一行），单只股票数月数据可达数十万行。原实现将 50 只股票的数据积存后统一入库，导致内存溢出进程静默退出。

修改为逐只入库：每只股票拉取完 3 月区间数据后立即写入 TDengine 并释放内存。同时跳过 2018 年前的无效 API 调用。

### 5.2 TDengine 列名冲突

`stk_nineturn`、`stk_ah_comparison` 因 TDengine REST API 不支持通过 `INSERT ... USING` 自动建表，需先显式创建超表。

### 5.3 stk_factor_pro — 261列宽表

API 返回 261 个技术因子字段，远超原 GreatSQL 表 36 列定义。重建表结构以包含全部字段：

```sql
CREATE TABLE stk_factor_pro (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ts_code VARCHAR(20),
    trade_date VARCHAR(10),
    -- 253 个技术指标列 (DOUBLE)
    ...
    UNIQUE KEY uk_code_date (ts_code, trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
```

### 5.4 stk_surv — 文本字段超长

原表字段均为 `VARCHAR(100)`，`rece_place`、`fund_visitors` 等字段存在超长数据导致入库失败。修复：将文本类字段扩展为 TEXT/LONGTEXT。

### 5.5 broker_recommend — 仅支持 month 参数

该接口只接受 `month(YYYYMM)` 入参，不支持 `start_date`/`end_date`。同步函数内部将日期转换为月份列表逐月查询。

### 5.6 速率限制调整

初始 `RateLimiter(300次/分钟)`，在高积分用户场景下调整为 `2000次/分钟`，显著缩短总同步时间（cyq_chips 从预估 61h 降至约 6.5h）。

### 5.7 TDengine 超级表

| 超级表 | 前缀 | ts 来源 | 示例子表 |
|--------|------|---------|---------|
| cyq_perf | cp_ | trade_date | cp_000001_SZ |
| cyq_chips | cc_ | trade_date | cc_000001_SZ |
| ccass_hold | ch_ | trade_date | ch_605009_SH |
| stk_auction_o | ao_ | trade_date | ao_000001_SZ |
| stk_auction_c | ac_ | trade_date | ac_000001_SZ |
| stk_nineturn | nt_ | trade_date | nt_000001_SZ |
| stk_ah_comparison | ah_ | trade_date | ah_000001_SZ |

### 5.8 GreatSQL 表列定义

| 表名 | 列数 | 备注 |
|------|------|------|
| report_rc | 24 | 含 imp_dg、create_time 可选字段 |
| stk_factor_pro | 264 | 261个API字段 + id/ts_code/trade_date |
| ccass_hold_detail | 8 | 席位级持股明细 |
| stk_surv | 11 | 文本字段已扩展为 TEXT |
| broker_recommend | 5 | 月度金股，字段少 |

---

## 六、依赖模块

```
src/utils/sync_utils.py              # GreatSQL 工具（RateLimiter, insert_dataframe, get_db 等）
src/utils/td_utils.py                # TDengine 批量插入工具（insert_dataframe_to_td, 列映射）
src/fetch_tushare_data/stock_data/special_data/
├── fetch_report_rc.py               # 券商盈利预测
├── fetch_cyq_perf.py                # 每日筹码及胜率
├── fetch_cyq_chips.py               # 每日筹码分布
├── fetch_stk_factor_pro.py          # 股票技术面因子(专业版)
├── fetch_ccass_hold.py              # 中央结算系统持股统计
├── fetch_ccass_hold_detail.py       # 中央结算系统持股明细
├── fetch_stk_auction_o.py           # 股票开盘集合竞价
├── fetch_stk_auction_c.py           # 股票收盘集合竞价
├── fetch_stk_nineturn.py            # 神奇九转指标
├── fetch_stk_ah_comparison.py       # AH股比价
├── fetch_stk_surv.py                # 机构调研数据
└── fetch_broker_recommend.py        # 券商月度金股
src/data_sync/full_sync/stock_data/
└── sync_special_data_bydate.py      # 13个特色数据接口同步脚本
scripts/
├── sync_special_data.sh             # 全量 shell（13个接口）
├── sync_special_data_no_cyq_perf.sh # 跳过 cyq_perf（12个）
├── sync_special_data_remain.sh      # 跳过已完成 3 个（10个）
├── sync_special_data_v2.sh          # 跳过已完成 6 个（7个）
├── sync_special_data_v3.sh          # 跳过已完成 9 个（4个）
└── sync_special_data_v4.sh          # 跳过已完成 11 个（2个）
```

---

## 七、Tushare 积分权限要求

| 接口 | 积分要求 | 备注 |
|------|---------|------|
| report_rc | 8000分正式 | 120分试用(10次/天) |
| cyq_perf | 5000分 | 10000分以上 200000次/天 |
| cyq_chips | 5000分 | 15000分不限总量 |
| stk_factor_pro | 5000分 | 8000分以上 500次/分 |
| ccass_hold | 5000分 | 8000分以上 500次/分 |
| ccass_hold_detail | 8000分 | 300次/分 |
| stk_auction_o | 分钟权限 | 需开通股票分钟权限 |
| stk_auction_c | 分钟权限 | 同上 |
| stk_nineturn | 6000分 | 日线数据，21点更新 |
| stk_ah_comparison | 5000分 | 数据始于20250812 |
| stk_surv | 5000分 | 200次/分 |
| broker_recommend | 6000分 | 月度更新，1-3日更新当月 |
