# 期货数据同步指南

> 更新日期：2026-05-17 | 同步模块：`src/data_sync/full_sync/sync_futures_data_bydate.py`

---

## 一、接口总览（13 个）

### GreatSQL 入库（4 个）

| 接口 | 中文名称 | 表名 | 同步策略 | 数据量 | 最早日期 | 最晚日期 |
|------|---------|------|---------|--------|---------|---------|
| fut_basic | 合约信息 | fut_basic | 按交易所分片，TRUNCATE + INSERT | 10,923 | — | — |
| trade_cal | 交易日历 | trade_cal | 按交易所 × 日期区间 | 15,664 | 2015-01-01 | 2026-05-15 |
| fut_mapping | 主力与连续合约 | fut_mapping | 按 ts_code × 2年分片 | 260,376 | 2020-01-02 | 2026-05-15 |
| fut_weekly_detail | 品种交易周报 | fut_weekly_detail | 按半年度分片 | 22,323 | 2010 | 2020 |

> \* fut_weekly_detail 调试期间被清表，需重跑。全量预计 21,000+ 行，覆盖 2010~2020 约 475 周。

### TDengine 入库（9 个）

| 接口 | 中文名称 | 表名 | 同步策略 | 数据量 | 说明 |
|------|---------|------|---------|--------|------|
| fut_daily | 日线行情 | fut_daily | 按 2 天日期分片 | 867,140 | 2021-12-17 ~ 2026-05-15 |
| fut_weekly_monthly | 周/月线行情 | fut_weekly_monthly | 按 freq+日期分片 | 293,478 | 2020-01-03 ~ 2026-05-15 |
| ft_mins | 历史分钟行情 | ft_mins | 按 ts_code × 日期分片 | 0 | 未同步 |
| rt_fut_min | 实时分钟行情 | rt_fut_min | 按合约代码分批 | 0 | 实时接口 |
| fut_wsr | 仓单日报 | fut_wsr | 按交易日逐日循环 | 87,704 | 2020-01-02 ~ 2026-05-15 |
| fut_settle | 每日结算参数 | fut_settle | 按交易日逐日循环 | 388,323 | 2020-01-02 ~ 2026-05-15 |
| fut_holding | 每日持仓排名 | fut_holding | 按 fut_code × 3年分片 | 31,102 | 2020-01-02 ~ 2026-05-15 |
| index_daily | 南华期货指数 | index_daily | 按指数代码 × 年度分片 | 13,880,155 | 与指数专题共享表 |
| ft_limit | 合约涨跌停价格 | ft_limit | 按 5 天日期分片 | 1,113,238 | 2020-01-02 ~ 2026-05-15 |

> **总计**：GreatSQL 287,282+ 行 + TDengine 15,881,211 行

---

## 二、执行方式

### 2.1 Shell 脚本

```bash
# 基础数据全量（仅初次部署/数据重建，与日期无关）
bash scripts/sync_futures_data_all.sh

# 历史行情按日期同步（日常增量）
bash scripts/sync_futures_data.sh                            # 全量 (2005-01-01 至今)
bash scripts/sync_futures_data.sh 20260401                   # 从指定日期至今
bash scripts/sync_futures_data.sh 20260401 20260430          # 指定日期范围
bash scripts/sync_futures_data.sh 20260508 20260509          # 增量 (非交易日返回0行)

# 从 fut_weekly_detail 开始的剩余接口（跳过已完成的 trade_cal/fut_mapping/fut_daily）
bash scripts/sync_futures_data_rest.sh                       # 全量
bash scripts/sync_futures_data_rest.sh 20260501              # 从指定日期至今

# fut_weekly_monthly 独立同步
bash scripts/sync_fut_weekly_monthly.sh                      # 全量
bash scripts/sync_fut_weekly_monthly.sh 20260101 20260131    # 指定日期范围
```

### 2.2 Python 直接调用

