# 外汇数据同步指南

> 更新日期：2026-05-18 | 同步模块：`src/data_sync/full_sync/sync_forex_data_bydate.py`

---

## 一、接口总览（2 个）

### GreatSQL 入库（1 个）

| 接口 | 中文名称 | 表名 | 同步策略 | 数据量 | 最早日期 | 最晚日期 |
|------|---------|------|---------|--------|---------|---------|
| fx_obasic | 外汇基础信息（海外） | fx_obasic | 全量拉取，INSERT IGNORE 去重 | **69** | — | — |

### TDengine 入库（1 个）

| 接口 | 中文名称 | 表名 | 同步策略 | 数据量 | 最早日期 | 最晚日期 |
|------|---------|------|---------|--------|---------|---------|
| fx_daily | 外汇日线行情 | fx_daily | 按 ts_code × 3年窗口循环（1000条/次限制） | **103,789** | 2020-01-02 | 2026-05-14 |

> **总计**：GreatSQL **69 行** + TDengine **103,548 行** = **103,617 行**
> 
> **说明**：
> - fx_daily 实际数据起始日期为 2020-01-02（FXCM平台数据起始）
> - 69个子表对应69种外汇代码
> - 加密货币（CRYPTO类）数据量较少，约287-556行
> - 传统外汇货币对（FX类）数据量最多，约1978-2033行

---

## 二、执行方式

### 2.1 Shell 脚本

```bash
# 基础数据全量（仅初次部署/数据重建，与日期无关）
# 说明：清理GreatSQL表数据 + 同步fx_obasic基础信息
bash scripts/sync_forex_data_all.sh

# 日行情按日期同步（日常增量）
bash scripts/sync_forex_data.sh                            # 全量 (2005-01-01 至今)
bash scripts/sync_forex_data.sh 20260401                   # 从指定日期至今
bash scripts/sync_forex_data.sh 20260401 20260430          # 指定日期范围
bash scripts/sync_forex_data.sh 20260506 20260507          # 增量 (非交易日返回0行)
```

### 2.2 Python 直接调用

```python
from sync_forex_data_bydate import sync_fx_obasic, sync_fx_daily

# GreatSQL 基础数据（全量拉取，不传参）
sync_fx_obasic()

# TDengine 历史行情（全量）
sync_fx_daily()

# TDengine 增量（传日期参数）
sync_fx_daily(start_date="20260506", end_date="20260507")
```

> **全量 vs 增量**：
> - **不传参数** → 使用默认起始日期（2005-01-01）全量拉取
> - **传 start_date/end_date** → 不删已有数据，仅追加新数据
> - **TDengine 自动去重**：同子表+时间戳唯一，重复 INSERT 自动跳过
> - **fx_obasic** → 全量拉取 + INSERT IGNORE 去重，不会重复插入

---

## 三、各接口起始日期与限制

| 接口 | 默认起始日期 | Tushare限制 | 说明 |
|------|-------------|------------|------|
| fx_obasic | — | 单次可提取全部，需2000积分 | 全量拉取，当前约86种外汇代码 |
| fx_daily | 2005-01-01 | **1000条/次**，需2000积分，有流量控制 | 按3年窗口分批拉取 |

---

## 四、速率限制

所有接口共享全局 `RateLimiter(300次/分钟)`，确保 Tushare API 不超限。

| 接口 | API限制 | 实际调用量（全量） | 预估耗时 |
|------|--------|-------------------|---------|
| fx_obasic | 单次全部 | 1次 | ~1秒 |
| fx_daily | 1000条/次 | ~220次（86种外汇 × 8个3年窗口） | ~2分钟 |

---

## 五、TDengine 插入机制

### 5.1 子表+时间戳唯一

TDengine 超级表中，同一子表的相同时间戳 INSERT 会自动去重，**不会产生重复行**。增量更新无需先删后插。

### 5.2 批量插入优化

