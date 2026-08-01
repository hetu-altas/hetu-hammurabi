# 股票参考数据同步指南

> 更新日期：2026-05-16 | 同步模块：`src/data_sync/full_sync/stock_data/sync_reference_data_bydate.py`

---

## 一、接口总览（12 个）

### TDengine 入库（5 个）

| 接口 | 中文名称 | 表名 | 同步策略 | 当前行数 | 最早日期 | 最晚日期 |
|------|---------|------|---------|---------|---------|---------|
| stk_shock | 个股异常波动 | stk_shock | 按 ts_code 循环，100只/批 | 470 | 2026-03-03 | 2026-05-08 |
| stk_high_shock | 个股严重异常波动 | stk_high_shock | 按 ts_code 循环，100只/批 | 22 | 2026-02-09 | 2026-05-08 |
| stk_alert | 交易所重点提示证券 | stk_alert | 按 ts_code 循环，100只/批 | 2 | 2026-05-07 | 2026-05-07 |
| block_trade | 大宗交易 | block_trade | 按3天日期区间循环 | 186,563 | 2005-01-04 | 2026-05-08 |
| stk_holdertrade | 股东增减持 | stk_holdertrade | 按7天日期区间循环 | 80,667 | 2005-01-06 | 2026-05-15 |

### GreatSQL 入库（7 个）

| 接口 | 中文名称 | 表名 | 同步策略 | 当前行数 | 最早日期 | 最晚日期 |
|------|---------|------|---------|---------|---------|---------|
| share_float | 限售股解禁 | share_float | **1天日期区间** | 8,332,335 | 2005-01-21 | 2026-05-15 |
| top10_holders | 前十大股东 | top10_holders | 按 ts_code 循环，100只/批 | 1,557,768 | 2005-01-29 | 2026-04-30 |
| top10_floatholders | 前十大流通股东 | top10_floatholders | 按 ts_code 循环，100只/批 | 2,469,071 | 2005-01-29 | 2026-04-30 |
| pledge_stat | 股权质押统计数据 | pledge_stat | 按 ts_code 循环 + end_date 后置过滤 | 2,086,609 | 2014-03-07 | 2026-05-08 |
| pledge_detail | 股权质押明细 | pledge_detail | 按 ts_code 循环 + ann_date 后置过滤 | 186,535 | 2005-01-05 | 2026-05-09 |
| repurchase | 股票回购 | repurchase | 按半月日期区间循环 | 65,063 | 2005-06-17 | 2026-05-09 |
| stk_holdernumber | 股东人数 | stk_holdernumber | 按 ts_code 循环，100只/批 | 457,206 | 2002-06-28 | 2026-05-08 |

> **总计**：TDengine 267,724 行 + GreatSQL 15,154,587 行 = **15,422,311 行**

---

## 二、执行方式

### 2.1 Shell 脚本

```bash
# 全量同步 12 个接口（2005-01-01 至今）
bash scripts/stock_data/sync_reference_data.sh

# 指定日期范围
bash scripts/stock_data/sync_reference_data.sh 20250101 20260504

# share_float 清表 + 1天区间全量重跑（消除截断）
bash scripts/stock_data/resync_share_float.sh
bash scripts/stock_data/resync_share_float.sh 20220101 20241231

# share_float + stk_holdertrade 修复重跑（截断修复 + 字段补全）
bash scripts/stock_data/resync_reference_fix.sh
```

### 2.2 Python 直接调用

```python
from sync_reference_data_bydate import (
    sync_stk_shock, sync_block_trade, sync_share_float,
    sync_top10_holders, sync_repurchase, sync_stk_holdernumber,
    run_all_sync,
)

# 全量（2005年至今）：不传参
sync_share_float()
sync_block_trade()

# 增量：传 start_date/end_date
sync_block_trade(start_date="20260501", end_date="20260504")
sync_share_float(start_date="20260501")

# 并行执行全部 12 个接口
run_all_sync()
```

> **全量 vs 增量**：
> - **不传参数** → 使用默认起始日期全量拉取
> - **传 start_date/end_date** → 仅拉取指定区间数据
> - **GreatSQL 已启用 INSERT IGNORE**：增量自动跳过重复（需表有唯一键）
> - **TDengine 自动去重**：同子表+时间戳唯一，重复 INSERT 自动跳过

---

## 三、各接口限制与策略说明

