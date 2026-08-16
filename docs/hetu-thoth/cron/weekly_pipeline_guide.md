# npr/stock_report/industry_report/anns_d 周度流水线指南（weekly_pipeline）

> 沉淀日期：2026-08-08（20260810 任务1 更新：4 源化 + anns_d 仅下载+转MD 不向量化） | 来源任务：20260808任务1（npr_stock_industry周度拉取转MD向量化入库）、20260810任务1（anns_d 周度下载转MD补充）
> 模块：`scripts/weekly_pipeline.sh`（主编排）、`scripts/weekly_cron_install.sh`（cron 自管理）
> 本指南为沉淀版；业务版对应章节见 hetu-thoth `docs/text2jsonl/batch_embedding_guide.md` 3.6 节。

---

## 一、概述

为 **npr（国家政策）、stock_report（个股研报）、industry_report（行业研报）、anns_d（上市公司公告）** 四个数据源编排**按周**「拉取 → 转 MD → 向量化入库」流水线，节奏为：**周六凌晨下载上周五到本周五的报告，周六白天转 MD，周日向量化，周日晚 poll-only 补齐**。其中 **anns_d 仅下载 + 转 MD、不进行向量化操作**（vectorize/poll-only 阶段打印 SKIPPED 跳过，视为通过）。

本流水线为**纯整合型编排**：只调用 13 个既有原子脚本（下载/转MD/JSONL 生成/提交 Batch/轮询/下载结果/入库 Milvus），不重写任何下载、转MD、向量化业务逻辑，也不修改任何原子脚本。

| 文件 | 说明 |
|------|------|
| `scripts/weekly_pipeline.sh` | 周度主编排：`--stage download\|convert\|vectorize\|poll-only` 四阶段子命令 + `--dry-run/--anchor-date/--sources/--notify` 参数；回退式锚点周窗口计算；逐源逐步骤容错；钉钉失败告警 |
| `scripts/weekly_cron_install.sh` | cron 自管理：`--install/--uninstall/--status` 三动作，管理 4 条周度 cron 条目（标记注释幂等、安装/卸载前备份、`%` 转义） |
| `unit_test/test_weekly_pipeline.py` | 周度流水线单元测试（24 用例，≥16 门禁），结果 `unit_test/test/test_weekly_pipeline_result.txt` |

---

## 二、命令用法

### 2.1 主编排 `weekly_pipeline.sh`

```bash
# 四阶段（--stage 必选，缺省/非法退出码 2）
bash scripts/weekly_pipeline.sh --stage download        # 周六凌晨：研报+anns_d 公告下载（上周五~本周五）
bash scripts/weekly_pipeline.sh --stage convert         # 周六白天：四源转 MD（含 anns_d）
bash scripts/weekly_pipeline.sh --stage vectorize       # 周日：3 源 build→submit→poll→finalize→insert（anns_d 跳过）
bash scripts/weekly_pipeline.sh --stage poll-only       # 周日晚：跨天补齐（3 源仅 poll/finalize/insert；anns_d 跳过）

# 常用选项
bash scripts/weekly_pipeline.sh --stage vectorize --dry-run                        # 演练：仅打印命令，零副作用
bash scripts/weekly_pipeline.sh --stage download --anchor-date 2026-08-08          # 显式锚定周窗口（补跑）
bash scripts/weekly_pipeline.sh --stage vectorize -s stock_report                  # 单源过滤
bash scripts/weekly_pipeline.sh --stage vectorize -s npr,stock_report,industry_report
bash scripts/weekly_pipeline.sh --stage download -s anns_d                         # 单源：仅 anns_d 下载/转 MD
bash scripts/weekly_pipeline.sh --stage vectorize --notify off                     # 关闭失败钉钉告警（默认 on）
bash scripts/weekly_pipeline.sh -h                                                 # 帮助
```

### 2.2 cron 自管理 `weekly_cron_install.sh`

