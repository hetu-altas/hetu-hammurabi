# 公募基金数据同步指南

> 更新日期：2026-05-17 | 同步模块：`src/data_sync/full_sync/sync_fund_data_bydate.py`

---

## 一、接口总览（7 个）

### GreatSQL 入库（3 个）

| 接口 | 中文名称 | 表名 | 同步策略 | 数据量 | 最早日期 | 最晚日期 |
|------|---------|------|---------|--------|---------|---------|
| fund_basic | 基金列表 | fund_basic | 按 market×status 分片（6片），INSERT IGNORE 去重 | 22,100 | — | — |
| fund_company | 基金管理人 | fund_company | 全量拉取，INSERT IGNORE 去重 | 15,279 | — | — |
| fund_manager | 基金经理 | fund_manager | 按 ts_code 批量（50只/批逗号拼接），INSERT IGNORE 去重 | 34,239 | — | — |

### TDengine 入库（4 个）

| 接口 | 中文名称 | 表名 | 同步策略 | ts 映射 | 备注 |
|------|---------|------|---------|---------|------|
| fund_nav | 基金净值 | fund_nav | 按 ts_code 循环，100只/批 | nav_date → ts | — |
| fund_div | 基金分红 | fund_div | 按 ts_code 循环，50只/批 | ex_date → ts | API 不支持 start_date/end_date，按代码拉全量后入库端过滤 ann_date |
| fund_share | 基金规模 | fund_share | 按 ts_code × 3年窗口循环，100只/批 | trade_date → ts | 单次 2000 条限制，按 3 年分片 |
| fund_portfolio | 基金持仓 | fund_portfolio | 按 ts_code 循环，100只/批 | end_date → ts | end_date 可能为空，入库前 dropna |

---

## 二、执行方式

### 2.1 Shell 脚本

```bash
# 基础数据全量（仅初次部署/数据重建，含全量清理）
bash scripts/sync_fund_data_all.sh

# 历史行情按日期同步（日常增量）
bash scripts/sync_fund_data.sh                            # 全量 (2020-01-01 至今)
bash scripts/sync_fund_data.sh 20260401                   # 从指定日期至今
bash scripts/sync_fund_data.sh 20260401 20260430          # 指定日期范围

# 独立脚本（按需单表同步）
bash scripts/sync_fund_div.sh                             # 基金分红
bash scripts/sync_fund_portfolio.sh                       # 基金持仓
```

### 2.2 Python 直接调用

```python
from sync_fund_data_bydate import (
    sync_fund_basic, sync_fund_company, sync_fund_manager,
    sync_fund_nav, sync_fund_div, sync_fund_share,
    sync_fund_portfolio,
)

# GreatSQL 基础数据（全量拉取，不传参）
sync_fund_basic()
sync_fund_company()
sync_fund_manager()

# TDengine 历史行情（全量）
sync_fund_nav()
sync_fund_div()
sync_fund_share()
sync_fund_portfolio()

# TDengine 增量（传日期参数）
sync_fund_nav(start_date="20260506", end_date="20260507")
sync_fund_share(start_date="20260506", end_date="20260507")
sync_fund_portfolio(start_date="20260101", end_date="20260430")
# 注意：fund_div 传入 start_date/end_date 仅在入库端过滤 ann_date，API 端仍按代码拉全量
sync_fund_div(start_date="20260506", end_date="20260507")
```

> **全量 vs 增量**：
> - **不传参数** → 使用默认起始日期（2020-01-01）全量拉取
> - **传 start_date/end_date** → 不删已有数据，仅追加新数据
> - **TDengine 自动去重**：同子表+时间戳唯一，重复 INSERT 自动跳过

---

## 三、各接口起始日期与限制

| 接口 | 默认起始日期 | Tushare限制 | 说明 |
|------|-------------|------------|------|
| fund_basic | — | **15000条/次**，按 market×status 分6片 | E/O × L/I/D，O/L 片可能触及上限 |
| fund_company | — | 一次全部 | 约 150+ 家管理人 |
| fund_manager | — | **5000条/次**，按 ts_code 批量50个/批 | 逗号拼接代码一次拉取 |
| fund_nav | 2020-01-01 | 按 ts_code 循环 | 每只基金约 1500 行（约6年） |
| fund_div | 2020-01-01 | 按 ts_code 循环 | API 仅支持四选一参数，不支持日期区间 |
| fund_share | 2020-01-01 | **2000条/次**，按 3 年分片 | 每只基金约 1500 行 |
| fund_portfolio | 2020-01-01 | 按 ts_code 循环 | 季度更新，每只基金约 20-80 行 |

---

## 四、速率限制

所有接口共享全局 `RateLimiter(300次/分钟)`。

| 接口 | 实际调用量（全量） | 预估耗时 |
|------|-------------------|---------|
| fund_basic | 6 次（6 片） | <1 分钟 |
| fund_company | 1 次 | <1 秒 |
| fund_manager | ~440 次（22000 基金 / 50） | ~1.5 分钟 |
| fund_nav | ~22,000 次 | ~73 分钟 |
| fund_div | ~22,000 次 | ~73 分钟 |
| fund_share | ~66,000 次（22000 × 3年分片） | ~220 分钟 |
| fund_portfolio | ~22,000 次 | ~73 分钟 |