| 接口 | 单次最大 | 积分要求 | 日期区间策略 | 策略原因 |
|------|---------|---------|-------------|---------|
| stk_shock | 1000条 | 6000分 | ts_code 循环 | start_date/end_date 必须搭配 ts_code |
| stk_high_shock | 1000条 | 需确认 | ts_code 循环 | 同上 |
| stk_alert | 1000条 | 需确认 | ts_code 循环 | 同上 |
| block_trade | 1000条 | 300分 | **3天区间** | 大盘每日200+笔，3天约600-900条，<1000 |
| stk_holdertrade | 3000条 | 2000分 | **7天区间** | 每日100+笔，7天约700-1400条，<3000 |
| share_float | 6000条 | 120分 | **1天区间** | 日均约400条，但部分日超过6000，1天已最细 |
| top10_holders | 未明确 | 2000分 | ts_code 循环 | 每季度10条/股，最大782条/股 |
| top10_floatholders | 未明确 | 需确认 | ts_code 循环 | 同上 |
| pledge_stat | 1000条 | 需确认 | ts_code 循环 + end_date过滤 | 仅支持 ts_code+end_date 参数，单股最大625条 |
| pledge_detail | 1000条 | 500分 | ts_code 循环 + ann_date过滤 | 仅支持 ts_code 参数，单股最大858条 |
| repurchase | 2000条 | 需确认 | 半月区间 | 回购事件较少，日频低 |
| stk_holdernumber | 3000条 | 600分 | ts_code 循环 | 每季度1次/股，最大427条/股 |

---

## 四、速率限制

所有接口共享全局 `RateLimiter(300次/分钟)`。

| 接口 | API限制 | 实际调用量（全量） | 预估耗时 |
|------|--------|-------------------|---------|
| stk_shock | 6000分起 | ~5,500次 (ts_code循环) | ~20分钟 |
| block_trade | 300分，每分钟限制 | ~2,600次 (3天×21年) | ~9分钟 |
| stk_holdertrade | 2000分，5000分以上无限制 | ~1,100次 (7天×21年) | ~4分钟 |
| share_float | 120分，5000分以上高频 | ~7,800次 (1天×21年) | ~26分钟 |
| top10_holders | 2000分，5000分以上高频 | ~5,500次 (ts_code循环) | ~20分钟 |
| pledge_detail | 500分 | ~5,500次 (ts_code循环) | ~20分钟 |
| 其他 | — | 数百~数千次 | 数分钟~数十分钟 |

---

## 五、特殊说明

### 5.1 share_float — 1天区间与残存截断

`share_float` 原按半月区间同步，但2017年起单月解禁量超出6000条API上限，导致每年恰好144,000行的全面截断。经过两次修复：
- **3天区间**（2026-05-16）：行数从 157万 → 523万，恢复约370万行
- **1天区间**（2026-05-16）：行数从 523万 → 833万，再恢复约310万行

当前仍有约174个交易日（约3%）返回恰好6000条，属Tushare API 6000条硬上限。因API不支持批量ts_code筛选和分页，完整补漏需逐股查询（174天×5500股≈96万次），成本过高。残存丢失量估计<0.5%。

`ann_date` 字段大量为空值（Tushare部分老数据未填公告日期），因此该表入 GreatSQL 而非 TDengine。

### 5.2 GreatSQL 去重机制

原同步未做去重，全量重跑或叠加增量会产生大面积重复数据。已做以下修复：
- **7张表全部建立唯一键**（`scripts/sql/add_unique_keys_reference_data.sql`）
- **同步脚本统一使用 `INSERT IGNORE`**，增量自动跳过重复
- **已清理历史重复数据** 697,753 行

各表唯一键：
| 表 | 唯一键 |
|---|------|
| share_float | (`ts_code`, `float_date`, `holder_name`) |
| top10_holders | (`ts_code`, `end_date`, `holder_name`) |
| top10_floatholders | (`ts_code`, `end_date`, `holder_name`) |
| pledge_stat | (`ts_code`, `end_date`) |
| pledge_detail | (`ts_code`, `ann_date`, `holder_name`, `pledge_amount`) |
| repurchase | (`ts_code`, `ann_date`, `proc`) |
| stk_holdernumber | (`ts_code`, `end_date`) |

### 5.3 stk_holdertrade — begin_date/close_date 字段修复

Tushare `stk_holdertrade` 接口中 `begin_date` 和 `close_date` 字段默认不返回（默认显示=N）。原 fetch 函数未显式指定 `fields` 参数，导致这两个字段100%为NULL。

已在 `fetch_stk_holdertrade.py` 中增加 `fields` 参数显式请求全部13个字段，重跑后 `begin_date` 97.0%有值，`close_date` 100.0%有值。

### 5.4 stk_shock/stk_high_shock/stk_alert — Tushare 新接口

这三个接口 `doc_id` 在 451-453，属于Tushare较晚上线的接口，数据仅覆盖2026年初至今：
- `stk_shock`：470行，2026-03-03 ~ 2026-05-08
- `stk_high_shock`：22行，2026-02-09 ~ 2026-05-08
- `stk_alert`：2行，2026-05-07 单日

历史数据不可得，属于Tushare数据源限制，非同步脚本缺陷。

`start_date`/`end_date` 参数必须搭配 `ts_code` 使用，单独传日期范围 API 返回空数据。

### 5.5 pledge_stat / pledge_detail — 无日期入参的接口

这两个接口不支持 `start_date`/`end_date` 参数：
- `pledge_stat` 仅支持 `ts_code` + `end_date`
- `pledge_detail` 仅支持 `ts_code`