```bash
bash scripts/weekly_cron_install.sh            # 默认动作：安装
bash scripts/weekly_cron_install.sh --install  # 显式安装
bash scripts/weekly_cron_install.sh --uninstall# 卸载（仅删自动管理标记块，用户条目保留）
bash scripts/weekly_cron_install.sh --status   # 查询安装状态（0=已安装，1=未安装）
```

### 2.3 参数与环境变量注入点

| 参数 | 说明 |
|------|------|
| `--stage <download\|convert\|vectorize\|poll-only>` | 必选阶段；缺省/非法退出码 2 |
| `--anchor-date YYYY-MM-DD` | 周窗口锚点（默认系统当天；非周六自动回退到所在周的周六） |
| `--dry-run` | 演练模式：仅打印命令；不执行、不写状态文件、不调 crontab、不发通知 |
| `-s, --sources <列表>` | 逗号分隔源过滤，合法值 `npr,stock_report,industry_report,anns_d`；非法源退出码 2 并打印合法源列表 |
| `--notify on\|off` | 失败钉钉告警开关（默认 on；dry-run 一律不发送） |

| 环境变量 | 默认值 | 用途 |
|----------|--------|------|
| `THOTH_SCRIPTS_DIR` | `<项目>/scripts` | 步骤脚本目录（测试桩注入点） |
| `THOTH_STATE_DIR` | `/mnt/e/logs/weekly_pipeline` | 状态文件目录（`weekly_last_run.date`） |
| `THOTH_LOG_DIR` | `/mnt/e/logs/weekly_pipeline` | 日志目录（`<YYYYMMDD>.log`、cron 重定向、crontab 备份） |
| `THOTH_NOTIFY_BIN` | `<父目录>/venv-hetu/bin/python` | 钉钉通知执行器（测试注入桩） |
| `THOTH_CRONTAB_BIN` | `crontab` | crontab 命令（`weekly_cron_install.sh` 用，测试注入桩） |

---

## 三、周窗口锚点计算规则

**锚点制**：锚点 A = 运行日（或 `--anchor-date` 指定日）回退到「不晚于它的最近周六」；各阶段共用同一周窗口 **START（上周五）~ END（本周五）**。

```bash
# calc_window（回退式公式，已 date 实测修正任务书 D1 前进式笔误）
dow=$(date -d "$RUN_DATE" +%u)                  # %u：1=周一 ... 6=周六
back=$(( (7 + dow - 6) % 7 ))                   # 回退天数：周六=0、周五=1、周一=2
A    = RUN_DATE - back 天                        # 不晚于 RUN_DATE 的最近周六
END   = A - 1 天                                 # 本周五
START = END - 7 天（= A - 8 天）                  # 上周五
```

> ⚠️ 实测修正记录：GNU date 的 `A - 7 days` 是 A 前 7 个自然日（2026-08-08 → 08-01，上周六），并非上周五；正确公式为 **START = END − 7 天（= A − 8 天）**。此修正已在代码注释（L255-257）、实施计划与研发日志中固化。

**三个样例（date 实测与实现一致）**：

| 运行日 / --anchor-date | %u | 锚点 A | START（上周五） | END（本周五） | 说明 |
|------------------------|----|--------|----------------|--------------|------|
| 2026-08-08（周六） | 6 | 2026-08-08 | 2026-07-31 | 2026-08-07 | 常规周六运行 |
| 2026-08-10（周一补跑） | 1 | 2026-08-08（回退 2 天） | 2026-07-31 | 2026-08-07 | 回退同窗 → 幂等不重不漏 |
| 2026-08-15（下周六） | 6 | 2026-08-15 | 2026-08-07 | 2026-08-14 | 窗口随锚点前移 |

**补数操作**：错过整周后用 `--anchor-date` 显式锚定往前各周窗口补跑（默认首次上线不补历史）。

---

## 四、四阶段命令形态（以锚点 2026-08-08 → 窗口 2026-07-31 ~ 2026-08-07 为例）

