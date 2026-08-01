# ETF专题数据同步指南

> 更新日期：2026-05-17 | 同步模块：`src/data_sync/full_sync/sync_etf_data_bydate.py`

---

## 一、接口总览（9 个）

### GreatSQL 入库（2 个）

| 接口 | 中文名称 | 表名 | 同步策略 | 数据量 | 最早日期 | 最晚日期 |
|------|---------|------|---------|--------|---------|---------|
| etf_basic | ETF基本信息 | etf_basic | 全量清表重建（TRUNCATE + INSERT） | 2,954 | 2005-02-23 | 2026-05-15 |
| etf_index | ETF基准指数 | etf_index | 全量清表重建（TRUNCATE + INSERT） | 1,495 | — | — |

### TDengine 入库（7 个）

| 接口 | 中文名称 | 表名 | 同步策略 | 数据量 | 最早日期 | 最晚日期 |
|------|---------|------|---------|--------|---------|---------|
| fund_daily | ETF日线行情 | fund_daily | 按 ts_code 循环，100只/批 | 1,158,916 | 2020-01-02 | 2026-05-15 |
| fund_adj | ETF复权因子 | fund_adj | 按 ts_code 循环，100只/批（2000条/次限制） | 1,162,983 | 2020-01-02 | 2026-05-15 |
| etf_share_size | ETF份额规模 | etf_share_size | 按 ts_code 循环，100只/批（显式指定 fields 含 nav/close） | 1,163,311 | 2020-01-02 | 2026-05-15 |
| etf_mins | ETF历史分钟(15min) | etf_mins | 按 ts_code × 日期分片循环（150天/片，8000条/次限制） | 19,774,179 | 2020-01-02 | 2026-05-15 |
| rt_min | ETF实时分钟 | rt_min | 按代码分批（10个/批），实时接口 | 0* | — | — |
| rt_etf_k | ETF实时日线 | rt_etf_k | 深市+沪市通配符批量拉取，实时接口 | 0* | — | — |
| rt_etf_sz_iopv | ETF实时参考净值 | rt_etf_sz_iopv | 全市场拉取（仅深市），实时接口 | 0* | — | — |

> \* 实时接口为零时快照，定时任务拉取后才有数据。
> **总计**：GreatSQL 4,449 行 + TDengine 23,259,389 行（1,518 只场内 ETF）

---

## 二、执行方式

### 2.1 Shell 脚本

```bash
# 基础数据全量（清表+重建，仅初次部署/数据重建时使用）
bash scripts/sync_etf_data_all.sh

# 历史行情按日期同步（日常增量）
bash scripts/sync_etf_data.sh                            # 全量 (2020-01-01 至今)
bash scripts/sync_etf_data.sh 20260401                   # 从指定日期至今
bash scripts/sync_etf_data.sh 20260401 20260430          # 指定日期范围
bash scripts/sync_etf_data.sh 20260506 20260507          # 增量 (非交易日返回0行)

# ETF分钟数据独立同步
bash scripts/sync_etf_mins.sh                            # 全量 5min
bash scripts/sync_etf_mins.sh 20260401 20260430 1min     # 指定日期+频率

# 单独重刷 etf_share_size（补齐 nav/close 字段）
bash scripts/resync_etf_share_size.sh                    # 全量 (2020-01-01 至今)
bash scripts/resync_etf_share_size.sh 20260401 20260430  # 指定日期范围
```

### 2.2 Python 直接调用

```python
from sync_etf_data_bydate import (
    sync_etf_basic, sync_etf_index,
    sync_fund_daily, sync_fund_adj, sync_etf_share_size,
    sync_stk_mins, sync_rt_etf_k, sync_rt_min, sync_rt_etf_sz_iopv,
)

# GreatSQL 基础数据（全量拉取，不传参）
sync_etf_basic()
sync_etf_index()

# TDengine 历史行情（全量）
sync_fund_daily()
sync_fund_adj()
sync_etf_share_size()
sync_stk_mins()                    # 默认 freq='5min'

# TDengine 增量（传日期参数）
sync_fund_daily(start_date="20260506", end_date="20260507")
sync_fund_adj(start_date="20260506", end_date="20260507")
sync_etf_share_size(start_date="20260506", end_date="20260507")
sync_stk_mins(start_date="20260506", end_date="20260507", freq="5min")

# 实时接口（拉取当日快照，不传日期）
sync_rt_etf_k()                    # 深市+沪市全量
sync_rt_min(freq="5MIN", ts_code="510050.SH,159919.SZ")
sync_rt_etf_sz_iopv()              # 深市全量
```

> **全量 vs 增量**：
> - **不传参数** → 使用默认起始日期（2020-01-01）全量拉取
> - **传 start_date/end_date** → 不删已有数据，仅追加新数据
> - **TDengine 自动去重**：同子表+时间戳唯一，重复 INSERT 自动跳过
> - **etf_basic/etf_index** → `sync_etf_data_all.sh` 先 TRUNCATE 清表再全量写入，确保数据干净

---

## 三、各接口起始日期与限制

