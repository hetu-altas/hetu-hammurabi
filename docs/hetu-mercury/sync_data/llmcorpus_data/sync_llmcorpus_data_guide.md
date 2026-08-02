# 大模型语料专题数据同步指南

> 更新日期：2026-05-18（20260802 任务2 更新：自然日区间 + 状态文件驱动、唯一键幂等修订） | 同步模块：`src/data_sync/full_sync/sync_llmcorpus_data_bydate.py`

---

## 一、接口总览（8 个）

全部入 **GreatSQL**，无 TDengine 入库。

| # | 接口 | 中文名称 | 表名 | 同步策略 | 单次上限 | 最早日期 |
|---|------|---------|------|---------|---------|---------|
| 1 | npr | 国家政策库 | npr | 按年分块（22年），fields 指定全列 | 500 | 2005-01-01 |
| 2 | research_report | 券商研究报告 | research_report | 3天分块 × report_type 主动分片（个股/行业） | 1000 | 2005-01-01 |
| 3 | news | 新闻快讯（短讯） | news | src(9源) × 3小时分块（每天8段），fields 指定全列 | 1500 | 2005-01-01 |
| 4 | major_news | 新闻通讯（长篇） | major_news | src(9源) × 3小时分块（每天8段），fields 指定全列 | 400 | 2005-01-01 |
| 5 | cctv_news | 新闻联播文字稿 | cctv_news | 按日循环 | 无限制 | 2017-01-01 |
| 6 | anns_d | 上市公司公告 | anns_d | 按 ts_code 逐股拉取（全量日期），fields 指定全列 | 2000 | 2005-01-01 |
| 7 | irm_qa_sh | 上证e互动问答 | irm_qa_sh | 按半月分块 | 3000 | 2005-01-01 |
| 8 | irm_qa_sz | 深证易互动问答 | irm_qa_sz | 按半月分块 | 3000 | 2005-01-01 |

### 分片策略详解

| 接口 | 主分片维度 | 副分片维度 | 单次预估量 | 截断风险 |
|------|-----------|-----------|-----------|---------|
| npr | 年(1年) | — | <50 | 低 |
| research_report | 3天 | report_type(个股/行业各1次) | <600 | 无（主动分片避让） |
| news | src(9源) | 3小时(8段/天) | <500 | 低 |
| major_news | src(9源) | 3小时(8段/天) | <100 | 低 |
| cctv_news | 日 | — | <20 | 无 |
| anns_d | ts_code(逐股) | start_date/end_date(全量) | <200 | 无（单股不超2000） |
| irm_qa_sh | 半月(15天) | — | <500 | 低 |
| irm_qa_sz | 半月(15天) | — | <500 | 低 |

---

## 二、执行方式

### 2.1 Shell 脚本

```bash
# 全量同步（含全量清理，仅初次部署/数据重建）
bash scripts/sync_llmcorpus_data_all.sh

# 按日期区间同步（日常增量）
bash scripts/sync_llmcorpus_data.sh                            # 全量 (2005-01-01 至今)
bash scripts/sync_llmcorpus_data.sh 20260501                   # 从指定日期至今
bash scripts/sync_llmcorpus_data.sh 20260501 20260514          # 指定日期范围
```

> **20260802 任务2 更新**：日常增量实际由 `scripts/sync_by_day/daily_llmcorpus_sync.sh` 驱动（crontab `40 21 * * *`，每日含周末）。2026-08-02 任务2 修复缺陷 B：原脚本按 `get_latest_trade_day('CN')`（最近交易日）同步**单日**，周六/周日运行时仍取周五，导致周末产生的 news/major_news/cctv_news 等自然日数据永不同步；现改为「**自然日区间 + 状态文件驱动**」：