| 阶段 | 源 | 命令（`bash $THOTH_SCRIPTS_DIR/...`） | 条数 |
|------|----|----------------------------------------|------|
| download | npr | **跳过**：npr 无独立下载脚本（`scripts/` 下无 download_npr\*），正文抓取内嵌 `convert_npr_to_markdown.py`，在 convert 阶段完成；仅打印/记录跳过说明（SKIPPED） | 0 |
| download | stock_report / industry_report | `download_research_report.sh -s 20260731 -e 20260807`（YYYYMMDD 区间） | 2 |
| download | **anns_d** | `download_anns_d_pdf.sh -s 20260731 -e 20260807`（YYYYMMDD 区间；股票范围由 `conf/favourite_conf.json` 关注板块控制） | **1** |
| convert | npr | `convert_npr_to_markdown.sh -s 20260731 -e 20260807`（YYYYMMDD 区间） | 1 |
| convert | stock_report / industry_report | `convert_stock_report_to_md.sh 2026-07-31`、`convert_industry_report_to_md.sh 2026-07-31`（**位置参数直接传日期**，$1=日期值本身，脚本内部拼 `--from-date` 前缀；终点隐含当天） | 2 |
| convert | **anns_d** | `convert_anns_d_to_md.sh 2026-07-31`（**CPU 版**，位置参数 $1=YYYY-MM-DD 起点，终点隐含当天） | **1** |
| vectorize | npr / stock_report / industry_report | `build_<src>_jsonl.sh 2026-07-31 2026-08-07`（显式传 `$START $END`，杜绝无参全量路径） | 3 |
| vectorize | npr / stock_report / industry_report | `submit_batch_task.sh -s <src>` → `poll_batch_tasks.sh -s <src>` → `finalize_batch_tasks.sh -s <src>` → `insert_vectors.sh -s <src>` | 12 |
| vectorize | **anns_d** | **跳过（SKIPPED）**：打印/记录「anns_d 不进行向量化操作，跳过」；不产生任何命令 | **0** |
| poll-only | npr / stock_report / industry_report | `poll_batch_tasks.sh -s <src>` → `finalize_batch_tasks.sh -s <src>` → `insert_vectors.sh -s <src>`（跳过 build/submit，跨天续跑） | 9 |
| poll-only | **anns_d** | **跳过（SKIPPED）**：同 vectorize 语义，不产生任何命令 | **0** |

**命令数校验**：download=3、convert=4、vectorize=15（3 个向量化源 × 5，anns_d 跳过）、poll-only=9（3 源 × 3）；`-s stock_report,industry_report` 过滤后 vectorize=10；`-s anns_d` 单源：download=1、convert=1、vectorize/poll-only=0（退出码 0）。

**SKIPPED 语义（20260810 任务1 新增，anns_d 不向量化）**：

- 触发点：`stage_vectorize` 与 `stage_poll_only` 中 `src = anns_d` 时，**不调用任何命令**；
- 键与值：vectorize 阶段 5 个键 `vectorize_anns_d_{build,submit,poll,finalize,insert}`、poll-only 阶段 3 个键 `poll-only_anns_d_{poll,finalize,insert}` 全部置 `STEP_RESULT=SKIPPED`、`STEP_RC=0`；
- 展示：stdout 打印 `[INFO] anns_d 不进行向量化操作，跳过（SKIPPED）`；日志写一行（键 `vectorize_anns_d_build` / `poll-only_anns_d_poll`）；汇总二维行显示 `[anns_d] build=SKIPPED submit=SKIPPED ...`；
- **视为通过**：SKIPPED 不计入 total/fail_count（print_summary/notify_failure 统计口径仅计 SUCCESS/FAILURE/DRY-RUN）→ 不触发钉钉告警、不改变退出码、不阻塞 `weekly_last_run.date` 写入；
- DRY-RUN 总体结论按**实际执行口径**表述（如「执行源 3 个，共 15 条命令；anns_d 不向量化跳过；未实际执行」），避免「4 源 × 5 = 15」式自相矛盾（20260810 M8a 修正）。

