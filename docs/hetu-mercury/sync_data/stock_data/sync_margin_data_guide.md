# 两融及转融通数据同步指南

> 更新日期：2026-05-05 | 同步模块：`src/data_sync/full_sync/stock_data/sync_margin_data_bydate.py`

---

## 一、接口总览（4 个）

### TDengine 入库（4 个）

| 接口 | 中文名称 | 表名 | 表类型 | 同步策略 | 当前行数 | 最早日期 | 最晚日期 |
|------|---------|------|--------|---------|---------|---------|---------|
| margin | 融资融券交易汇总 | margin | 超级表(tag=ts_code) | 半月区间循环 | 8,590 | 2010-03-31 | 2026-04-30 |
| margin_detail | 融资融券交易明细 | margin_detail | 超级表(tag=ts_code) | 按日区间循环 | 6,419,045 | 2010-03-31 | 2026-04-30 |
| margin_secs | 融资融券标的（盘前） | margin_secs | 超级表(tag=ts_code) | 3天区间循环 | 5,840,400 | 2010-03-29 | 2026-04-30 |
| slb_len | 转融资交易汇总 | slb_len | 普通表 | 半月区间循环 | 2,811 | 2014-01-02 | **2025-07-25** |

> **总计**：**12,270,846 行**（全部入 TDengine）
> 
> ⚠️ **slb_len 数据截至 2025-07-25**，之后无新数据（Tushare 可能已停更该接口）

---

## 二、执行方式

### 2.1 Python 直接调用

```python
from sync_margin_data_bydate import (
    sync_margin, sync_margin_detail,
    sync_margin_secs, sync_slb_len,
    run_all_sync,
)

# 全量（2005-01-01 至今）：不传参
sync_margin()
sync_slb_len()

# 增量：传 start_date/end_date（YYYYMMDD 格式）
sync_margin_detail(start_date="20260501", end_date="20260504")
sync_margin_secs(start_date="20260501")

# 串行执行全部 4 个接口
run_all_sync()
```

### 2.2 Shell 命令行

```bash
# 单独同步 slb_len
/venv-hetu/bin/python -c "
import sys; from pathlib import Path
_PROJECT = Path('/mnt/d/workspace/hetu-altas/hetu-mercury')
sys.path.insert(0, str(_PROJECT / 'src/utils'))
sys.path.insert(0, str(_PROJECT.parent / 'hetu-aether'))
sys.path.insert(0, str(_PROJECT / 'src/data_sync/full_sync/stock_data'))
sys.path.insert(0, str(_PROJECT / 'src/fetch_tushare_data/stock_data/margin_data'))
from sync_margin_data_bydate import sync_slb_len
print(sync_slb_len())
"
```

> **全量 vs 增量**：
> - **不传参数** → 使用默认起始日期 `2005-01-01` 全量拉取
> - **传 start_date/end_date** → 仅拉取指定区间数据
> - **TDengine 超级表自动去重**：同子表+时间戳唯一，重复 INSERT 自动跳过

---

## 三、各接口限制与策略说明

| 接口 | 单次最大 | 积分要求 | 日期区间策略 | 单日行数 | 策略原因 |
|------|---------|---------|-------------|---------|---------|
| margin | 4000行 | 2000分 | 半月区间 | ~3行 | 按 exchange_id 返回，日量极少 |
| margin_detail | 6000行 | 2000分 | **按日区间** | ~4,335行 | 接近6000上限，按日防截断 |
| margin_secs | 6000行 | 2000分 | **3天区间** | ~4,348行 | 3天≈13,000行理论值，保守3天≤6000 |
| slb_len | 5000行 | 2000分 | 半月区间 | — | 每日无增量数据（API 已停更） |

> **margin_detail 按日循环**已充分验证：单日最大 ~4,335 行，API 限制 6,000，安全余量 28%。

---

## 四、速率限制

所有接口共享全局 `RateLimiter(300次/分钟)`。