| 接口 | 默认起始日期 | Tushare限制 | 说明 |
|------|-------------|------------|------|
| etf_basic | — | 5000条/次 | 全量拉取，当前约2954只ETF |
| etf_index | — | 5000条/次 | 全量拉取，当前约1495个指数 |
| fund_daily | 2020-01-01 | **5000条/次**，按 ts_code 循环 | 每只ETF约1500行（6年） |
| fund_adj | 2020-01-01 | **2000条/次**，按 ts_code 循环 | 每只ETF约1500行 |
| etf_share_size | 2020-01-01 | **5000条/次**，按 ts_code 循环 | 每只ETF约1500行 |
| etf_mins | 2020-01-01 | **8000条/次**，按 ts_code×freq 循环 | 5min频度约48行/天/只 |
| rt_min | 实时 | **1000条/次**，支持多代码 | 按10个/批分批拉取 |
| rt_etf_k | 实时 | 通配符支持 | 深市`1*.SZ` + 沪市`5*.SH` |
| rt_etf_sz_iopv | 实时 | **5000条/次**，仅深市 | 全市场一次拉取 |

---

## 四、速率限制

所有接口共享全局 `RateLimiter(300次/分钟)`，确保 Tushare API 不超限。

| 接口 | API限制 | 实际调用量（全量） | 预估耗时 |
|------|--------|-------------------|---------|
| fund_daily | 5000条/次 | ~1,518次（1518只ETF） | ~5分钟 |
| fund_adj | 2000条/次 | ~1,518次 | ~5分钟 |
| etf_share_size | 5000条/次 | ~1,518次 | ~5分钟 |
| etf_mins | 8000条/次 | ~1,518次 × 频率 | ~5分钟（单频率） |
| rt_min | 1000条/次 | ~150次（分批） | ~1分钟 |
| rt_etf_k | 通配符 | 2次（深+沪） | ~1秒 |
| rt_etf_sz_iopv | 5000条/次 | 1次 | ~1秒 |

---

## 五、TDengine 插入机制

### 5.1 子表+时间戳唯一

TDengine 超级表中，同一子表的相同时间戳 INSERT 会自动去重，**不会产生重复行**。增量更新无需先删后插。

### 5.2 批量插入优化

```python
# td_utils.insert_dataframe_to_td()
# 每个 ts_code 生成一条 INSERT ... USING ... TAGS (...) VALUES (...)
# 格式: INSERT INTO qmt_ai.ef_510050_SH USING fund_daily TAGS ('510050.SH') (ts, ...) VALUES (...)
```

### 5.3 子表命名规则

| 超级表 | 前缀 | 示例 |
|--------|------|------|
| fund_daily | ef_ | ef_510050_SH |
| fund_adj | ea_ | ea_510050_SH |
| etf_mins | en_ | en_510050_SH |
| etf_share_size | es_ | es_510050_SH |
| rt_min | em_ | em_510050_SH |
| rt_etf_k | er_ | er_510050_SH |
| rt_etf_sz_iopv | ei_ | ei_159919_SZ |

### 5.4 时间字段映射

| 接口 | API字段 | TDengine ts | 格式处理 |
|------|---------|-------------|---------|
| fund_daily | trade_date | ts | YYYYMMDD → YYYY-MM-DD 00:00:00 |
| fund_adj | trade_date | ts | 同上 |
| etf_share_size | trade_date | ts | 同上 |
| etf_mins | trade_time | ts | 直接使用 |
| rt_min | time | ts | 直接使用 |
| rt_etf_k | trade_time | ts | API未返回时补当前时间 |
| rt_etf_sz_iopv | trade_time | ts | 直接使用 |

### 5.5 列类型说明

| 表 | 特殊列 | 类型 | 说明 |
|----|--------|------|------|
| etf_mins | vol | BIGINT | ETF成交量可能超INT上限（21亿），使用BIGINT |
| fund_daily | vol, amount | DOUBLE | 成交量(手)、成交额(千元) |
| rt_etf_k | vol, amount | INT | 成交量(股)、成交金额(元) |

---

## 六、特殊说明

### 6.1 etf_basic — 不做日期过滤

`sync_etf_basic` 全量拉取所有上市 ETF（`list_status='L'`），**不按 list_date 过滤**。etf_basic 作为基础查表，需包含所有 ETF 代码，其后再按日期参数同步各 ETF 的历史行情。

### 6.2 .OF 场外代码过滤

`_get_etf_codes()` 自动过滤 `.OF` 场外基金代码，仅返回场内 ETF（`.SH`/`.SZ`），减少无效 API 调用。

### 6.3 实时接口不放入定时 Shell

rt_min、rt_etf_k、rt_etf_sz_iopv 为实时接口，拉取当前时刻快照，无历史回溯能力，不放入按日期循环的 `sync_etf_data.sh` 中。

### 6.4 etf_mins 与 stk_mins 分离

ETF 分钟数据使用独立的 `etf_mins` 超级表，不与股票 `stk_mins` 共用。二者字段一致但前缀不同（`en_` vs `n_`）。

### 6.5 rt_etf_k 时间戳兜底