**日期参数换算要点**：4 个转MD脚本日期语义不一致（npr `-s/-e` YYYYMMDD 区间 vs stock/industry/anns_d `--from-date` 起点、终点隐含当天），由编排层统一换算，原子脚本不改；build 统一显式传 `$START $END` 两参（YYYY-MM-DD）；anns_d 下载脚本 `-s/-e` 为 YYYYMMDD 区间（与 stock/industry 同形态）。

**容错与退出码**：每命令独立 `set +e` 捕获（`run_step`）；源内任一步失败不影响该源后续步骤，源间任一源失败不影响其余源；汇总按「源 × 步骤」二维 + 失败明细；任一 FAILURE → 退出码 1；参数错误 → 退出码 2；成功/dry-run → 0。

---

## 五、cron 定时条目

标记注释：`# hetu-thoth npr/stock/industry 周度流水线（自动管理，勿手改）`

> ⚠️ 标记注释保持 20260808 原样（未体现 anns_d）：4 条 cron 为**阶段级触发**（不涉及源集合），源白名单变化对 cron 完全透明——周六 download/convert 自动带上 anns_d，周日 vectorize/poll-only 由 pipeline 内 SKIPPED 逻辑自动不含 anns_d；更新标记需重装 cron，与「cron 零改动」结论冲突，默认不更新（20260810 任务1 决策）。

| # | 表达式 | 阶段 | 触发语义 |
|---|--------|------|---------|
| 1 | `30 0 * * 6` | download | 周六凌晨下载（避开晚间同步与日间带宽高峰） |
| 2 | `30 8 * * 6` | convert | 周六白天转 MD |
| 3 | `0 8 * * 0` | vectorize | 周日全流程 build→submit→poll→finalize→insert |
| 4 | `0 22 * * 0` | poll-only | 周日夜间跨天补齐（Batch 异步兜底） |

- 每条均重定向至 `/mnt/e/logs/weekly_pipeline/cron_$(date +\%Y\%m\%d).log`；
- **`%` 必须转义为 `\%`**（crontab 中裸 `%` 非法，`$(date +\%Y\%m\%d)` 才能正确展开）；
- **备份原则（宪法第一条）**：安装/卸载前均自动备份 crontab 至 `crontab.bak.<时间戳>`（`$THOTH_LOG_DIR` 下）；卸载用 awk 状态机仅删标记行及其下 4 条执行条目，hetu-mercury 与 embedding 每日条目等用户条目完整保留；
- 幂等：标记已存在且 4 条齐全 → 「已安装」跳过；标记存在但条目 <4 → 移除旧块重装（升级路径）；
- 真实 crontab 操作前须人工确认并先备份（测试全程 `THOTH_CRONTAB_BIN` 桩隔离，不触碰真实 crontab）。

---

## 六、状态文件 `weekly_last_run.date`

- 路径：`$THOTH_STATE_DIR/weekly_last_run.date`（默认 `/mnt/e/logs/weekly_pipeline/weekly_last_run.date`）；
- 内容：`START~END`（如 `2026-07-31~2026-08-07`）；
- 写入时机：**仅 `--stage vectorize` 且非 dry-run 且全部源全部步骤 SUCCESS 时写入**；任一 FAILURE、dry-run、download/convert/poll-only 阶段均不写；
- **anns_d SKIPPED 不参与判定**（20260810 任务1）：anns_d 的 5 个键为 SKIPPED（≠ FAILURE），写入条件仍由 3 个向量化源（npr/stock_report/industry_report）决定；`weekly_last_run.date` 仍只反映向量化源窗口，**不记录 anns_d 下载/转换完成窗口**（补数判断口径不变）；
- 用途：窗口记录与补数判断；**不参与区间计算**（窗口永远由锚点决定，幂等由 build 脚本内置 `_check_existing_coverage` 按 source+日期范围查 `embedding_batch_task` 活动状态保证）。

---

## 七、与每日 embedding_pipeline 的分工