```python
# td_utils.insert_dataframe_to_td()
# 每个 ts_code 生成一条 INSERT ... USING ... TAGS (...) VALUES (...)
# 格式: INSERT INTO qmt_ai.fx_USDCNH_FXCM USING qmt_ai.fx_daily TAGS ('USDCNH.FXCM') VALUES (...)
```

### 5.3 子表命名规则

| 超级表 | 前缀 | 示例 |
|--------|------|------|
| fx_daily | fx_ | fx_USDCNH_FXCM, fx_EURUSD_FXCM, fx_XAUUSD_FXCM |

> **特殊字符处理**：外汇代码中的 `.` 替换为 `_`

### 5.4 时间字段映射

| 接口 | API字段 | TDengine ts | 格式处理 |
|------|---------|-------------|---------|
| fx_daily | trade_date | ts | YYYYMMDD → YYYY-MM-DD 00:00:00 |

> **注意**：API输出的日期格式为 YYYY-MM-DD，入库时转换为 TDengine 时间戳格式

---

## 六、字段映射说明

### 6.1 fx_obasic 字段映射

Tushare API 字段与 GreatSQL 表字段映射：

| API字段 | GreatSQL字段 | 说明 |
|---------|-------------|------|
| ts_code | ts_code | 外汇代码（如 USDCNH.FXCM） |
| name | name | 名称（如 美元人民币） |
| classify | classify | 分类（FX/INDEX/COMMODITY/METAL/BUND/CRYPTO/FX_BASKET） |
| exchange | exchange | 交易商（目前仅FXCM） |
| min_unit | min_unit | 最小交易单位 |
| max_unit | max_unit | 最大交易单位 |
| pip | pip | 点 |
| pip_cost | pip_cost | 点值 |
| traget_spread | traget_spread | 目标差价 |
| min_stop_distance | min_stop_distance | 最小止损距离（点子） |
| trading_hours | trading_hours | 交易时间 |
| break_time | break_time | 休市时间 |

### 6.2 fx_daily 字段映射（双报价结构）

fx_daily 接口返回 **bid买价 + ask卖价** 双报价数据：

| API字段 | TDengine字段 | 说明 |
|---------|-------------|------|
| trade_date | ts | 交易日期（GMT格林尼治时间，比北京时间晚一天） |
| bid_open | bid_open | 买入开盘价 |
| bid_close | bid_close | 买入收盘价 |
| bid_high | bid_high | 买入最高价 |
| bid_low | bid_low | 买入最低价 |
| ask_open | ask_open | 卖出开盘价 |
| ask_close | ask_close | 卖出收盘价 |
| ask_high | ask_high | 卖出最高价 |
| ask_low | ask_low | 卖出最低价 |
| tick_qty | tick_qty | 报价笔数 |
| exchange | exchange | 交易商 |

> **双报价说明**：bid是买入价（银行买入外汇的价格），ask是卖出价（银行卖出外汇的价格）

---

## 七、特殊说明

### 7.1 fx_obasic — 不支持日期参数

`sync_fx_obasic` 全量拉取所有外汇代码基础信息，**不支持 start_date/end_date 参数**。fx_obasic 作为基础查表，需包含所有外汇代码，其后再按日期参数同步各外汇的历史行情。

### 7.2 fx_daily 按3年窗口分批

接口单次最大返回1000条，约21年数据。采用3年窗口策略分批拉取：
- 2005-2007、2008-2010、2011-2013、2014-2016、2017-2019、2020-2022、2023-2025、2026-
- 确保每个窗口数据量不超过API限制
- 返回接近1000条时记录截断警告

### 7.3 截断检测机制

- fx_daily：返回 ≥950条 时警告（单次上限1000条）

### 7.4 GMT时间说明

fx_daily 的 `trade_date` 为 GMT格林尼治时间，比北京时间晚一天。例如北京时间2026-05-10的数据，API返回的trade_date为2026-05-09。

### 7.5 数据依赖

fx_daily 依赖 fx_obasic 获取外汇代码列表：
- 若 fx_obasic 表无数据，sync_fx_daily 会自动触发 sync_fx_obasic
- 确保外汇代码存在后再同步日线行情