---

## 五、TDengine 建表注意事项

### 5.1 NCHAR 列宽度

`td_utils.insert_dataframe_to_td()` 会对所有日期类字符串自动拼接 `" 00:00:00"` 变为 19 字符。**所有日期 NCHAR 列必须使用 `NCHAR(20)`**，否则报错 `Value too long for column`。

### 5.2 TAG 只能是标识列

TAG 只能放 `ts_code` 等每行不变的标识。类似 `ann_date` 这种每行值不同的字段必须放入普通列。错误放入 TAG 会导致 `Invalid column name: ts_code` 等错误。

### 5.3 三映射注册

新增 TDengine 超级表需在 `src/utils/td_utils.py` 的三个映射中注册：

```python
_TD_COLUMNS_MAP   # 列顺序定义（不含 ts_code）
_TD_FIELD_MAP     # 字段名映射（含 ts 源字段）
_TABLE_PREFIX     # 子表名前缀
```

### 5.4 ts 字段不可为空

`ts` 列（TIMESTAMP）不能为 NULL。入库前需对 ts 源字段（如 `ex_date`、`end_date`）做 `dropna` 过滤。

### 5.5 子表命名

| 超级表 | 前缀 | 示例 |
|--------|------|------|
| fund_nav | fn_ | fn_000001_OF |
| fund_div | fd_ | fd_000001_OF |
| fund_share | fs_ | fs_000001_OF |
| fund_portfolio | pf_ | pf_000001_OF |

---

## 六、特殊说明

### 6.1 fund_basic — 分片策略

单次 API 最大 15000 条。使用 `market(E/O) × status(L/I/D)` 共 6 片分次拉取。Tushare 的 `fund_basic` 仅支持 `ts_code/market/status` 三个筛选参数，`fund_type` 和 `type` 作为筛选参数静默无效，`ts_code` 不支持通配符。`market=O status=L` 一片接近 15000 上限，可能会有少量截断。

### 6.2 fund_manager — 批量优化

API 支持 `ts_code` 参数逗号分隔多只基金。改为每批 50 只代码批量调用（原来逐只调用），调用量从 N 降至 N/50。

### 6.3 fund_div — API 参数限制

Tushare `fund_div` API 仅接受 `ann_date`/`ex_date`/`pay_date`/`ts_code` 四选一作为必选参数，**不支持 `start_date`/`end_date`**。同步策略改为按 `ts_code` 循环拉全量，在入库端按 `ann_date` 做日期过滤。`ex_date`（除息日）可能为空，入库前 dropna。

### 6.4 fetch_fund_basic — status 参数后补

原始 `fetch_fund_basic` 未包含 `status` 参数。分片策略需要按 status 筛选，已为 `fetch_fund_basic` 新增 `status` 参数。

### 6.5 fund_nav — ann_date TAG 修正

原始 DDL 将 `ann_date` 定义为 TAG（TIMESTAMP 类型），但 `ann_date` 每行值不同，无法在 INSERT 时作为固定标签传入。已修正为普通列 `NCHAR(20)`，`ts_code` 为唯一 TAG。

---

## 七、依赖模块

```
src/utils/sync_utils.py                      # GreatSQL 工具（RateLimiter, insert_dataframe, clear_table 等）
src/utils/td_utils.py                        # TDengine 批量插入工具（insert_dataframe_to_td）
src/fetch_tushare_data/fund/                 # 7个 fetch 接口实现
src/data_sync/full_sync/
└── sync_fund_data_bydate.py                 # 7个基金接口同步脚本
scripts/
├── sync_fund_data_all.sh                    # 基础数据全量同步（含清理）
├── sync_fund_data.sh                        # 历史行情按日期同步
├── sync_fund_div.sh                         # 基金分红独立同步
├── sync_fund_div.sh                         # 基金分红独立同步
├── sync_fund_portfolio.sh                   # 基金持仓独立同步
└── resync_fund_fix.sh                        # 修复重跑（fund_company / fund_nav）
```

---

## 八、Tushare 积分权限要求

| 接口 | 积分要求 | 备注 |
|------|---------|------|
| fund_basic | 2,000+ | 15000条/次，5000分权限更高 |
| fund_company | 1,500+ | 一次全部 |
| fund_manager | 500+ | 5000条/次，2000分频率更高 |
| fund_nav | 2,000+ | 按 ts_code 或 nav_date |
| fund_div | 400+ | 四选一参数 |
| fund_share | 2,000+ | 2000条/次 |
| fund_portfolio | 5,000+ | 5000分每分钟200次 |

---

## 九、踩坑记录