| 接口 | API 频率限制 | 实际调用量（全量） | 预估耗时 |
|------|------------|-------------------|---------|
| margin | 2000分起 | ~513次 (半月区间) | ~2分钟 |
| margin_detail | 2000分起 | ~5,000+次 (按日循环，含空数据日) | ~20分钟 |
| margin_secs | 2000分起 | ~1,300次 (3天×14年=1700区间) | ~5分钟 |
| slb_len | 2000分，200次/分钟 | ~513次 (半月区间) | ~2分钟 |

---

## 五、TDengine 表结构

### 5.1 超级表

| 超级表 | 前缀 | ts 来源 | tag 列 | 数据列 | 示例子表 |
|--------|------|---------|--------|--------|---------|
| margin | mg_ | trade_date→ts | ts_code(=exchange_id) | exchange_id, rzye, rzmre, rzche, rqye, rqmcl, rzrqye, rqyl | mg_SSE |
| margin_detail | md_ | trade_date→ts | ts_code | name, rzye, rqye, rzmre, rqyl, rzche, rqchl, rqmcl, rzrqye | md_000001_SZ |
| margin_secs | ms_ | trade_date→ts | ts_code | name, exchange | ms_000001_SZ |

### 5.2 普通表

| 表名 | ts 来源 | 列定义 |
|------|---------|--------|
| slb_len | trade_date→ts | ts, ob, auc_amount, repo_amount, repay_amount, cb |

### 5.3 列映射约定

- **所有表**：Tushare API 返回 `trade_date`(YYYYMMDD)，入库时统一重命名为 `ts`（TDengine TIMESTAMP）
- **margin 特殊处理**：API 返回 `exchange_id`（SSE/SZSE/BSE），同步时复制为 `ts_code` 用作超级表 tag，同时保留 `exchange_id` 作为数据列
- **slb_len**：普通表，表通过 REST API 手动创建（`DROP` → `CREATE`），列名与 API 完全一致

---

## 六、特殊说明

### 6.1 数据起始时间

- `margin` / `margin_detail`：Tushare 数据从 **2010-03-31** 开始
- `margin_secs`：数据从 **2014 年左右** 开始
- `slb_len`：数据从 **2014-06-20** 开始
- 2005-01-01 到数据起始日之间的区间 API 返回空，同步脚本自动跳过

### 6.2 margin_detail 按日循环

`margin_detail` 是数据量最大的接口，单日约 5000+ 条记录。API 单次限制 6000 行，因此必须按天循环（chunk_days=1），避免半月中 5000×15=75000 超出限制。

### 6.3 slb_len 表重建注意事项

`slb_len` 在 TDengine 中是**普通表**（非超级表）。如果表结构不对需要重建，使用 REST API：

```bash
# 删除旧表
curl -s -u 'qmt:Qmt@1895' 'http://localhost:6041/rest/sql' \
  -d 'DROP TABLE IF EXISTS qmt_ai.slb_len'

# 创建新表
curl -s -u 'qmt:Qmt@1895' 'http://localhost:6041/rest/sql' \
  -d 'CREATE TABLE IF NOT EXISTS qmt_ai.slb_len (ts TIMESTAMP, ob DOUBLE, auc_amount DOUBLE, repo_amount DOUBLE, repay_amount DOUBLE, cb DOUBLE)'
```

---

## 七、依赖模块

```
src/utils/sync_utils.py              # 通用工具（RateLimiter, insert_plain_table 等）
src/utils/td_utils.py                # TDengine 批量插入工具（insert_dataframe_to_td）
src/fetch_tushare_data/stock_data/margin_data/
├── fetch_margin.py                  # 融资融券交易汇总
├── fetch_margin_detail.py           # 融资融券交易明细
├── fetch_margin_secs.py             # 融资融券标的（盘前）
└── fetch_slb_len.py                 # 转融资交易汇总
src/data_sync/full_sync/stock_data/
└── sync_margin_data_bydate.py       # 4个两融及转融通接口同步脚本
```

---

## 八、Tushare 积分权限要求

| 接口 | 积分要求 | 频率限制 | 备注 |
|------|---------|---------|------|
| margin | 2,000 | — | 日频数据 |
| margin_detail | 2,000 | — | 日频数据 |
| margin_secs | 2,000 | 5000分无总量限制 | 盘前更新 |
| slb_len | 2,000 | 200次/分钟，5000分500次 | 转融通融资汇总 |