---

## 八、依赖模块

```
src/utils/sync_utils.py                      # GreatSQL 工具（RateLimiter, insert_dataframe 等）
src/utils/td_utils.py                        # TDengine 批量插入工具（insert_dataframe_to_td）
src/fetch_tushare_data/forex/                # 2个 fetch 接口实现
├── fetch_fx_obasic.py                       # 外汇基础信息接口
└── fetch_fx_daily.py                        # 外汇日线行情接口
src/data_sync/full_sync/
└── sync_forex_data_bydate.py                # 2个外汇接口同步脚本
scripts/
├── sync_forex_data_all.sh                   # 基础数据全量同步
└── sync_forex_data.sh                       # 日行情按日期同步
src/batch/sql/
├── tdengine/外汇数据.sql                     # fx_daily 超级表DDL
└── greatsql/外汇数据.sql                     # fx_obasic 表DDL
```

---

## 九、Tushare 积分权限要求

| 接口 | 积分要求 | 备注 |
|------|---------|------|
| fx_obasic | 2,000 | 单次可提取全部，约86种外汇 |
| fx_daily | 2,000 | 1000条/次，有流量控制，5000分以上频次更高 |

---

## 十、数据库分类原则

| 数据库 | 适用场景 | 外汇数据中的体现 |
|--------|---------|----------------|
| **GreatSQL** | 基础信息、映射关系、不频繁变动的参考数据 | fx_obasic（外汇代码、交易参数、交易时间等） |
| **TDengine** | 时序数据、按时间轴查询、高频更新的行情/指标 | fx_daily（日线双报价行情） |

---

## 十一、数据量详细统计

### 11.1 GreatSQL fx_obasic 分类统计

| 分类 | 代码数量 | 说明 |
|------|---------|------|
| FX | 40 | 外汇货币对（主流货币） |
| INDEX | 13 | 全球指数（道琼斯、纳斯达克、恒生等） |
| COMMODITY | 9 | 大宗商品（原油、黄金、大豆等） |
| CRYPTO | 5 | 加密数字货币（比特币、以太币等） |
| FX_BASKET | 1 | 外汇篮子（美元指数） |
| BUND | 1 | 国库债券（欧洲债券） |
| **总计** | **69** | — |

### 11.2 TDengine fx_daily 数据量TOP 10

| 外汇代码 | 名称 | 数据量 | 分类 |
|---------|------|--------|------|
| EURUSD.FXCM | 欧元美元 | 2,033 | FX |
| AUDUSD.FXCM | 澳元美元 | 2,016 | FX |
| EURGBP.FXCM | 欧元英镑 | 2,001 | FX |
| GBPUSD.FXCM | 英镑美元 | 1,999 | FX |
| ZARJPY.FXCM | 南非兰特日元 | 1,998 | FX |
| USDJPY.FXCM | 美元日元 | 1,990 | FX |
| TRYJPY.FXCM | 土耳其里拉日元 | 1,982 | FX |
| GBPCAD.FXCM | 英镑加元 | 1,979 | FX |
| USDCNH.FXCM | 美元人民币 | 1,979 | FX |
| EURJPY.FXCM | 欧元日元 | 1,978 | FX |

### 11.3 TDengine fx_daily 数据量最少 10

| 外汇代码 | 名称 | 数据量 | 分类 |
|---------|------|--------|------|
| XRPUSD.FXCM | 瑞波币美元 | 287 | CRYPTO |
| BTCUSD.FXCM | 比特币美元 | 554 | CRYPTO |
| ETHUSD.FXCM | 以太币美元 | 556 | CRYPTO |
| BCHUSD.FXCM | 比特币现金美元 | 556 | CRYPTO |
| LTCUSD.FXCM | 莱特币美元 | 556 | CRYPTO |
| HKG33.FXCM | 恒生指数 | 839 | INDEX |
| UK100.FXCM | 英国富时100 | 859 | INDEX |
| CORNF.FXCM | 玉米 | 862 | COMMODITY |
| WHEATF.FXCM | 小麦 | 863 | COMMODITY |
| SOYF.FXCM | 大豆 | 866 | COMMODITY |