```python
from sync_futures_data_bydate import (
    # GreatSQL
    sync_fut_basic, sync_trade_cal, sync_fut_mapping, sync_fut_weekly_detail,
    # TDengine
    sync_fut_daily, sync_fut_weekly_monthly, sync_ft_mins, sync_rt_fut_min,
    sync_fut_wsr, sync_fut_settle, sync_fut_holding,
    sync_index_daily, sync_ft_limit,
)

# === GreatSQL 基础数据 ===
# fut_basic 与日期无关，全量拉取
sync_fut_basic()

# trade_cal、fut_mapping、fut_weekly_detail 支持日期参数
sync_trade_cal(start_date="20260501", end_date="20260510")
sync_fut_mapping(start_date="20260501", end_date="20260510")
sync_fut_weekly_detail(start_date="20260501", end_date="20260510")

# === TDengine 历史行情 ===
# 全量（不传参，使用默认起始日期 2005-01-01）
sync_fut_daily()
sync_fut_weekly_monthly()
sync_fut_wsr()
sync_fut_settle()
sync_fut_holding()
sync_index_daily()
sync_ft_limit()

# 增量（传日期参数）
sync_fut_daily(start_date="20260508", end_date="20260509")
sync_fut_wsr(start_date="20260508", end_date="20260509")
sync_fut_holding(start_date="20260501", end_date="20260510")

# 历史分钟（需指定 freq）
sync_ft_mins(start_date="20260501", end_date="20260510", freq="5min")

# 实时分钟（不在 shell 中，手动调用）
sync_rt_fut_min(freq="5MIN", ts_codes="RB2510.SHF,CU2506.SHF")
```

> **全量 vs 增量**：
> - **不传参数** → 使用默认起始日期（2005-01-01）全量拉取
> - **传 start_date/end_date** → 不删已有数据，仅追加新数据
> - **TDengine 自动去重**：同子表+时间戳唯一，重复 INSERT 自动跳过
> - **fut_basic** → 全量拉取 + INSERT IGNORE 去重，不会重复插入

---

## 三、各接口日期参数与限制

| 接口 | 默认起始 | API 限制（单次） | 分片策略 | 预估调用次数 |
|------|---------|-----------------|---------|------------|
| fut_basic | — | 10000条 | 6交易所分片 | 6 次 |
| trade_cal | 2005-01-01 | — | 6交易所 × 日期区间 | 6 次 |
| fut_mapping | 2005-01-01 | 2000条 | ts_code × 2年 | ~2000 次 |
| fut_weekly_detail | 2010-01-01 | 4000条 | 半年度 start_week | ~33 次 |
| fut_daily | 2005-01-01 | 2000条 | 2天/片 | ~3800 次 |
| fut_weekly_monthly | 2005-01-01 | 6000条 | week:21天, month:60天 | ~500 次 |
| ft_mins | 2005-01-01 | 8000条 | ts_code × 日期分片 | 量大，单独执行 |
| fut_wsr | 2005-01-01 | 1000条 | 逐交易日 | ~5000 次 |
| fut_settle | 2005-01-01 | 1600条 | 逐交易日 | ~5000 次 |
| fut_holding | 2005-01-01 | 4000条 | fut_code × 3年 | ~700 次 |
| index_daily | 2005-01-01 | — | 6指数 × 年度 | ~120 次 |
| ft_limit | 2005-01-01 | 4000条 | 5天/片 | ~1500 次 |

---

## 四、速率限制

全局 `RateLimiter(max_calls_per_minute=300)` 控制所有 API 调用频率：