| 调用形态 | 同步区间 | 说明 |
|---------|---------|------|
| 无参（crontab 默认） | 上次成功同步日+1 ~ 今天 | 状态文件驱动，连续运行区间无缝衔接（不重不漏） |
| 无参 + 状态文件缺失/内容非法 | 昨天 ~ 今天 | 首次部署/文件损坏退化，避免全量拉取 |
| 1 参 `20260801` | `20260801 ~ 20260801` | 手动单日补数（兼容旧单参形态），**不写状态文件** |
| 2 参 `20260720 20260801` | `20260720 ~ 20260801` | 手动区间补数，**不写状态文件**（补数不改增量进度） |

- **状态文件路径**：`/mnt/e/logs/hetu-altas/hetu-mercury/llmcorpus_last_sync.date`（内容 `YYYYMMDD`，即上次成功同步日）。
- **写时机**：仅当「非手动 且 8 源全部成功」才原子写入（tmp+mv）`今天`；任一源失败 → 不写、退出码非 0，下次运行自动从原 last+1 重试；状态文件超前/同天 → 输出「已是最新」空跑退出 0（幂等）。
- **幂等**：8 个 sync 函数均经 `insert_dataframe(..., ignore_duplicates=True)`（INSERT IGNORE）写入，配合 8 表 `uk_*` 唯一键（见第十节），同日/同区间重复同步自动跳过重复行。
- **环境变量注入点**（测试/运维用）：`LLMCORPUS_STATE_FILE`（状态文件路径）、`LLMCORPUS_TODAY`（桩今天，默认 `date +%Y%m%d`）、`LLMCORPUS_SYNC_BIN`（桩同步执行器）。
- 日期统一 `YYYYMMDD`，加减复用 hetu-aether `utils/util_datetime.py`（禁止 shell 手写日期算术）；退出码：0 成功（含空跑）/ 1 同步失败 / 2 参数非法。

### 2.2 Python 直接调用

```python
from sync_llmcorpus_data_bydate import (
    sync_npr, sync_research_report, sync_news, sync_major_news,
    sync_cctv_news, sync_anns_d, sync_irm_qa_sh, sync_irm_qa_sz,
    run_all_sync,
)

# 全量同步
sync_npr(start_date="20050101", end_date="20260514")
sync_research_report(start_date="20050101", end_date="20260514")
sync_news(start_date="20050101", end_date="20260514")
sync_major_news(start_date="20050101", end_date="20260514")
sync_cctv_news(start_date="20050101", end_date="20260514")
sync_anns_d(start_date="20050101", end_date="20260514")
sync_irm_qa_sh(start_date="20050101", end_date="20260514")
sync_irm_qa_sz(start_date="20050101", end_date="20260514")

# 增量（传日期参数）
sync_news(start_date="20260513", end_date="20260514")
sync_anns_d(start_date="20260513", end_date="20260514")

# 8线程并行全量
result = run_all_sync()
```

---

## 三、新闻源列表

### 3.1 news（短讯）— 9 个源

| src 标识 | 来源 |
|---------|------|
| sina | 新浪财经 |
| wallstreetcn | 华尔街见闻 |
| 10jqka | 同花顺 |
| eastmoney | 东方财富 |
| yuncaijing | 云财经 |
| fenghuang | 凤凰新闻 |
| jinrongjie | 金融界 |
| cls | 财联社 |
| yicai | 第一财经 |

### 3.2 major_news（长篇）— 9 个源

| src 标识 | 来源 |
|---------|------|
| 新华网 | 新华网 |
| 凤凰财经 | 凤凰财经 |
| 同花顺 | 同花顺 |
| 新浪财经 | 新浪财经 |
| 华尔街见闻 | 华尔街见闻 |
| 中证网 | 中证网 |
| 财新网 | 财新网 |
| 第一财经 | 第一财经 |
| 财联社 | 财联社 |

---

## 四、速率限制与预估耗时

全局 `RateLimiter(200次/分钟)`，8线程并行。