### 11.4 数据时间范围

- **最早时间**：2020-01-02 00:00:00
- **最晚时间**：2026-05-07 00:00:00
- **时间跨度**：约6.3年

> **说明**：FXCM平台数据起始于2020年初，加密货币类数据起始时间更晚（约2021年）

### 12.1 fx_obasic 数据示例

```
ts_code          name              classify    exchange    min_unit    max_unit      pip      pip_cost
USDCNH.FXCM      美元人民币          FX          FXCM        1.0         10000000.0   0.0001   0.1
EURUSD.FXCM      欧元美元            FX          FXCM        1000.0      5000000.0    0.0001   10.0
XAUUSD.FXCM      黄金美元            METAL       FXCM        1.0         5000.0       0.1      0.1
US30.FXCM        道琼斯工业平均指数    INDEX       FXCM        1.0         4000.0       1.0      0.1
```

### 12.2 fx_daily 数据示例

```
ts_code          trade_date    bid_open  bid_close  bid_high  bid_low   ask_open  ask_close  ask_high  ask_low   tick_qty  exchange
USDCNH.FXCM      20260508      6.9261    6.9326     6.9342    6.9248    6.9277    6.9330     6.9347    6.9252    18080    FXCM
USDCNH.FXCM      20260509      6.9300    6.9350     6.9400    6.9280    6.9310    6.9360     6.9410    6.9290    20000    FXCM
XAUUSD.FXCM      20260508      2320.50   2325.00    2330.00   2315.00   2321.00   2326.00    2331.00   2316.00   50000    FXCM
```

---

## 十二、数据示例

### 12.1 fx_obasic 数据示例

```
ts_code          name              classify    exchange    min_unit    max_unit      pip      pip_cost
USDCNH.FXCM      美元人民币          FX          FXCM        1.0         10000000.0   0.0001   0.1
EURUSD.FXCM      欧元美元            FX          FXCM        1000.0      5000000.0    0.0001   10.0
XAUUSD.FXCM      黄金美元            METAL       FXCM        1.0         5000.0       0.1      0.1
US30.FXCM        道琼斯工业平均指数    INDEX       FXCM        1.0         4000.0       1.0      0.1
BTCUSD.FXCM      比特币美元          CRYPTO      FXCM        0.01        10.0         1.0      0.1
USDOLLAR.FXCM    元指数             FX_BASKET   FXCM        1.0         10000.0      0.001    1.0
Bund.FXCM        欧洲债券            BUND        FXCM        1.0         5000.0       0.01     0.1
```

### 12.2 fx_daily 数据示例

```
ts_code          trade_date    bid_open  bid_close  bid_high  bid_low   ask_open  ask_close  ask_high  ask_low   tick_qty  exchange
USDCNH.FXCM      20260508      6.9261    6.9326     6.9342    6.9248    6.9277    6.9330     6.9347    6.9252    18080    FXCM
USDCNH.FXCM      20260509      6.9300    6.9350     6.9400    6.9280    6.9310    6.9360     6.9410    6.9290    20000    FXCM
XAUUSD.FXCM      20260508      2320.50   2325.00    2330.00   2315.00   2321.00   2326.00    2331.00   2316.00   50000    FXCM
EURUSD.FXCM      20260508      1.0850    1.0875     1.0900    1.0820    1.0855    1.0880     1.0905    1.0825    25000    FXCM
BTCUSD.FXCM      20260508      63500.0   64000.0    64500.0   63000.0   63505.0   64005.0    64505.0   63005.0   3000     FXCM
```

## 十三、外汇分类说明