| 问题 | 现象 | 修复 |
|------|------|------|
| fund_div 数据为 0 | API 报错 "必选其一" | 改为按 ts_code 循环，不加 start_date/end_date |
| ann_date 超长 | `Value too long for column` | NCHAR(10) → NCHAR(20) |
| ann_date 错配为 TAG | INSERT 语法错误 | 改为普通列 |
| ts 列为 NULL | `Primary timestamp column should not be null` | 入库前 dropna 过滤 ex_date/end_date |
| ts_code 误入列列表 | `Invalid column name: ts_code` | 补全 _TD_COLUMNS_MAP 显式定义 |
| fund_basic 超 15000 | 单次截断 | 按 market×status 分 6 片 |
| fund_manager 逐只调用慢 | 22000 次 API 调用 | 改为逗号拼接 50 只/批 |

---

## 十、数据质量（2026-05-17 探查）

### 10.1 数据概况

#### GreatSQL

| 表 | 行数 | 说明 |
|----|------|------|
| fund_basic | 22,100 | E/L:1,941 / E/D:614 / O/L:15,000 / O/D:4,043 / E/I:5 / O/I:497 |
| fund_company | 15,279 | 基金管理人信息 |
| fund_manager | 34,239 | 基金经理信息 |

#### TDengine

| 表 | 行数 | 子表数 | 时间范围 | 状态 |
|----|------|--------|---------|------|
| fund_nav | 13,147,305 | 20,248 | 2020-01-01 ~ 2026-05-15 | ✓ |
| fund_div | 12,530 | 3,289 | 2007-04-26 ~ 2026-05-13 | ✓ |
| fund_share | 1,501,389 | 18,926 | 2020-01-02 ~ 2026-05-08 | ✓ |
| fund_portfolio | 141,162 | 13,010 | 2019-12-31 ~ 2026-03-31 | ✓ |

### 10.2 总体结论

| 检查项 | 结果 |
|--------|------|
| 数据连续性 | ✓ fund_nav 20,248 子表正常，fund_share/fund_div/fund_portfolio 无缺失 |
| API 截断 | ⚠ fund_basic O/L 片恰好返回 15,000 条（API 上限），可能有数据被截断 |
| 数据重复 | ✓ GreatSQL 三表零重复；TDengine 同子表+时间戳自动去重 |
| 字段 NULL | ⚠ 多字段 100% NULL，详见下方 |
| 日期格式 | ✓ 统一正确 |
| 同一日期 | ✓ 无异常 |

### 10.3 需关注的问题（按严重度）

#### P0 — 未同步

| 问题 | 详情 | 方案 |
|------|------|------|
| **fund_nav 仅 1 行** | 表内只有 `fn_test2` 一条测试数据（2026-04-30），全量同步从未执行或失败。API 验证正常返回数据（000001.OF 返回 8 行） | 执行全量同步 `sync_fund_nav()` |

#### P0 — API 截断

| 问题 | 详情 | 方案 |
|------|------|------|
| **fund_basic O/L 片截断** | `market=O status=L` 返回恰好 15,000 条（API 上限），实际 O 类上市基金数量可能 > 15,000 | 对 O/L 片进一步按 `found_date` 年份拆分（如按年分段） |

#### P1 — 字段 100% NULL（API 非默认字段）

| 表 | 字段 | NULL 率 | 方案 |
|----|------|---------|------|
| fund_basic | exp_return | 100% | fetch 加 `fields` 参数 |
| fund_basic | trustee | 100% | fetch 加 `fields` 参数 |
| fund_company | short_enname | 100% | 已修复：fetch 加 `fields` 参数 |
| fund_div | earpay_date | 100% | 检查 API 列名是否匹配 |

#### P2 — 大面积 NULL（正常业务）

| 表 | 字段 | NULL 率 | 说明 |
|----|------|---------|------|
| fund_basic | delist_date | 97.2% | 大多数基金未退市 |
| fund_basic | duration_year | 98.8% | 有限期基金是少数 |
| fund_basic | list_date | 88.4% | 场外基金无上市日 |
| fund_basic | due_date | 78.9% | 多数基金无到期日 |
| fund_company | main_business | 96.7% | API 不返回 |
| fund_company | end_date | 99.6% | 正常运营中 |
| fund_company | manager | 85.4% | API 不返回 |
| fund_company | phone | 83.4% | API 不返回 |
| fund_company | website | 71.0% | API 不返回 |
| fund_manager | birth_year | 95.7% | 信息不完整 |
| fund_manager | end_date | 62.1% | 在职期间 |

### 10.4 已修复 / 待修复

| 问题 | 状态 | 方案 |
|------|------|------|
| fund_nav 仅 1 行测试数据 | **已修复** | `resync_fund_fix.sh` 全量重跑 → 13,147,305 行, 20,248 子表 |
| fund_company short_enname 100% NULL | **已修复** | `fetch_fund_company.py` 添加 `fields` 参数 + TRUNCATE 重跑 → 1269/15279 非NULL |
| fund_basic O/L 片 15000 = API 上限 | 已知限制 | API 无可再拆分维度，`sync_fund_basic` 已内置 ≥14900 警告 |
| fund_basic exp_return/trustee 100% NULL | 不可修 | API 侧本身返回 NULL，即使传 fields 也无法获取 |
