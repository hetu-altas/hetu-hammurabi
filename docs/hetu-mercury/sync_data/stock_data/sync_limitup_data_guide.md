# 打板专题数据同步指南

> 更新日期：2026-05-06 | 同步模块：`src/data_sync/full_sync/stock_data/sync_limitup_data_bydate.py`

---

## 一、接口总览（24 个）

11 个入 TDengine，13 个入 GreatSQL。数据起始 2005-01-01，多数接口实际数据从 2020~2025 年开始。

| # | 接口 | 中文名称 | 目标库 | 表名 | 同步策略 | 当前行数 | API上限 |
|---|------|---------|--------|------|---------|---------|---------|
| 1 | top_list | 龙虎榜每日统计单 | TDengine | top_list | 交易日逐日 | 97,124 | 10,000 |
| 2 | top_inst | 龙虎榜机构交易单 | TDengine | top_inst | 交易日逐日 | 96,146 | 10,000 |
| 3 | limit_list_ths | 同花顺涨跌停榜单 | TDengine | limit_list_ths | 半月区间 | 46,425 | 4,000 |
| 4 | limit_list_d | 涨跌停和炸板数据 | TDengine | limit_list_d | 半月区间 | 155,467 | 2,500 |
| 5 | limit_step | 涨停股票连板天梯 | TDengine | limit_step | 半月区间 | 12,184 | 2,000 |
| 6 | limit_cpt_list | 涨停最强板块统计 | GreatSQL | limit_cpt_list | 半月区间 | 11,973 | 2,000 |
| 7 | ths_index | 同花顺行业概念板块 | GreatSQL | ths_index | 单次全量 | 1,724 | 5,000 |
| 8 | ths_daily | 同花顺概念行业指数行情 | TDengine | ths_daily | **按天循环** | 2,906,763 | 3,000 |
| 9 | ths_member | 同花顺行业概念成分 | GreatSQL | ths_member | 代码循环 | 310,287 | — |
| 10 | dc_index | 东方财富概念板块 | GreatSQL | dc_index | 单次全量 | 5,000 | 5,000 |
| 11 | dc_member | 东方财富概念成分 | GreatSQL | dc_member | 代码循环 | 5,026,516 | 5,000 |
| 12 | dc_daily | 东财概念行业指数行情 | TDengine | dc_daily | **按天循环** | 2,901,207 | 2,000 |
| 13 | stk_auction | 开盘竞价成交 | TDengine | stk_auction | **按天循环** | 1,708,671 | 8,000 |
| 14 | hm_list | 市场游资最全名录 | GreatSQL | hm_list | 单次全量 | 110 | 1,000 |
| 15 | hm_detail | 游资交易每日明细 | TDengine | hm_detail | 半月区间 | 45,126 | 2,000 |
| 16 | ths_hot | 同花顺App热榜 | GreatSQL | ths_hot | 交易日逐日 | 970,372 | 2,000 |
| 17 | dc_hot | 东方财富App热榜 | GreatSQL | dc_hot | 交易日逐日 | 1,183,386 | 2,000 |
| 18 | tdx_index | 通达信板块信息 | GreatSQL | tdx_index | 单次全量 | 1,000 | 1,000 |
| 19 | tdx_member | 通达信板块成分 | GreatSQL | tdx_member | 代码循环 | 1,431,461 | 3,000 |
| 20 | tdx_daily | 通达信板块行情 | TDengine | tdx_daily | 半月区间 | 80,815 | 3,000 |
| 21 | kpl_list | 榜单数据（开盘啦） | TDengine | kpl_list | 半月区间 | 137,337 | 8,000 |
| 22 | kpl_concept_cons | 题材成分（开盘啦） | GreatSQL | kpl_concept_cons | **按天循环** | 23,388,000 | 3,000 |
| 23 | dc_concept | 题材数据（东方财富） | GreatSQL | dc_concept | 单次全量 | 5,000 | 5,000 |
| 24 | dc_concept_cons | 题材成分（东方财富） | GreatSQL | dc_concept_cons | 代码循环 | 527,000 | 3,000 |

> **总计**：GreatSQL ~33,419,829 行 + TDengine ~7,189,265 行 = **约 4,000 万行**

---

## 二、执行方式

### 2.1 Shell 脚本

```bash
# 全量同步（2005-01-01 至今）
bash scripts/sync_limitup_data.sh

# 指定日期范围
bash scripts/sync_limitup_data.sh 20240101 20241231

# 修复重跑（仅跑有问题/截断的表）
bash scripts/sync_limitup_data_fix.sh
bash scripts/sync_limitup_data_fix.sh 20240101 20241231
```

### 2.2 Python 直接调用

