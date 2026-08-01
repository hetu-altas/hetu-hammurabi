# 财务数据同步指南

> 更新日期：2026-05-15 | 同步模块：`src/data_sync/full_sync/stock_data/sync_financial_data_bydate.py`

---

## 一、接口总览（10 个）

### TDengine 入库（7 个）

| 接口 | 中文名称 | 表名 | 同步策略 | 数据量 | 最早日期 | 最晚日期 |
|------|---------|------|---------|--------|---------|---------|
| income | 利润表 | income | 按 ts_code × report_type(1~12) × 全范围循环 | 1,555,538 | 2005-01-01 | 2026-05-04 |
| balancesheet | 资产负债表 | balancesheet | 按 ts_code × report_type(1~12) × 全范围循环 | 562,012 | 2005-01-01 | 2026-05-04 |
| cashflow | 现金流量表 | cashflow | 按 ts_code × report_type(1~12) × 全范围循环 | 1,490,887 | 2005-01-01 | 2026-05-04 |
| forecast | 业绩预告 | forecast | 按 ts_code × 全范围循环，100只/批 | 47,000 | 2005-01-01 | 2026-05-04 |
| express | 业绩快报 | express | 按半月日期区间循环（513个区间） | 29,505 | 2005-01-01 | 2026-05-04 |
| dividend | 分红送股 | dividend | 按 ts_code 循环，100只/批（不支持start/end） | 94,579 | 2005-01-01 | 2026-05-04 |
| fina_indicator | 财务指标 | fina_indicator | 按 ts_code × 5年窗口循环（100条/次限制），100只/批 | 244,000 | 2005-01-01 | 2026-05-04 |

### GreatSQL 入库（3 个）

| 接口 | 中文名称 | 表名 | 同步策略 | 数据量 | 最早日期 | 最晚日期 |
|------|---------|------|---------|--------|---------|---------|
| fina_audit | 财务审计意见 | fina_audit | 按 ts_code 循环，100只/批，REPLACE INTO | 83,568 | 2005-01-01 | 2026-05-04 |
| fina_mainbz | 主营业务构成 | fina_mainbz | 按 ts_code × type(P/D/I) × 5年窗口循环，30只/批，REPLACE INTO | 1,886,380 | 2005-01-01 | 2026-05-04 |
| disclosure_date | 财报披露日期 | disclosure_date | 按 ts_code 循环，100只/批（不支持start/end） | 281,344 | 2005-01-01 | 2026-05-04 |

> **总计**：TDengine 4,023,521 行 + GreatSQL 2,251,292 行 = **6,274,813 行**

---

## 二、执行方式

### 2.1 Shell 脚本（推荐）

```bash
# 全量同步（2005-01-01 至今）
bash scripts/resync_financial_fix.sh

# 日常增量同步
bash scripts/sync_financial_data.sh
```

### 2.2 Python 直接调用

```python
from sync_financial_data_bydate import sync_income, sync_dividend

# 全量：不传参
sync_income()

# 增量（start_date/end_date）：传日期参数
sync_income(start_date="20260430", end_date="20260504")
sync_balancesheet(start_date="20260430", end_date="20260504")
sync_cashflow(start_date="20260430", end_date="20260504")
sync_forecast(start_date="20260430", end_date="20260504")
sync_express(start_date="20260430", end_date="20260504")
sync_fina_indicator(start_date="20260430", end_date="20260504")
sync_fina_audit(start_date="20260430", end_date="20260504")
sync_fina_mainbz(start_date="20260430", end_date="20260504")

# dividend 和 disclosure_date 不支持 start_date/end_date，用 ann_date
sync_dividend(ann_date="20260430")
sync_disclosure_date(ann_date="20260430")
```

> **全量 vs 增量**：
> - **不传参数** → 使用默认起始日期（2005-01-01）全量拉取
> - **传 start_date/end_date** → 不删已有数据，仅追加新数据
> - **TDengine**：子表+时间戳唯一，同一子表相同 ts 的 INSERT 自动覆盖
> - **GreatSQL**：fina_audit/fina_mainbz 使用 REPLACE INTO + 唯一索引自动去重
> - **dividend/disclosure_date** → 使用 `ann_date` 参数

---

## 三、各接口起始日期与限制