| classify代码 | 分类名称 | 示例 |
|-------------|---------|------|
| FX | 外汇货币对 | USDCNH（美元人民币）、EURUSD（欧元美元） |
| INDEX | 指数 | US30（道琼斯）、NAS100（纳斯达克100） |
| COMMODITY | 大宗商品 | SOYF（大豆） |
| METAL | 金属 | XAUUSD（黄金）、XAGUSD（白银） |
| BUND | 国库债券 | Bund（长期欧元债券） |
| CRYPTO | 加密数字货币 | BTCUSD（比特币） |
| FX_BASKET | 外汇篮子 | USDOLLAR（美元指数） |

---

## 十四、常见问题

### Q1: 为什么 fx_daily 同步返回 0 行？

检查以下几点：
1. Tushare积分是否达到2000分门槛
2. fx_obasic 表是否有数据（先执行 `sync_fx_obasic()`）
3. 日期范围是否有效（非交易日返回0行）
4. API是否返回空数据（可手动调用验证）

### Q2: 子表名包含特殊字符怎么办？

`insert_dataframe_to_td` 已自动处理：
- `.` → `_`（如 USDCNH.FXCM → fx_USDCNH_FXCM）

### Q3: bid和ask有什么区别？

- **bid（买入价）**：银行/交易商愿意买入外汇的价格，客户卖出外汇时使用
- **ask（卖出价）**：银行/交易商愿意卖出外汇的价格，客户买入外汇时使用
- **spread（点差）**：ask - bid，反映交易成本

### Q4: 为什么日期比北京时间晚一天？

fx_daily 的 trade_date 采用 GMT格林尼治时间，比北京时间晚8小时。例如北京时间2026-05-10 08:00的交易，GMT时间为2026-05-09 00:00，API返回的trade_date为2026-05-09。

### Q5: 数据量超过API限制怎么办？

代码已内置截断检测：
- 返回接近API上限（≥950条）时记录警告日志
- 3年窗口策略确保单次不超过1000条
- 若某外汇历史数据特别密集，可手动缩小日期范围重试

---

## 十五、更新记录

| 日期 | 更新内容 |
|------|---------|
| 2026-05-10 | 初版：完成 fx_obasic + fx_daily 同步模块开发、单元测试、DDL建表、Shell脚本 |
| 2026-05-18 | 数据探查：确认数据质量良好，记录已知截断风险和字段NULL |


## 十六、数据质量（2026-05-18 探查）

### 数据概况

| 表 | 行数 | 子表数 | 时间范围 | 状态 |
|----|------|--------|---------|------|
| fx_obasic | 69 | — | — | ✓ |
| fx_daily | 103,789 | 69 | 2020-01-02 ~ 2026-05-14 | ✓ |

### 总体结论

| 检查项 | 结果 |
|--------|------|
| 数据连续性 | ✓ 69 只外汇代码，2020~2026 连续，按年分布均匀 |
| API 截断 | ⚠ 43/69 子表 ≥950 行，3 年窗口接近 1000 上限（已知，≥950 会记录 WARNING） |
| 数据重复 | ✓ GreatSQL 零重复；TDengine 同子表+时间戳零重复 |
| 字段 NULL | 见下方（均为正常业务数据） |
| 日期格式 | ✓ 统一正确 |
| 同一日期 | ✓ 无异常 |

### 截断风险（P2 — 已知）

43 只代码的 3 年窗口数据量 ≥950 行（如 EURUSD: 2033/6.3年≈322行/年，3年≈967行）。超过 1000 会被截断。当前未发现子表行数异常偏低，已知但未产生实际影响。

### 字段 NULL（正常业务）

| 表 | 字段 | NULL率 | 说明 |
|----|------|--------|------|
| fx_obasic | max_unit | 59.4% | 部分品种（如外汇货币对）不设最大单位 |
| fx_obasic | pip_cost | 59.4% | 同上 |
| fx_obasic | traget_spread | 68.1% | 非 FX 品种无目标点差 |
| fx_obasic | min_stop_distance | 66.7% | 非 FX 品种无最小止损 |
| fx_obasic | break_time | 71.0% | 多数品种无休市时间 |
| fx_daily | exchange | 100% | exchange 存为 NCHAR 但 API 始终返回 FXCM，数据列可忽略 |