```python
from sync_limitup_data_bydate import (
    sync_top_list, sync_top_inst, sync_limit_list_ths,
    sync_limit_list_d, sync_limit_step, sync_limit_cpt_list,
    sync_ths_index, sync_ths_daily, sync_ths_member,
    sync_dc_index, sync_dc_member, sync_dc_daily,
    sync_stk_auction, sync_hm_list, sync_hm_detail,
    sync_ths_hot, sync_dc_hot, sync_tdx_index,
    sync_tdx_member, sync_tdx_daily, sync_kpl_list,
    sync_kpl_concept_cons, sync_dc_concept, sync_dc_concept_cons,
    run_all_sync,
)

# 全量：不传参
sync_top_list()
sync_ths_index()

# 增量：传 start_date/end_date（YYYYMMDD 格式）
sync_top_list(start_date="20260501", end_date="20260505")
sync_ths_daily(start_date="20260501")

# 串行执行全部 24 个接口
run_all_sync()
```

---

## 三、同步策略详解

### 3.1 策略分类

| 策略 | 接口数 | 接口列表 | 说明 |
|------|--------|---------|------|
| **按天循环** (chunk_days=1) | 4 | stk_auction, dc_daily, ths_daily, kpl_concept_cons | 避免单次 API 超限截断 |
| 交易日逐日 | 4 | top_list, top_inst, ths_hot, dc_hot | 仅支持 trade_date 单日查询 |
| 半月区间 | 7 | limit_list_ths, limit_list_d, limit_step, limit_cpt_list, hm_detail, tdx_daily, kpl_list | 数据量适中，15天不超限 |
| 单次全量 | 6 | ths_index, dc_index, dc_concept, tdx_index, hm_list, dc_concept_cons | 一次性返回完整参考数据 |
| 代码循环 | 4 | ths_member, dc_member, tdx_member, dc_concept_cons | 先获取代码列表，再逐代码拉取 |

### 3.2 超限截断问题

以下接口因单日数据量较大，原半月区间超出 API 最大返回条数，已改为**按天循环**：

| 接口 | API 上限 | 单日~量 | 半月区间预估 | 丢失率 | 修复 |
|------|---------|---------|-------------|--------|------|
| stk_auction | 8,000 | ~5,499 | ~82,485 | ~90% | chunk_days=1 |
| dc_daily | 2,000 | ~667 | ~10,000 | ~80% | chunk_days=1 |
| ths_daily | 3,000 | ~1,000 | ~15,000 | ~80% | chunk_days=1 |
| kpl_concept_cons | 3,000 | ~2,000 | ~30,000 | ~90% | chunk_days=1 |

### 3.3 不支持日期参数的接口

| 接口 | 入参 | 注意 |
|------|------|------|
| ths_member | ts_code, con_code | 仅返回最新成分快照 |
| dc_concept_cons | ts_code, concept_code | 仅返回当日快照，每个题材上限 3,000 |

---

## 四、已知问题与修复记录

| # | 接口 | 问题 | 现象 | 修复 |
|---|------|------|------|------|
| 1 | stk_auction | 前缀 `sa_` 与 stk_alert 冲突 | `Table already exists in other stables` | stk_alert 前缀改为 `al_` |
| 2 | tdx_daily | 数字开头列名(3day等)映射错误 | `Invalid column name: day_3` | 别名映射 d3→3day |
| 3 | hm_detail | FIELD_MAP 中 name→ts_name，API 实际返回 ts_name | ts_name 字段全 NULL | 改为 ts_name→ts_name |
| 4 | limit_cpt_list / tdx_index / ths_hot / dc_hot / kpl_concept_cons / dc_concept / dc_concept_cons | GreatSQL 列名列表与实际 API 返回值不匹配 | 数据全 0 或字段错位 | 逐一修正为实际列名 |
| 5 | dc_concept_cons | code_field 用 ts_code，实际应 concept_code | 代码循环全部 0 行 | 改为 concept_code |
| 6 | ths_member / dc_concept_cons | 传入不支持的 start_date/end_date | TypeError 静默失败 | 移除日期参数传递 |
| 7 | hm_list | orgs 列 varchar(100) 太小 | Data too long (实际 4436 字符) | ALTER 为 TEXT |
| 8 | ths_hot | rank_reason 列 varchar(100) 太小 | Data too long (581 字符) | ALTER 为 TEXT |
| 9 | dc_hot | 缺少 hot / concept 列 | Unknown column | ALTER TABLE ADD |
| 10 | kpl_concept_cons | desc 列 varchar(100) 太小 | Data too long (154 字符) | ALTER 为 TEXT |

---

## 五、TDengine 表结构

| 超级表 | 前缀 | ts 来源 | 子表示例 |
|--------|------|---------|---------|
| top_list | tl_ | trade_date → ts | tl_000001_SZ |
| top_inst | ti_ | trade_date → ts | ti_000001_SZ |
| limit_list_ths | lt_ | trade_date → ts | lt_000001_SZ |
| limit_list_d | ld_ | trade_date → ts | ld_000001_SZ |
| limit_step | ls_ | trade_date → ts | ls_000001_SZ |
| stk_auction | sa_ | trade_date → ts | sa_000001_SZ |
| hm_detail | hd_ | trade_date → ts | hd_000001_SZ |
| ths_daily | td_ | trade_date → ts | td_880001_TI |
| dc_daily | dd_ | trade_date → ts | dd_BK1184_DC |
| tdx_daily | tx_ | trade_date → ts | tx_880559_TDX |
| kpl_list | kl_ | trade_date → ts | kl_000001_SZ |