| 接口 | 调用量（全量 2005~2026） | 预估耗时 |
|------|------------------------|---------|
| npr | 22 次（22年） | <1 分钟 |
| research_report | ~1,550 次（776窗 × 2类） | ~8 分钟 |
| news | ~138,000 次（9源 × 1915天 × 8段） | ~690 分钟 |
| major_news | ~138,000 次（9源 × 1915天 × 8段） | ~690 分钟 |
| cctv_news | ~4,000 次（2017年起约4000天） | ~20 分钟 |
| anns_d | ~6,000 次（~6000只股票） | ~30 分钟 |
| irm_qa_sh | ~500 次（~250月 × 2半月） | ~2.5 分钟 |
| irm_qa_sz | ~500 次 | ~2.5 分钟 |

> **注意**：news/major_news 全量调用量极大（~14万次），8线程并行下实际耗时约 690/8 ≈ 86 分钟。建议首次全量时分批次执行，日常增量仅按日期区间运行。

### 各接口实际数据量（截止 2026-05-16）

| 接口 | 行数 | 最早日期 | 最晚日期 | 数据大小 | 索引大小 |
|------|------|---------|---------|---------|---------|
| npr | 3,182 | 2020-09-12 | 2026-05-15 | 7.5 MB | 0.5 MB |
| research_report | 231,806 | 2020-01-01 | 2026-05-15 | 64.6 MB | 20.5 MB |
| news | 23,068,262 | 2020-01-01 | 2026-05-15 | 9.6 GB | 1.1 GB |
| major_news | 5,455,011 | 2020-01-01 | 2026-05-16 | 12.6 GB | 0.3 GB |
| cctv_news | 70,012 | 2020-01-01 | 2026-05-16 | 102.6 MB | 2.5 MB |
| anns_d | 11,771,475 | 2020-01-01 | 2026-05-16 | 2.7 GB | 1.2 GB |
| irm_qa_sh | 196,435 | 2023-06-07 | 2026-05-15 | 115.6 MB | 35.1 MB |
| irm_qa_sz | 222,103 | 2020-01-01 | 2026-05-15 | 117.6 MB | 37.6 MB |
| **合计** | **41,018,286** | — | — | **~25.1 GB** | **~2.8 GB** |

> 数据量最大的是 news（9.6 GB）和 major_news（12.6 GB），两项合计占总量的 88%。建议日常增量按天执行，全量首次同步时注意磁盘空间。

---

## 五、DDL 注意事项

### 5.1 非默认列需 fields 指定

以下 API 列标记为 `N`（非默认输出），必须在 fetch 调用中通过 `fields` 显式指定，否则对应 DDL 列入库为 NULL：

| 接口 | 需 fields 列 | 
|------|------------|
| npr | url, content_html |
| news | channels |
| major_news | content |
| anns_d | rec_time |

已在 sync 脚本中通过 `",".join(_XXX_COLUMNS)` 统一指定。

### 5.2 大写列名处理

部分 API 返回大写列名，sync 脚本统一执行 `df.columns = [c.lower() for c in df.columns]`。

### 5.3 文本字段类型

| 字段 | 类型 | 说明 |
|------|------|------|
| npr.content_html | MEDIUMTEXT | HTML 正文 |
| major_news.content | MEDIUMTEXT | 长篇通讯正文 |
| cctv_news.content | MEDIUMTEXT | 新闻联播文字稿 |
| research_report.abstr | TEXT | 研报摘要 |
| news.content | TEXT | 短讯内容 |
| irm_qa_sh.q / irm_qa_sh.a | TEXT | 问答文本 |
| irm_qa_sz.q / irm_qa_sz.a | TEXT | 问答文本 |

### 5.4 日期格式

- `YYYYMMDD` 格式（research_report, cctv_news, anns_d, irm_qa_sh/sz）→ 列类型 `DATE`
- `YYYY-MM-DD HH:MM:SS` 格式（npr, news, major_news）→ 列类型 `DATETIME`
- MySQL `DATE` 类型可直接接受 `YYYYMMDD` 格式字符串

### 5.5 索引设计

每张表按查询频率建立了索引，anns_d 和 research_report 额外包含 `(ts_code, date)` 联合索引。