| 接口 | 单次时长(估) | 总调用次数 | 预计耗时 |
|------|-------------|-----------|---------|
| fut_basic | 0.2s | 6 | <1s |
| trade_cal | 0.2s | 6 | ~2s |
| fut_weekly_detail | 0.2s | 33 | ~10s |
| fut_daily | 0.3s | 3800 | ~20min |
| fut_weekly_monthly | 0.3s | 500 | ~3min |
| fut_mapping | 0.2s | 2000 | ~7min |
| fut_wsr | 0.2s | 5000 | ~17min |
| fut_settle | 0.3s | 5000 | ~25min |
| fut_holding | 0.2s | 700 | ~3min |
| index_daily | 0.2s | 120 | ~1min |
| ft_limit | 0.3s | 1500 | ~8min |

---

## 五、TDengine 表结构与插入机制

### 5.1 超级表命名

所有子表按 `{前缀}_{ts_code}` 格式自动创建（下划线替换 `.` 和 `-`）：

| 表名 | 前缀 | 示例 |
|------|------|------|
| fut_daily | `fu_` | `fu_RB2510_SHF` |
| fut_weekly_monthly | `fw_` | `fw_RB2510_SHF` |
| ft_mins | `fm_` | `fm_RB2510_SHF` |
| rt_fut_min | `fr_` | `fr_RB2510_SHF` |
| fut_wsr | `ws_` | `ws_RB` |
| fut_settle | `fs_` | `fs_RB2510_SHF` |
| fut_holding | `fh_` | `fh_RB` |
| index_daily | `id_` | `id_NHCI_NH` |
| ft_limit | `fl_` | `fl_RB2510_SHF` |

### 5.2 时间字段映射

| 表名 | API 源字段 | TDengine `ts` 字段 |
|------|-----------|-------------------|
| fut_daily | trade_date | YYYYMMDD → YYYY-MM-DD 00:00:00 |
| fut_weekly_monthly | trade_date | 同上 |
| ft_mins | trade_time | YYYY-MM-DD HH:MM:SS |
| rt_fut_min | time | YYYY-MM-DD HH:MM:SS |
| fut_wsr | trade_date | YYYYMMDD → YYYY-MM-DD 00:00:00 |
| fut_settle | trade_date | 同上 |
| fut_holding | trade_date | 同上 |
| index_daily | trade_date | 同上 |
| ft_limit | trade_date | 同上 |

### 5.3 NCHAR 列长度

所有日期类 NCHAR 列统一使用 NCHAR(20)，因 `td_utils` 插入代码会给日期字符串拼接 `00:00:00`，产生 19 字符长度。

---

## 六、特殊说明

### 6.1 API 参数名差异

| 接口 | 文档参数 | 实际有效参数 | fetch 函数参数 | 备注 |
|------|---------|-------------|---------------|------|
| fut_weekly_monthly | freq=W/M | freq=week/month | freq | 需传全小写单词 |
| fut_weekly_detail | start_date/end_date | start_week/end_week | —(sync直接调pro) | start_date 被 API 忽略 |
| rt_fut_min | ts_code | code | ts_code | API 返回 code 列，插入前重命名 |

### 6.2 不支持 start_date/end_date 的接口

`fut_wsr`、`fut_settle`、`fut_holding` 三个接口的 `start_date`/`end_date` 参数被 API 拒绝（错误：`trade_date,symbol参数不能都为空`）。需提供 `trade_date` 或 `symbol` 之一：

