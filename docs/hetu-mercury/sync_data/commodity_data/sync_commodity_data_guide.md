# 现货数据同步指南

> 更新日期：2026-05-17 | 同步模块：`src/data_sync/full_sync/sync_commodity_data_bydate.py`

---

## 一、接口总览（2 个）

### GreatSQL 入库（1 个）

| 接口 | 中文名称 | 表名 | 同步策略 | 数据量 | 最早日期 | 最晚日期 |
|------|---------|------|---------|--------|---------|---------|
| sge_basic | 上海黄金基础信息 | sgt_basic | 全量拉取，INSERT IGNORE 去重 | 13 | 2002-10-30 | — |

### TDengine 入库（1 个）

| 接口 | 中文名称 | 表名 | 同步策略 | 数据量 | 最早日期 | 最晚日期 |
|------|---------|------|---------|--------|---------|---------|
| sge_daily | 上海黄金现货日行情 | sge_daily | 按半月日期区间循环（2000条/次限制） | 18,780 | 2005-01-04 | 2026-05-15 |

> **总计**：GreatSQL 13 行 + TDengine 18,780 行（47 个合约）

---

## 二、执行方式

### 2.1 Shell 脚本

```bash
# 基础数据全量（仅初次部署/数据重建，与日期无关）
# 说明：清理GreatSQL表数据 + 同步sge_basic基础信息
bash scripts/sync_commodity_data_all.sh

# 日行情按日期同步（日常增量）
bash scripts/sync_commodity_data.sh                            # 全量 (2005-01-01 至今)
bash scripts/sync_commodity_data.sh 20260401                   # 从指定日期至今
bash scripts/sync_commodity_data.sh 20260401 20260430          # 指定日期范围
bash scripts/sync_commodity_data.sh 20260506 20260507          # 增量 (非交易日返回0行)
```

### 2.2 Python 直接调用

```python
from sync_commodity_data_bydate import sync_sge_basic, sync_sge_daily

# GreatSQL 基础数据（全量拉取，不传参）
sync_sge_basic()

# TDengine 历史行情（全量）
sync_sge_daily()

# TDengine 增量（传日期参数）
sync_sge_daily(start_date="20260506", end_date="20260507")
```

> **全量 vs 增量**：
> - **不传参数** → 使用默认起始日期（2005-01-01）全量拉取
> - **传 start_date/end_date** → 不删已有数据，仅追加新数据
> - **TDengine 自动去重**：同子表+时间戳唯一，重复 INSERT 自动跳过
> - **sge_basic** → 全量拉取 + INSERT IGNORE 去重，不会重复插入

---

## 三、各接口起始日期与限制

| 接口 | 默认起始日期 | Tushare限制 | 说明 |
|------|-------------|------------|------|
| sge_basic | — | **100条/次**，5000积分 | 全量拉取，当前约15个合约 |
| sge_daily | 2005-01-01 | **2000条/次**，2000积分 | 按半月区间分批拉取 |

---

## 四、速率限制

所有接口共享全局 `RateLimiter(300次/分钟)`，确保 Tushare API 不超限。

| 接口 | API限制 | 实际调用量（全量） | 预估耗时 |
|------|--------|-------------------|---------|
| sge_basic | 100条/次 | 1次 | ~1秒 |
| sge_daily | 2000条/次 | ~255次（21年×12×2区间） | ~1分钟 |

---

## 五、TDengine 插入机制

### 5.1 子表+时间戳唯一

TDengine 超级表中，同一子表的相同时间戳 INSERT 会自动去重，**不会产生重复行**。增量更新无需先删后插。

### 5.2 批量插入优化

```python
# td_utils.insert_dataframe_to_td()
# 每个 ts_code 生成一条 INSERT ... USING ... TAGS (...) VALUES (...)
# 格式: INSERT INTO qmt_ai.sg_Au99_95 USING sge_daily TAGS ('Au99.95') VALUES (...)
```

### 5.3 子表命名规则

| 超级表 | 前缀 | 示例 |
|--------|------|------|
| sge_daily | sg_ | sg_Au99_95, sg_Au_T_D, sg_AUX_CNY1Y_FWD |

> **特殊字符处理**：合约代码中的 `.`、`-`、`(`、`)`、`+` 均替换为 `_`

### 5.4 时间字段映射

| 接口 | API字段 | TDengine ts | 格式处理 |
|------|---------|-------------|---------|
| sge_daily | trade_date | ts | YYYYMMDD → YYYY-MM-DD 00:00:00 |

---

## 六、字段映射说明

### 6.1 sge_basic 字段映射

Tushare API 字段与 GreatSQL 表字段映射：

| API字段 | GreatSQL字段 | 说明 |
|---------|-------------|------|
| ts_code | ts_code | 品种代码 |
| ts_name | name | 品种名称 |
| t_unit | trade_unit | 交易单位(克/手) |
| p_unit | quote_unit | 报价单位 |
| — | exchange | 固定值 'SGE' |
| — | per_unit | NULL（预留字段） |
| list_date | list_date | 上市日期（YYYY-MM-DD → YYYYMMDD） |

> 其他API字段（trade_type, min_change, price_limit, min_vol, max_vol, trade_mode, margin_rate, liq_rate, trade_time）暂不入库

---

## 七、特殊说明