rt_etf_k 接口的 `trade_time` 字段为可选输出，API 默认不返回。同步时若缺失则自动补齐当前时间，避免 TDengine 因 NULL ts 拒绝入库。

### 6.6 etf_share_size — 显式指定 fields 获取 nav/close

tushare `etf_share_size` 接口的 `nav`（基金份额净值）和 `close`（收盘价）为**非默认输出字段**，不传 `fields` 参数时 API 不返回这两列。`fetch_etf_share_size.py` 已显式指定 `fields="trade_date,ts_code,etf_name,total_share,total_size,nav,close,exchange"` 确保入库完整。若需补刷历史数据可使用 `bash scripts/resync_etf_share_size.sh`。

> **注意**：nav/close 数据 T+1/T+2 才完全就绪，当天及前一天可能为 NULL，属正常延迟。

---

## 七、依赖模块

```
src/utils/sync_utils.py                      # GreatSQL 工具（RateLimiter, insert_dataframe 等）
src/utils/td_utils.py                        # TDengine 批量插入工具（insert_dataframe_to_td）
src/fetch_tushare_data/etf/                  # 9个 fetch 接口实现
src/data_sync/full_sync/
└── sync_etf_data_bydate.py                  # 9个ETF接口同步脚本
scripts/
├── sync_etf_data_all.sh                     # 基础数据全量同步（含 TRUNCATE 清表）
├── sync_etf_data.sh                         # 历史行情按日期同步
├── sync_etf_mins.sh                         # ETF分钟数据独立同步
└── resync_etf_share_size.sh                 # 单独重刷 etf_share_size（补齐 nav/close）
```

---

## 八、Tushare 积分权限要求

| 接口 | 积分要求 | 备注 |
|------|---------|------|
| etf_basic | 8,000 | 5000条/次 |
| etf_index | 8,000 | 5000条/次 |
| fund_daily | 5,000+ | 5000条/次，8000分频次更高 |
| fund_adj | 600+ | 2000条/次，5000分以上频次更高 |
| etf_share_size | 8,000 | 5000条/次 |
| etf_mins | 在线开通 | 分钟权限需单独开通 |
| rt_min | 在线开通 | 实时权限需单独开通 |
| rt_etf_k | 在线开通 | 实时权限需单独开通 |
| rt_etf_sz_iopv | 在线开通 | 实时权限需单独开通 |

---

## 九、数据库分类原则

| 数据库 | 适用场景 | ETF数据中的体现 |
|--------|---------|----------------|
| **GreatSQL** | 基础信息、映射关系、不频繁变动的参考数据 | etf_basic（基本信息）、etf_index（基准指数映射） |
| **TDengine** | 时序数据、按时间轴查询、高频更新的行情/指标 | fund_daily（日线）、etf_mins（分钟）、etf_share_size（份额）等 |

---

## 十、数据质量（2026-05-17 探查）

### 10.1 总体结论

| 检查项 | 结果 |
|--------|------|
| 数据连续性 | ✓ 老牌 ETF 与交易日历完美对齐；159901.SZ 缺失 2021-03-10 一天 |
| API 截断 | ✓ 无截断风险，每只 ETF 最多 1,540 行，远小于单次 API 限制 |
| 数据重复 | ✓ GreatSQL 无重复；TDengine 同子表+时间戳自动去重，抽样验证无重复 |
| 字段 NULL | 见下方详表 |
| 日期格式 | ✓ GreatSQL 为 DATE 类型，TDengine 为 TIMESTAMP 类型，格式统一 |
| 同一日期 | ✓ 无异常，不存在某字段所有数据使用同一日期 |

### 10.2 字段 NULL 明细

| 表 | 字段 | NULL 率 | 说明 |
|----|------|---------|------|
| etf_basic | mgt_fee | 48.31% | `.OF` 场外代码 99.4% NULL，`.SH/.SZ` 场内 0% NULL，API 不返回场外费率 |
| etf_basic | index_code / index_name | 1.86% | 部分货币 ETF 无跟踪指数 |
| etf_basic | list_date | 0.17% | 少数待上市 ETF 无上市日期 |
| etf_index | adj_circle | 61.40% | 部分指数无调整周期，API 本身不返回 |
| etf_share_size | nav | 0.38% | T+1/T+2 延迟 + 个别跨境 ETF 净值晚更新 |
| etf_share_size | close | 0.68% | 同上 |
| etf_share_size | etf_name | 0.38% | 少量新上市 ETF 名称未就绪 |
| fund_daily | — | 0% | 无 NULL |
| fund_adj | — | 0% | 无 NULL |
| etf_mins | — | 0% | 无 NULL |

### 10.3 已知缺失

| ETF | 缺失日期 | 说明 |
|-----|----------|------|
| 159901.SZ（深证100ETF） | 2021-03-10 | 该日为正常交易日，其他 ETF 有数据，仅此 ETF 缺失 |

### 10.4 交叉校验

- fund_daily / fund_adj / etf_share_size 三表子表完全对齐（均为 1,518 只 ETF）
- 可使用 `trade_cal`（SSE）作为统一交易日判断依据，沪深两市交易日完全一致