- **fut_wsr**/**fut_settle**：从 `trade_cal` 表获取交易日列表，逐日循环调用
- **fut_holding**：从 `fut_basic` 表获取 `fut_code`（品种代码），按品种 × 3年分片调用

### 6.3 分片策略注意事项

- **fut_daily**：`_generate_date_ranges` 已修复 off-by-one bug（`chunk_days=N` 产出 N 天区间，非 N+1）
- **fut_weekly_detail**：`start_week`/`end_week` 格式为 YYYYWW，配合 `strftime("%Y%U")` 生成
- **fut_holding**：使用 `fut_code`（如 RB、CU）非 `symbol`（如 RB2510）或 `ts_code`（如 RB2510.SHF），前者约 98 个，后者约 10000 个

### 6.4 截断检测

`fut_weekly_detail` 和 `fut_weekly_monthly` 在每批次返回 ≥3950/5950 行时输出 WARNING 日志，提示可能截断。

### 6.5 实时接口

`sync_rt_fut_min` 为实时接口，不在任何 shell 脚本中，需手动调用。`sync_ft_mins` 因数据量巨大（分钟级全量 × 20年），也不在 shell 中。

### 6.6 GreatSQL 表清理

`sync_futures_data_all.sh` 仅清理 `fut_basic` 表（唯一与日期无关的接口）。其余 GreatSQL 表（`trade_cal`、`fut_mapping`、`fut_weekly_detail`）通过日期参数增量更新。

---

## 七、依赖模块

```
src/
├── utils/
│   ├── sync_utils.py          # RateLimiter, get_db, insert_dataframe, clear_table
│   └── td_utils.py            # insert_dataframe_to_td, get_td
├── fetch_tushare_data/futures/
│   ├── fetch_fut_basic.py     # 合约信息
│   ├── fetch_trade_cal.py     # 交易日历
│   ├── fetch_fut_daily.py     # 日线行情
│   ├── fetch_fut_weekly_monthly.py  # 周/月线行情
│   ├── fetch_ft_mins.py       # 历史分钟
│   ├── fetch_rt_fut_min.py    # 实时分钟
│   ├── fetch_fut_wsr.py       # 仓单日报
│   ├── fetch_fut_settle.py    # 每日结算
│   ├── fetch_fut_holding.py   # 持仓排名
│   ├── fetch_fut_index_daily.py    # 南华指数
│   ├── fetch_fut_mapping.py   # 主力合约映射
│   ├── fetch_fut_weekly_detail.py  # 品种交易周报
│   └── fetch_ft_limit.py      # 涨跌停价格
├── data_sync/full_sync/
│   └── sync_futures_data_bydate.py  # 本模块
scripts/
├── sync_futures_data_all.sh
├── sync_futures_data.sh
├── sync_futures_data_rest.sh
├── sync_fut_weekly_monthly.sh
└── resync_futures_fix.sh                   # 修复重跑（fut_basic/fut_daily/fut_weekly_detail）
```

---

## 八、Tushare 积分权限要求

| 接口 | 积分要求 | 备注 |
|------|---------|------|
| fut_basic | ≥2,000 | 期货合约信息 |
| trade_cal | ≥2,000 | 期货交易日历 |
| fut_daily | ≥2,000 | 日线行情 |
| fut_weekly_monthly | — | 周/月线行情 |
| ft_mins | 120(试调) / 需单独开通 | 历史分钟行情 |
| rt_fut_min | 需单独开通 | 实时分钟行情 |
| fut_wsr | ≥2,000 | 仓单日报 |
| fut_settle | ≥2,000 | 每日结算参数 |
| fut_holding | ≥2,000 | 每日持仓排名 |
| index_daily | ≥2,000 | 南华期货指数 |
| fut_mapping | ≥2,000 | 主力与连续合约 |
| fut_weekly_detail | ≥600 | 品种交易周报 |
| ft_limit | ≥5,000 | 涨跌停价格 |

---

## 九、数据库分类原则

| 维度 | GreatSQL（4张表） | TDengine（9张表） |
|------|------------------|------------------|
| 数据类型 | 基础信息、映射关系 | 时序行情、分钟数据 |
| 更新频率 | 低频（日/周级） | 高频（日/分/实时） |
| 查询模式 | 点查询、关联查询 | 时间范围聚合查询 |
| 数据量 | 千~万级 | 百万~千万级 |
| 典型表 | fut_basic, trade_cal | fut_daily, ft_mins |

---

## 十、数据质量（2026-05-17 探查）

### 10.1 数据概况

#### GreatSQL

| 表 | 行数 | 说明 |
|----|------|------|
| fut_basic | 10,923 | 6 交易所，trade_time_desc 10708/10923 非NULL（已修复） |
| fut_mapping | 260,376 | 204 个合约，2020-01-02 ~ 2026-05-15 |
| fut_weekly_detail | 22,323 | 2010~2020 全覆盖（已修复） |

#### TDengine

| 表 | 行数 | 子表数 | 时间范围 | 状态 |
|----|------|--------|---------|------|
| fut_daily | 867,140 | 4,454 | 2021-12-17 ~ 2026-05-15 | ✓（已补 2023~2025） |
| fut_weekly_monthly | 293,478 | 5,138 | 2020-01-03 ~ 2026-05-15 | ✓ |
| fut_wsr | 87,704 | 73 | 2020-01-02 ~ 2026-05-15 | ✓ |
| fut_settle | 388,323 | 2,486 | 2020-01-02 ~ 2026-05-15 | ✓ |
| fut_holding | 31,102 | 71 | 2020-01-02 ~ 2026-05-15 | ✓ |
| ft_limit | 1,113,238 | 5,532 | 2020-01-02 ~ 2026-05-15 | ✓ |
| ft_mins | 0 | 0 | — | 未同步 |
| rt_fut_min | 0 | 0 | — | 实时接口 |

### 10.2 总体结论

| 检查项 | 结果 |
|--------|------|
| 数据连续性 | ✓ fut_daily 2021~2026 连续；fut_weekly_detail 2010~2020 全覆盖 |
| API 截断 | ⚠ fut_weekly_detail API 全量返回 4000 条（= 上限），需缩窄时间分片 |
| 数据重复 | ✓ 所有表零重复 |
| 字段 NULL | 见下方 |
| 日期格式 | ✓ 统一正确 |
| 同一日期 | ✓ 无异常 |

### 10.3 需关注的问题

#### P0

| 问题 | 详情 | 方案 |
|------|------|------|
| **fut_daily 缺失 2023~2025** | 2021:8372/2022:84373/2023:0/2024:0/2025:0/2026:3074。同步中断于 2022 年底 | `sync_fut_daily(start_date="20230101")` |
| **fut_weekly_detail 仅 2020 年** | 仅 1028 行，API 2010~2025 全量 4000 条（= 上限）被截断 | 按年度缩窄分片后全量重跑 |
| **ft_mins 空表** | 分钟数据从未同步，数据量巨大 | 按需决定是否同步 |

#### P1

| 表 | 字段 | NULL率 | 说明 |
|----|------|--------|------|
| fut_basic | trade_time_desc | 100% | API 非默认字段，显式 fields 后可返回 3512/3552 |
| fut_basic | multiplier | 93.69% | API 返回 NULL，无法修复 |
| fut_daily | exchange | 100% | 存为数据列但 API 不单独返回，应为 TAG 或可忽略 |

#### P2（正常业务 NULL）

| 表 | 字段 | NULL率 | 说明 |
|----|------|--------|------|
| fut_daily | open/high/low | 19.9% | 部分合约/非交易日无 OHLC |
| fut_weekly_monthly | end_date | 62.69% | 周线数据不返回 end_date |
| fut_wsr | pre_vol | 41.33% | 部分品种无前日数据 |

### 10.4 已修复/待修复

| 问题 | 状态 | 方案 |
|------|------|------|
| fut_basic trade_time_desc 100% NULL | **已修复** | `fetch_fut_basic.py` 加 `fields` → 10708/10923 非NULL |
| fut_daily 缺 2023~2025 | **已修复** | `resync_futures_fix.sh` 补跑 → 867,140 行 |
| fut_weekly_detail 仅 2020 年 | **已修复** | `resync_futures_fix.sh` 全量重跑 → 22,323 行（2010~2020） |
| fut_basic multiplier 93.69% NULL | 不可修 | API 返回 NULL |
| ft_mins 空表 | 按需 | 数据量巨大，按需决定 |