> 注：`tdx_daily` 表中 `3day`/`5day`/`10day`/`20day`/`60day`/`1year` 六列为数字开头列名，在 Python 代码中通过别名 `d3`/`d5`/`d10`/`d20`/`d60`/`y1` 映射，INSERT SQL 中使用反引号包裹。

---

## 六、速率限制

全局 `RateLimiter(200次/分钟)`。各接口预估耗时：

| 接口 | 调用次数（全量） | 预估耗时 |
|------|----------------|---------|
| top_list / top_inst / ths_hot / dc_hot | ~7,700 次 (交易日) | ~38 分钟/个 |
| stk_auction / dc_daily / ths_daily | ~7,700 次 (按天) | ~38 分钟/个 |
| kpl_concept_cons（按天） | ~7,700 次 | ~38 分钟 |
| 其他半月区间 (7个) | ~513 次 | ~2 分钟/个 |
| 代码循环 (4个) | N×代码数 | 取决于代码数量 |
| 单次全量 (5个) | 1 次 | < 1 秒 |

> 24 接口全量预估总耗时约 **6~8 小时**。

---

## 七、依赖模块

```
src/utils/sync_utils.py                              # 通用工具（RateLimiter, get_db, insert_dataframe）
src/utils/td_utils.py                                # TDengine 批量插入（insert_dataframe_to_td）
src/fetch_tushare_data/stock_data/limit_up_data/
├── fetch_top_list.py / fetch_top_inst.py             # 龙虎榜
├── fetch_limit_list_ths.py / fetch_limit_list_d.py   # 涨跌停
├── fetch_limit_step.py / fetch_limit_cpt_list.py     # 连板天梯/板块统计
├── fetch_ths_index.py / fetch_ths_daily.py           # 同花顺板块
├── fetch_ths_member.py / fetch_ths_hot.py            # 同花顺成分/热榜
├── fetch_dc_index.py / fetch_dc_daily.py             # 东财板块
├── fetch_dc_member.py / fetch_dc_hot.py              # 东财成分/热榜
├── fetch_dc_concept.py / fetch_dc_concept_cons.py    # 东财题材
├── fetch_tdx_index.py / fetch_tdx_daily.py           # 通达信板块
├── fetch_tdx_member.py                               # 通达信成分
├── fetch_hm_list.py / fetch_hm_detail.py             # 游资
├── fetch_kpl_list.py / fetch_kpl_concept_cons.py     # 开盘啦
└── fetch_stk_auction.py                              # 竞价成交
src/data_sync/full_sync/stock_data/
└── sync_limitup_data_bydate.py                       # 24 接口同步脚本
scripts/
├── sync_limitup_data.sh                              # 全量 Shell 脚本
└── sync_limitup_data_fix.sh                          # 修复重跑 Shell 脚本
unit_test/
├── test_sync_limitup_data.py                         # 50 个单元测试用例
└── test/
    └── test_sync_limitup_data_result.txt              # 测试结果（50/50 通过）
```

---

## 八、Tushare 积分权限要求

| 接口 | 积分要求 | 频率限制 | 备注 |
|------|---------|---------|------|
| top_list | 2,000 | — | 龙虎榜每日统计单 |
| top_inst | 5,000 | — | 龙虎榜机构交易单 |
| limit_list_ths | 8,000 | 500/min | 同花顺涨跌停榜单，数据从 2023-11-01 开始 |
| limit_list_d | 5,000/8,000 | 200~500/min | 涨跌停炸板，数据从 2020 年开始 |
| limit_step | 8,000 | 500/min | 连板天梯 |
| limit_cpt_list | 8,000 | 500/min | 涨停最强板块统计 |
| ths_index / ths_daily / ths_member | 6,000 | 200/min (member) | 同花顺板块系列 |
| dc_index / dc_member / dc_daily | 6,000 | — | 东方财富板块系列 |
| dc_concept / dc_concept_cons | 6,000 | — | 东方财富题材系列 |
| tdx_index / tdx_member / tdx_daily | 6,000 | — | 通达信板块系列 |
| hm_list / hm_detail | 5,000/10,000 | — | 游资名录/明细 |
| ths_hot / dc_hot | 6,000/8,000 | — | 热榜数据 |
| kpl_list / kpl_concept_cons | 5,000 | 200~500/min | 开盘啦系列 |
| stk_auction | 分钟权限 | — | 单独开权限，已有股票分钟权限自动获得 |

> 备注：`stk_auction` 需分钟权限；`limit_list_ths` 数据从 2023-11 开始；`kpl_concept_cons` 因源站改版暂无新增数据。