| 接口 | 默认起始日期 | Tushare限制 | 说明 |
|------|-------------|------------|------|
| income | 2005-01-01 | ts_code 必选，**不传 report_type 默认只返回 type=1** | 需循环 report_type 1~12 |
| balancesheet | 2005-01-01 | ts_code 必选，同上 | 需循环 report_type 1~12（实际有效 1/4/5/6/9/10/11/12） |
| cashflow | 2005-01-01 | ts_code 必选，同上 | 需循环 report_type 1~12 |
| forecast | 2005-01-01 | ts_code 或 ann_date 二选一 | 每只股票~9行 |
| express | 2005-01-01 | ts_code 必选 | 每只股票约5行 |
| dividend | 2005-01-01 | 不支持 start/end，用 ann_date | 每只股票约17行 |
| fina_indicator | 2005-01-01 | **100条/次** | 需5年窗口分块 |
| fina_audit | 2005-01-01 | ts_code 必选 | 每只股票约5行 |
| fina_mainbz | 2005-01-01 | **100条/次**，按产品/地区/行业 | 需5年窗口分块 |
| disclosure_date | 2005-01-01 | 不支持 start/end，用 ann_date | 每只股票约20行 |

---

## 四、速率限制

所有接口共享全局 `RateLimiter(300次/分钟)`，确保 Tushare API 不超限。

| 接口 | API限制 | 实际调用量（全量） | 预估耗时 |
|------|--------|-------------------|---------|
| income | ts_code 必选 + report_type 循环 | ~66,144次 (12×5512股) | ~3.7小时 |
| balancesheet | ts_code 必选 + report_type 循环 | ~66,144次 | ~3.7小时 |
| cashflow | ts_code 必选 + report_type 循环 | ~66,144次 | ~3.7小时 |
| forecast | ts_code 必选 | 5,512次 | ~19分 |
| express | 半月日期区间 | 513次 | ~4分 |
| fina_indicator | **100条/次**, 5年分块 | ~27,560次 (5窗口×5512股) | ~92分 |
| fina_audit | ts_code 必选 | 5,512次 | ~19分 |
| fina_mainbz | **100条/次**, ×3类型×5窗口 | ~82,680次 | ~4.6小时 |
| dividend | 不支持 start/end | 5,512次 | ~19分 |
| disclosure_date | 不支持 start/end | 5,512次 | ~19分 |

> **全量同步耗时**：~12 小时（三大报表 report_type 循环占大头）

---

## 五、TDengine 插入机制

### 5.1 双 TAG 设计（income/balancesheet/cashflow）

Tushare API **不传 `report_type` 默认只返回 type=1（合并报表）**，必须显式传入 `report_type` 参数循环拉取全部 12 种报表类型。

为避免同 stock 同 ann_date 不同 report_type 互相覆盖，采用双 TAG：

```python
# TAGS (ts_code NCHAR(100), report_type NCHAR(10))
# 子表命名: {prefix}_{ts_code}_{report_type}
```

| 超级表 | 前缀 | 示例 |
|--------|------|------|
| income | pi_ | pi_000001_sz_1 (合并报表), pi_000001_sz_4 (调整合并) |
| balancesheet | bs_ | bs_000001_sz_1, bs_000001_sz_6 (母公司) |
| cashflow | cf_ | cf_000001_sz_1, cf_000001_sz_2 (单季合并) |

### 5.2 单 TAG 设计（forecast/express/dividend/fina_indicator）

| 超级表 | 前缀 | 示例 |
|--------|------|------|
| forecast | fc_ | fc_000001_sz |
| express | ex_ | ex_000001_sz |
| dividend | dv_ | dv_000001_sz |
| fina_indicator | fi_ | fi_000001_sz |

### 5.3 日期字段写入修复

`f_ann_date`、`end_date`、`record_date` 等 TIMESTAMP 列原本会将 YYYYMMDD 格式的浮点数直接当作毫秒时间戳写入（显示 `1970-01-01 13:34:10.112`），已通过 `_format_yyyymmdd()` 函数自动转换为 `YYYY-MM-DD 00:00:00`。

### 5.4 TIMESTAMP 范围

TDengine REST API 支持的时间戳范围为 **1995-01-01 至 2038-01-19**。早于 1995 年的记录会被自动过滤（`ann_date >= 20050101` 确保安全范围内）。

### 5.5 字符串转义

长文本字段（如 forecast 的 `summary`）中的单引号和反斜杠在插入前自动转义，截断至 200 字符。

---

## 六、GreatSQL 插入机制

### 6.1 REPLACE INTO（去重）

`fina_audit` 和 `fina_mainbz` 使用 `REPLACE INTO` + 唯一索引，避免重复累积：

| 表 | 唯一索引 |
|------|---------|
| fina_audit | `UNIQUE(ts_code, ann_date, end_date)` |
| fina_mainbz | `UNIQUE(ts_code, end_date, bz_item(100))` |

### 6.2 常规 INSERT

`disclosure_date` 使用 `INSERT INTO`，子表+时间戳唯一保证无重复。

---

## 七、特殊说明

### 7.1 income/balancesheet/cashflow — report_type 循环

Tushare API 规定 `report_type` 为可选参数，但**不传参时默认只返回 type=1**。必须显式传入 `report_type="2"` 等才能获取其他类型。因此每只股票需循环 12 次 API 调用。