### 7.1 sge_basic — 不做日期过滤

`sync_sge_basic` 全量拉取所有上海黄金现货合约，**不按 list_date 过滤**。sge_basic 作为基础查表，需包含所有合约代码，其后再按日期参数同步各合约的历史行情。

### 7.2 sge_daily 按半月区间分批

接口单次最大返回2000条，采用半月区间策略分批拉取：
- 每月分成2个区间：1日-15日、16日-月末
- 确保每个区间数据量不超过API限制
- 返回接近2000条时记录截断警告

### 7.3 截断检测机制

- sge_basic：返回 ≥95条 时警告（单次上限100条）
- sge_daily：返回 ≥1950条 时警告（单次上限2000条）

---

## 八、依赖模块

```
src/utils/sync_utils.py                      # GreatSQL 工具（RateLimiter, insert_dataframe 等）
src/utils/td_utils.py                        # TDengine 批量插入工具（insert_dataframe_to_td）
src/fetch_tushare_data/commodity/            # 2个 fetch 接口实现
├── fetch_sge_basic.py                       # 上海黄金基础信息接口
└── fetch_sge_daily.py                       # 上海黄金现货日行情接口
src/data_sync/full_sync/
└── sync_commodity_data_bydate.py            # 2个现货接口同步脚本
scripts/
├── sync_commodity_data_all.sh               # 基础数据全量同步
└── sync_commodity_data.sh                   # 日行情按日期同步
src/batch/sql/
├── tdengine/现货数据.sql                     # sge_daily 超级表DDL
└── greatsql/现货数据.sql                     # sgt_basic 表DDL
```

---

## 九、Tushare 积分权限要求

| 接口 | 积分要求 | 备注 |
|------|---------|------|
| sge_basic | 5,000 | 单次100条，当前合约数约15个，一次可拉取全部 |
| sge_daily | 2,000 | 单次2000条，需按日期区间分批拉取 |

---

## 十、数据库分类原则

| 数据库 | 适用场景 | 现货数据中的体现 |
|--------|---------|----------------|
| **GreatSQL** | 基础信息、映射关系、不频繁变动的参考数据 | sgt_basic（合约基础信息） |
| **TDengine** | 时序数据、按时间轴查询、高频更新的行情/指标 | sge_daily（日行情） |

---

## 十一、数据示例

### 11.1 sge_basic 数据示例

```
ts_code    name      trade_unit  quote_unit  list_date
Au99.95    黄金9995   1000.0      1.0         20021030
Au99.99    黄金9999   1000.0      1.0         20040601
Au(T+D)    黄金延期   1000.0      1.0         20040816
```

### 11.2 sge_daily 数据示例

```
ts_code      trade_date    close    open    high    low     vol       amount
Au99.95      20260424      403.30   403.20  403.30  403.20  24.00     9678.00
Au99.99      20260424      403.60   405.97  408.00  402.80  13667.66  5500000.00
Au(T+D)      20260424      403.22   405.01  407.70  402.53  27196.00  11000000.00
```

---

## 十二、常见问题

### Q1: 为什么 sge_daily 同步返回 0 行？

检查以下几点：
1. Tushare积分是否达到2000分门槛
2. 日期范围是否有效（非交易日返回0行）
3. API是否返回空数据（可手动调用验证）

### Q2: 子表名包含特殊字符怎么办？

`insert_dataframe_to_td` 已自动处理：
- `.` → `_`（如 Au99.95 → Au99_95）
- `-` → `_`
- `(` → `_`
- `)` → `_`
- `+` → `_`（如 Au(T+D) → Au_T_D）

### Q3: 数据量超过API限制怎么办？

代码已内置截断检测：
- 返回接近API上限时记录警告日志
- 半月区间策略确保单次不超过2000条
- 若某区间超限，可手动缩小日期范围重试

---

## 十三、数据质量（2026-05-17 探查）

### 总体结论

| 检查项 | 结果 |
|--------|------|
| 数据连续性 | ✓ 47 个合约，Au99.95/Au99.99/Au(T+D) 等主力合约 2005-01-04 ~ 至今连续 |
| API 截断 | ✓ 半月区间单次 ≤ 15天 × 47合约 ≈ 700 条，远小于 2000 上限 |
| 数据重复 | ✓ GreatSQL 零重复；TDengine 同子表+时间戳自动去重 |
| 字段 NULL | 见下方 |
| 日期格式 | ✓ 统一正确 |
| 同一日期 | ✓ 无异常 |

### 字段 NULL 明细

| 表 | 字段 | NULL率 | 说明 |
|----|------|--------|------|
| sgt_basic | per_unit | 100% | 预留字段，暂未使用 |
| sgt_basic | delist_date | 100% | 合约未退市 |
| sge_daily | settle_vol | 73.3% | 部分合约不提供结算量 |
| sge_daily | settle_dire | 73.7% | 部分合约不提供结算方向 |
| sge_daily | oi | 17.2% | 部分合约无持仓量 |
| sge_daily | open/high/low | 3.9% | 极少数非交易日/无数据日 |

### 需清理

| 问题 | 详情 | 方案 |
|------|------|------|
| `sg_test` 测试子表 | 3 行测试数据（2026-05-08~10），非真实合约 | `DROP TABLE \`sg_test\`` |