| 维度 | 每日流水线（20260801任务2） | 周度流水线（20260808任务1 + 20260810任务1） |
|------|---------------------------|---------------------------|
| 编排脚本 | `scripts/embedding_pipeline.sh` | `scripts/weekly_pipeline.sh` |
| 数据源 | news / major_news / cctv_news / irm_qa_sh / irm_qa_sz（5 源） | npr / stock_report / industry_report / anns_d（4 源；anns_d 仅下载+转MD 不向量化） |
| 周期 | 每日 23:30 | 周六凌晨下载 → 周六白天转MD → 周日向量化 → 周日晚 poll-only |
| 区间计算 | 按源状态文件 `last_run.<src>.date` 增量 | 锚点制统一周窗口（START~END） |
| 日志目录 | `/mnt/e/logs/embedding_pipeline/` | `/mnt/e/logs/weekly_pipeline/`（隔离） |
| 白名单 | 各自脚本内 `SUPPORTED_SOURCES` 常量，互不改动 | 同左 |

**两流水线数据源无交集**（每日 5 源不含周度 4 源中的任何源，anns_d 亦不在每日 5 源内，已核实 embedding `SUPPORTED_SOURCES` L49 与 weekly `SUPPORTED_SOURCES` L66），无需跨流水线去重；日志目录独立隔离，互不干扰。Batch 异步语义、`embedding_batch_task` 状态机与 `milvus_status`、Milvus collection `thoth_knowledge`、custom_id 前缀（`npr_`/`stock_report_`/`industry_report_`；anns_d 无向量化故无 custom_id 前缀）等复用既有定义（见 `docs/text2jsonl/batch_embedding_guide.md` 第二节）。

---

## 八、上游依赖

| 依赖 | 说明 |
|------|------|
| hetu-mercury 表记录同步 | npr / research_report 表记录（url/标题/pubtime/trade_date）由 hetu-mercury 从 Tushare 拉取入库；crontab 现有条目 `40 21 * * * ... daily_llmcorpus_sync.sh` **每日 21:40 同步**（`fetch_npr.py` / `fetch_research_report.py`）；下载安排在周六凌晨（`30 0 * * 6`）天然晚于周五 21:40 同步，数据就绪前提成立 |
| anns_d 公告记录同步（20260810 任务1 新增） | anns_d 表公告记录（url/标题/pubtime/trade_date）由 hetu-mercury `src/fetch_tushare_data/llm_corpus/fetch_anns_d.py` 同一 `daily_llmcorpus_sync.sh` 每日 21:40 同步链路维护；`download_anns_d_pdf.py` 从 GreatSQL `anns_d` 表读记录下载 → 周六凌晨下载天然晚于周五 21:40 同步，数据就绪前提成立（与 npr/research_report 同口径） |
| npr「下载」语义 | npr **无独立下载脚本**：npr 表记录由上游同步维护，「下载」语义 = convert 阶段由 `convert_npr_to_markdown.py` 内置 `_fetch_page_html` 从 npr 表读 url 抓网页 → 转 MD → 更新 file_locate |
| 数据落点 | PDF/MD 落 `file_dir=/mnt/backup/files`、`md_dir=/mnt/e/files`（原子脚本维护，编排不触碰）；JSONL 落 `/mnt/f/batch_jsonl/<source>/<YYYYMMDD>/`；配置见 `conf/dir_conf.json`。**anns_d 仅 PDF/MD 落盘，无 JSONL、无 Milvus 写入** |

---

## 九、故障排查