balancesheet 实际只有 8 种 report_type 有数据（1/4/5/6/9/10/11/12），2/3/7/8 全市场无数据。

### 7.2 fina_indicator / fina_mainbz — 100条/次限制

采用 **5年窗口分块**：2005-2009, 2010-2014, 2015-2019, 2020-2024, 2025-2026。每只股票 5 次 API 调用，每次 ≤100 行。

### 7.3 forecast — ts_code 或 ann_date 二选一

Tushare 要求必须传入 `ts_code` 或 `ann_date` 之一。采用 ts_code 循环模式，数据稀疏（每只股票平均仅 ~9 条），无需额外分块。

### 7.4 dividend / disclosure_date — 不使用 start/end

这两个接口不支持 `start_date`/`end_date` 范围查询，改用 `ann_date` 单日参数。

### 7.5 express — 数据稀疏

express（业绩快报）远少于季度财报（~30k vs ~360k），按半月区间循环即可完成全量拉取。

---

## 八、依赖模块

```
src/utils/sync_utils.py                          # GreatSQL 工具（RateLimiter, insert_dataframe 等）
src/utils/td_utils.py                            # TDengine 批量插入工具（insert_dataframe_to_td / insert_dataframe_to_td_multi_tags）
src/fetch_tushare_data/stock_data/financial_data/ # 10个 fetch 接口实现
src/data_sync/full_sync/stock_data/
├── sync_financial_data_bydate.py                 # 10个财务数据接口同步脚本
scripts/
├── sync_financial_data.sh                        # Shell 脚本（日常增量）
└── resync_financial_fix.sh                       # 全量重建+修复脚本
```

---

## 九、Tushare 积分权限要求

| 接口 | 积分要求 | 备注 |
|------|---------|------|
| income | 2,000 | ts_code 必选 |
| balancesheet | 2,000 | ts_code 必选 |
| cashflow | 2,000 | ts_code 必选 |
| forecast | 2,000 | ts_code 或 ann_date 二选一 |
| express | 2,000 | ts_code 必选 |
| dividend | 2,000 | — |
| fina_indicator | 2,000 | 100条/次 |
| fina_audit | 2,000 | ts_code 必选 |
| fina_mainbz | 2,000 | 100条/次 |
| disclosure_date | 2,000 | — |

---

## 十、数据库分类原则

| 数据库 | 适用场景 | 财务数据中的体现 |
|--------|---------|----------------|
| **TDengine** | 以时间为轴、每日/每季更新、查询时按时间段筛选 | 三大报表、业绩预告/快报、分红、财务指标 |
| **GreatSQL** | 以实体ID为主键、含文本内容、关系型数据 | 审计意见、主营业务构成、财报披露日期 |

> 分类依据：阅读每个 Tushare 接口文档的输出字段和更新频率，根据数据是否具有清晰的时序特征（每日更新、有 trade_date/ann_date 可作为 ts）来判断。

---

## 十一、数据质量修复记录

> 更新日期：2026-05-15 | 全部已修复

### 11.1 API report_type 默认截断修复

**问题**：Tushare income/balancesheet/cashflow API 不传 `report_type` 时**默认只返回 type=1**，导致只拉取到合并报表数据（占比仅 ~16%）。

**修复**：
- 每只股票循环 `report_type` 1~12，显式传入各类型参数
- 因同一 stock+ann_date 存在多种 report_type，`report_type` 提升为 TAG（双 TAG 分表）
- 子表命名：`{prefix}_{ts_code}_{report_type}`，如 `pi_000001_sz_1`

### 11.2 TDengine 日期字段 1970 epoch 修复

**问题**：`f_ann_date`/`end_date` 等 TIMESTAMP 列中，YYYYMMDD 格式的浮点数被直接当作毫秒时间戳写入，显示为 `1970-01-01 13:34:10.112`。

**修复**：在 `td_utils.py` 中新增 `_format_yyyymmdd()` 函数，对所有非 ts 的 TIMESTAMP 日期列自动执行 YYYYMMDD → `YYYY-MM-DD 00:00:00` 转换。

### 11.3 GreatSQL fina_audit/fina_mainbz 大面积重复修复

**问题**：`INSERT INTO` 无唯一约束导致重复累积。修复前 fina_audit 32%重复（122,902→83,568）、fina_mainbz 43%重复（3,289,745→1,886,380）。

**修复**：
- `sync_utils.py`：`insert_dataframe` 新增 `replace=True` 支持 `REPLACE INTO`
- 迁移脚本：清理历史重复 + 添加唯一索引
- `fina_audit`：`UNIQUE(ts_code, ann_date, end_date)`
- `fina_mainbz`：`UNIQUE(ts_code, end_date, bz_item(100))`

### 11.4 全量重建步骤

```bash
cd hetu-mercury
bash scripts/resync_financial_fix.sh
```