---

## 六、特殊说明

### 6.1 anns_d — ts_code 不支持逗号分隔

实测 `fetch_anns_d(ts_code="600590.SH,300504.SZ")` 返回 0 行，不支持批量查询。改为逐股调用（~6000只），每只传 `start_date/end_date` 全量日期范围。单股公告数远低于 2000 条，无截断风险。

### 6.2 research_report — ts_code 不支持逗号分隔

与 anns_d 相同，不支持批量 ts_code。尝试过 ts_code 分批策略失败后，改为 **3天分块 × report_type 主动分片**（`个股研报`/`行业研报`各一次），实测 3天窗 + 个股研报 <600条，无截断。

### 6.3 news — 日期格式为 datetime

news/major_news/npr 接口的 `start_date`/`end_date` 参数为 datetime 格式 `YYYY-MM-DD HH:MM:SS`，而非 YYYYMMDD。sync 脚本通过 `_ymd_to_datetime_str()` 转换，3小时分块直接产生 datetime 格式区间。

### 6.4 news/major_news — src 为必选参数

news API 的 `src` 参数为必选，major_news 的 `src` 为可选（不传则全源拉取）。sync 脚本对两接口均显式遍历所有源。

### 6.5 cctv_news — 数据始于 2017 年

cctv_news API 数据开始于 2017 年，2005-2016 年间调用返回空 DataFrame，不影响同步流程。

### 6.6 author 列长度

research_report 的 `author` 列原为 `VARCHAR(100)`，实测研报作者常含多人署名超长（如 "张三,李四,王五,赵六,孙七"），已扩大为 `VARCHAR(500)`。

### 6.7 并行执行

`run_all_sync()` 使用 `ThreadPoolExecutor(max_workers=8)` 并行执行 8 个接口，全局 RateLimiter 线程安全。news 和 major_news 调用量大，会占据大部分执行时间。

---

## 七、依赖模块

```
src/utils/sync_utils.py                              # GreatSQL 工具（RateLimiter, insert_dataframe, clear_table 等）
src/fetch_tushare_data/llm_corpus/                   # 8个 fetch 接口实现
├── fetch_npr.py
├── fetch_research_report.py
├── fetch_news.py
├── fetch_major_news.py
├── fetch_cctv_news.py
├── fetch_anns_d.py
├── fetch_irm_qa_sh.py
└── fetch_irm_qa_sz.py
src/data_sync/full_sync/
└── sync_llmcorpus_data_bydate.py                    # 8个接口同步脚本
scripts/
├── sync_llmcorpus_data_all.sh                       # 全量同步（含清理）
├── sync_llmcorpus_data.sh                           # 按日期区间同步
└── sync_major_news.sh                               # major_news 单独同步（2025起）
src/batch/sql/greatsql/大模型语料专题数据.sql          # GreatSQL 建表语句（8张表）
# ⚠️ 20260802 任务2 登记：该 DDL 8 表均无 UNIQUE KEY（仅普通 KEY + 自增主键），
#    与实库不符（实库 8 表均有 uk_* 唯一键，见第十节）——DDL 文件已过期，
#    是否修订由需求方决策，修订前以实库 SHOW CREATE TABLE 为准。
unit_test/
├── test_sync_llmcorpus_data_bydate.py               # 41个单元测试
└── test/
    └── test_sync_llmcorpus_data_result.txt           # 测试结果
```

---

## 八、Tushare 权限要求

所有接口均需**单独开权限**（与积分无关），具体请参阅 Tushare 权限说明。

| 接口 | doc_id | 权限要求 |
|------|--------|---------|
| npr | 406 | 需单独开权限 |
| research_report | 415 | 需单独开权限 |
| news | 143 | 需单独开权限 |
| major_news | 195 | 需单独开权限 |
| cctv_news | 154 | 需单独开权限 |
| anns_d | 176 | 需单独开权限 |
| irm_qa_sh | 366 | 需单独开权限 |
| irm_qa_sz | 367 | 需单独开权限 |