同步时按 ts_code 拉取全部数据，通过 `date_filter_col` 参数在入库前过滤，确保只入库 `>= start_date` 的记录。

去重后单股最大记录数：`pledge_stat` 625条（<1000上限），`pledge_detail` 858条（<1000上限），暂无截断风险。

### 5.6 block_trade / stk_holdertrade — 日期区间细粒度切割

由于这两个接口单日数据量大，使用比半月更细的区间：
- `block_trade`：3天一区间（每天大宗交易 200+ 笔，3天约 600-900 条，<1000）
- `stk_holdertrade`：7天一区间（每天增减持 100+ 笔，7天约 700-1400 条，<3000）

### 5.7 字段NULL情况

以下字段NULL比率较高，均属Tushare源数据特征，非同步脚本缺陷：

| 表 | 字段 | NULL比例 | 原因 |
|---|------|------:|------|
| pledge_detail | is_release, release_date, is_buyback | ~50% | 质押未到期则为空，业务合理 |
| pledge_detail | end_date, p_total_ratio | ~40% | 同上 |
| repurchase | exp_date | 96% | Tushare源数据缺乏该字段 |
| repurchase | end_date, vol | ~40% | 回购进行中则为空 |
| stk_holdertrade | avg_price | 37% | 部分交易无均价 |
| top10_floatholders | hold_change | 30% | 早期数据缺此字段 |
| top10_holders | hold_float_ratio | 22% | 早期数据缺此字段 |

### 5.8 日期格式

- share_float：`ann_date`/`float_date` 为 `VARCHAR(10)`，存储 `YYYYMMDD` 格式
- 其余 6 个 GreatSQL 表：日期列为 `DATE` 类型，`YYYY-MM-DD` 格式
- TDengine 5 个表：`ts` 为 `TIMESTAMP` 类型

share_float 与其他表格式不一致（建表历史原因），不影响功能但需注意跨表查询。

### 5.9 TDengine 超级表

| 超级表 | 前缀 | ts 来源 | 示例子表 |
|--------|------|---------|---------|
| stk_shock | sk_ | trade_date | sk_000001_SZ |
| stk_high_shock | hs_ | trade_date | hs_000001_SZ |
| stk_alert | sa_ | start_date | sa_000001_SZ |
| block_trade | bt_ | trade_date | bt_000001_SZ |
| stk_holdertrade | ht_ | ann_date | ht_000001_SZ |

### 5.10 GreatSQL 表列定义

同步脚本中定义的列列表与数据库实际表结构一致，`ts_code` 在 TDengine 中为 TAG 而非普通列。

---

## 六、依赖模块

```
src/utils/sync_utils.py              # GreatSQL 工具（RateLimiter, insert_dataframe, safe_db_value 等）
src/utils/td_utils.py                # TDengine 批量插入工具（insert_dataframe_to_td）
src/fetch_tushare_data/stock_data/reference_data/
├── fetch_stk_shock.py               # 个股异常波动
├── fetch_stk_high_shock.py          # 个股严重异常波动
├── fetch_stk_alert.py               # 交易所重点提示证券
├── fetch_top10_holders.py           # 前十大股东
├── fetch_top10_floatholders.py      # 前十大流通股东
├── fetch_pledge_stat.py             # 股权质押统计
├── fetch_pledge_detail.py           # 股权质押明细
├── fetch_repurchase.py              # 股票回购
├── fetch_share_float.py             # 限售股解禁
├── fetch_block_trade.py             # 大宗交易
├── fetch_stk_holdernumber.py        # 股东人数
└── fetch_stk_holdertrade.py         # 股东增减持
src/data_sync/full_sync/stock_data/
└── sync_reference_data_bydate.py    # 12个参考数据接口同步脚本
scripts/stock_data/
├── sync_reference_data.sh           # 全量 shell 脚本（12个接口）
├── resync_share_float.sh            # share_float 清表+1天区间重跑
└── resync_reference_fix.sh          # share_float + stk_holdertrade 修复重跑
scripts/sql/
└── add_unique_keys_reference_data.sql # 7表去重 + 建唯一键 DDL
```

---

## 七、Tushare 积分权限要求

| 接口 | 积分要求 | 备注 |
|------|---------|------|
| stk_shock | 6,000 | 日频数据，2026年3月起有数据 |
| stk_high_shock | 需确认 | 严重异常波动（极少） |
| stk_alert | 需确认 | 重点提示证券（极少） |
| top10_holders | 2,000 | 5000分以上频次更高 |
| top10_floatholders | 需确认 | — |
| pledge_stat | 需确认 | — |
| pledge_detail | 500 | — |
| repurchase | 需确认 | — |
| share_float | 120 | 5000分以上频次更高，每分钟限制 |
| block_trade | 300 | 每分钟限制，5000分以上频次更高 |
| stk_holdernumber | 600 | 基础100次/分钟，5000分以上频次更高 |
| stk_holdertrade | 2,000 | 5000分以上无限制 |