| 现象 | 排查路径 |
|------|---------|
| 某阶段失败 | 看日志 `/mnt/e/logs/weekly_pipeline/<YYYYMMDD>.log`：每源每步一行 `[时间] [<阶段>_<源>_<步骤>] SUCCESS\|FAILURE\|DRY-RUN \| 描述`，末尾「weekly pipeline 汇总」块含失败源×步骤明细；cron 触发问题看 `cron_<YYYYMMDD>.log` |
| 窗口是否已跑 | 看状态文件 `weekly_last_run.date`（内容 `START~END`）：仅 vectorize 全成功写入；若窗口缺失或失败，用 `--stage vectorize --anchor-date <该周周六> --dry-run` 演练后补跑 |
| 补数 | 用 `--anchor-date` 显式锚定往前各周窗口（周一补跑自动回退同窗幂等）；build 幂等由 `_check_existing_coverage` 保证，重复跑不重复生成 |
| 钉钉告警 | 存在失败步骤且 `--notify on`（默认）时发送失败汇总（含失败源×步骤明细）；成功不发；dry-run 不发送；通知失败仅 warning 不影响退出码 |
| cron 条目异常 | `bash scripts/weekly_cron_install.sh --status` 查状态；`--uninstall` 后重装；注意条目中 `%` 必须是 `\%`；安装/卸载前自动备份 `crontab.bak.<时间戳>` |
| 原子脚本级失败 | 单任务级失败可能仍 0 退出（submit/poll/finalize 内部 logger.error + continue），编排以退出码为唯一判定依据；任务级失败详情见各原子脚本日志与 Batch 状态；finalize 成功自带钉钉成功通知属原子脚本既有行为，编排不拦截 |

### 风险与注意事项（20260810 任务1 补充）

- **P1：anns_d 下载窗口时长（高优先，首次上线观察）**：anns_d 公告按 `conf/favourite_conf.json` 关注板块股票数拉取，7 天窗口数据量可能显著大于研报——周六 00:30（`30 0 * * 6` download）触发下载，能否在 08:30（`30 8 * * 6` convert）前完成需**首次运行观察**（实际耗时查 `/mnt/e/logs/weekly_pipeline/cron_<YYYYMMDD>.log`）；若超时需评估：**调整下载时间 / 拆分窗口 / convert 顺延**（涉及 cron 变更须回提需求方确认）；源间容错保证 anns_d 失败/超时不影响既有 3 源与退出码判定（20260810 任务1 待确认项 P1，来源任务书附待确认项）。

---

## 十、复用的既有原子脚本（只调用不修改）

| 原子脚本 | 周度编排调用形态 |
|---------|-----------------|
| `scripts/download_research_report.sh` | stock_report、industry_report 共用：`-s YYYYMMDD -e YYYYMMDD` |
| `scripts/download_anns_d_pdf.sh`（20260810 任务1 新增） | anns_d 公告下载：`-s YYYYMMDD -e YYYYMMDD` 区间（默认 20240101 起；股票范围由 `conf/favourite_conf.json` 控制；调用 `download_anns_d_pdf.py::download_anns_d_pdf(start_date, end_date)`，返回 `{total, success, failed, skipped, no_pdf}`） |
| `scripts/convert_npr_to_markdown.sh` | npr 转 MD：`-s YYYYMMDD -e YYYYMMDD` 区间（npr 正文抓取内嵌于此） |
| `scripts/convert_stock_report_to_md.sh` / `convert_industry_report_to_md.sh` | 位置参数直接传日期 `"$START"`（YYYY-MM-DD；$1=日期值本身） |
| `scripts/convert_anns_d_to_md.sh`（20260810 任务1 新增） | anns_d 转 MD（**CPU 版**）：位置参数 `"$START"`（YYYY-MM-DD；脚本内部拼 `--from-date` 前缀，终点隐含当天）；GPU 版 `convert_anns_d_to_md_gpu.sh` 存在但**不在周度编排使用**（留作手动/未来提速） |
| `scripts/build_npr_jsonl.sh` / `build_stock_report_jsonl.sh` / `build_industry_report_jsonl.sh` | 显式传 `$START $END`（YYYY-MM-DD）；内置 `_check_existing_coverage` 防重复；**无 build_anns_d_jsonl.sh 调用**（anns_d 不向量化） |
| `scripts/submit_batch_task.sh` / `poll_batch_tasks.sh` / `finalize_batch_tasks.sh` / `insert_vectors.sh` | `-s <source>` |

> 环境变量注入点沿用 embedding_pipeline 命名（`THOTH_SCRIPTS_DIR`/`THOTH_STATE_DIR`/`THOTH_LOG_DIR`/`THOTH_NOTIFY_BIN`/`THOTH_CRONTAB_BIN`），单测全量桩注入，不触碰真实 crontab / 数据库 / Batch API / 钉钉网络。