---

## 九、踩坑记录

| 问题 | 现象 | 修复 |
|------|------|------|
| research_report 按周截断 | 3天窗返回恰好1000条 | 改为3天 × report_type 主动分片（个股/行业各1次） |
| research_report ts_code 逗号分隔无效 | 返回0行 | 放弃 ts_code 批量策略，改用 report_type 分片 |
| anns_d 按日截断 | 单日返回恰好2000条 | 改为逐股+全量日期，单股不超2000 |
| anns_d ts_code 逗号分隔无效 | 返回0行 | 改为逐股循环 |
| news 按日截断 | 单源单日可能超1500条 | 改为3小时(8段/天)分块 |
| major_news 按日截断 | 单源单日可能超400条 | 改为3小时(8段/天)分块 |
| author 列超长 | `Data too long for column 'author'` | VARCHAR(100) → VARCHAR(500) |
| 非默认列缺失 | url/content_html/channels/rec_time 恒为 NULL | fetch 调用添加 `fields` 参数指定全列 |
| 旧表结构不匹配 | 4张表列名与 DDL 完全不一致 | 删除旧表，按 DDL 重建 8 张表 |
| 周末数据漏同步（缺陷 B） | 按最近交易日（`get_latest_trade_day`）同步单日，周六/周日运行时仍取周五，周末产生的 news/major_news/cctv_news 永不同步进 GreatSQL | 20260802 任务2：改为状态文件驱动的自然日区间（last+1 ~ 今天，含周末），并支持手动 1/2 参补数 |


## 十、数据质量（2026-05-18 探查）

### 数据概况

| 表 | 行数 | 时间字段 | 时间范围 |
|----|------|---------|---------|
| npr | 3,182 | pubtime | 2020-09-12 ~ 2026-05-15 |
| research_report | 231,806 | trade_date | 2020-01-01 ~ 2026-05-15 |
| news | 23,068,262 | datetime | 2020-01-01 ~ 2026-05-15 |
| major_news | 5,455,011 | pub_time | 2020-01-01 ~ 2026-05-16 |
| cctv_news | 70,012 | date | 2020-01-01 ~ 2026-05-16 |
| anns_d | 11,771,475 | ann_date | 2020-01-01 ~ 2026-05-16 |
| irm_qa_sh | 196,435 | trade_date | 2023-06-07 ~ 2026-05-15 |
| irm_qa_sz | 222,103 | trade_date | 2020-01-01 ~ 2026-05-15 |

### 总体结论

| 检查项 | 结果 |
|--------|------|
| 数据连续性 | ✓ 8 张表全部有数据，时间轴 2020~2026 连续 |
| API 截断 | ✓ 分片策略已验证（3h/8段、3天×report_type、逐股、半月） |
| 数据重复 | 8 表均含 `uk_*` 唯一键（20260802 任务2 实库 SHOW CREATE TABLE 核实：`uk_news(datetime,title(100),channels)`、`uk_major_news(pub_time,title(100),src)`、`uk_date_title(date,title)`、`uk_irm_qa_sh(ts_code,pub_time,q(100))`、`uk_ts_td_q(ts_code,trade_date,q(200))`、`uk_anns_d(ann_date,ts_code,title(100))`、`uk_npr(pubtime,title(100))`、`uk_ts_td_title(ts_code,trade_date,title)`）；重复同步由「INSERT IGNORE + 唯一键」幂等去重（原「未加唯一索引」记载与实库不符，已修订） |
| 字段 NULL | 非默认字段已通过 `fields` 参数修复 |
| 日期格式 | ✓ DATE/DATETIME 两种格式统一正确 |
| 同一日期 | ✓ 无异常 |

### 无需修复

- 8 张表全部有数据，零空表
- 日期范围均正确，无 1970-01-01 等异常占位
- news(23M)/major_news(5.5M) 为最大的两张表，占总量 88%
- `fields` 参数已配置（5.1 节），非默认列正常入库
