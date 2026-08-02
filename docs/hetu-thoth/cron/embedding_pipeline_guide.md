# embedding 多数据源定时向量化入库流水线指南

> 更新日期：2026-08-01（任务2 泛化改造，原 major_news 专用版重命名泛化） | 模块：`scripts/embedding_pipeline.sh`、`scripts/embedding_cron_install.sh`
> 所属项目：hetu-thoth | 适用数据源：news / major_news / cctv_news / irm_qa_sh / irm_qa_sz（Milvus collection `thoth_knowledge`，向量维数 1024）

---

## 一、概述

hetu-thoth 已具备多数据源完整向量化流水线组件（生成 JSONL → 提交 DashScope Batch → 轮询 → 下载结果 → 入库 Milvus），但此前均需人工按步骤调用。本指南对应的两套脚本将其编排为「每日 23:30 自动执行」的定时任务，支持 5 种数据源逐源独立执行：

| 脚本 | 职责 |
|------|------|
| `scripts/embedding_pipeline.sh` | 主流水线：5 源循环 × 4 个阶段（每源 5 条命令），任一步骤失败不影响同源后续步骤、任一源失败不影响其余源，最终按「源 × 步骤」二维汇总并可选钉钉告警；支持 `--poll-only` 模式（仅轮询下载入库） |
| `scripts/embedding_cron_install.sh` | cron 自管理：安装 / 卸载 / 状态查询，共两条自动管理条目——23:30 全流程 + 02:00 轮询补齐；自动迁移任务1 已安装的旧版 major_news 标记条目 |

### 1.1 流水线 4 个阶段 / 5 条命令（复用既有组件，只调用不修改）

| 阶段 | 调用 | 说明 |
|------|------|------|
| ① 生成 JSONL | `bash scripts/build_<source>_jsonl.sh <start> <end>` | 按源生成增量 JSONL（pipeline 统一显式传区间，消除各 build 脚本缺省起点差异）；内置 `_check_existing_coverage` 日期覆盖去重，重复运行不重复产出 |
| ② 提交 Batch | `bash scripts/submit_batch_task.sh -s <source>` | 只处理 `status='pending'` 记录；同 source+日期范围已有 `completed` 记录则跳过（防重复提交/重复计费） |
| ③ 轮询 + 下载 | `bash scripts/poll_batch_tasks.sh -s <source>` 后 `bash scripts/finalize_batch_tasks.sh -s <source>` | poll 同步运行中任务状态；finalize 处理所有 `finalizing` 记录（状态机保证不重复下载）。两个子命令各自独立记录结果，共 2 条命令 |
| ④ 入库 Milvus | `bash scripts/insert_vectors.sh -s <source>` | 自动拉取 `status='completed'` 且 `milvus_status IN ('pending','failed')` 的任务；插入前按 ID 去重（幂等） |

> 步骤③④天然覆盖「历史已完成未下载/未入库」的遗留任务（Batch 为异步，23:30 提交的新任务通常当日不能完成），跨天自动续跑，无需专门补数逻辑。

### 1.2 轮询补齐模式（--poll-only，凌晨 02:00 定时）

Batch 向量化为**异步**：23:30 提交的新任务通常需要数小时才能完成，当日无法下载入库。为此 cron 在**每天 02:00** 追加执行一次 `--poll-only` 模式——跳过 ①生成 JSONL 与 ②提交 Batch，仅对全部选中源执行 ③轮询 + ④下载 + ⑤入库 Milvus（每源 3 条命令），将当晚已完成的任务结果补齐入库。

```bash
bash scripts/embedding_pipeline.sh --poll-only                      # 仅轮询下载入库（全 5 源）
bash scripts/embedding_pipeline.sh --poll-only -s news,cctv_news    # 指定源
bash scripts/embedding_pipeline.sh --poll-only --dry-run            # 演练（15 条命令）
```

行为约定：
- 不写状态文件（状态文件仅由 23:30 全流程模式的步骤①维护）、不计算区间（汇总显示 N/A）；
- 汇总中 ①生成JSONL / ②提交Batch 显示「未执行」；
- 与 `--sources/-s`、`--notify`、`--dry-run` 可自由组合；任一步骤失败不影响同源后续步骤、任一源失败不影响其余源（同全流程模式）。

### 1.3 状态机与关键字段（既有定义）

- `embedding_batch_task`：`pending → uploaded → validating → in_progress → finalizing → completed / failed / expired / cancelled`；入库状态字段 `milvus_status`（pending/completed/failed）
- `custom_id` 前缀按源：`news_` / `major_news_` / `cctv_news_` / `irm_qa_sh_` / `irm_qa_sz_`；Milvus collection：`thoth_knowledge`；向量维数 1024
- 数据目录：JSONL 输入 `/mnt/f/batch_jsonl/<source>/<YYYYMMDD>/`，结果输出 `/mnt/f/embedding_jsonl/<source>/<YYYYMMDD>/`（目录配置见 `conf/dir_conf.json`，位于 hetu-thoth 项目 `conf/` 下）

---

## 二、安装与卸载 cron

### 2.1 安装（--install，默认动作）

```bash
bash scripts/embedding_cron_install.sh --install
# 或直接：
bash scripts/embedding_cron_install.sh
```

安装逻辑：

1. 先备份当前 crontab 至 `/mnt/e/logs/embedding_pipeline/crontab.bak.<时间戳>`（增删改前先备份；crontab 无条目或命令不可用时按空备份处理，备份目录不可写则中止退出 1）；
2. **旧版自动迁移**：若检测到任务1 已安装的旧标记 `# hetu-thoth major_news 每日向量化入库（自动管理，勿手改）`，先按卸载逻辑删除旧标记与其执行条目（写回前备份已含旧状态），保证 crontab 不残留两套、旧条目不会每天调用已删除脚本而报错；
3. **幂等 / 升级补装**：若 crontab 已含新版自动管理标记：检查 02:00 轮询条目（`--poll-only`）是否已存在——已存在则提示「已安装」退出（幂等）；缺失（旧版仅 23:30 一条的安装状态）则**升级补装** 02:00 轮询条目后退出；
4. 全新安装：原样保留全部既有条目，末尾追加标记注释与两条执行条目后写回，写回后校验标记已写入（校验失败退出 1）。写回内容基于**写回前一刻读取的实时 crontab**（命令替换先完整读取再追加，非基于安装开始时的备份快照），避免覆盖写回前发生的并发变更。

固定条目（注意 `%` 已转义为 `\%`，否则 crontab 将 `%` 解释为换行/命令分隔导致条目非法）：

```cron
# hetu-thoth embedding 每日向量化入库（自动管理，勿手改）
30 23 * * * bash /mnt/d/workspace/hetu-altas/hetu-thoth/scripts/embedding_pipeline.sh >> /mnt/e/logs/embedding_pipeline/cron_$(date +\%Y\%m\%d).log 2>&1
0 2 * * * bash /mnt/d/workspace/hetu-altas/hetu-thoth/scripts/embedding_pipeline.sh --poll-only >> /mnt/e/logs/embedding_pipeline/cron_poll_$(date +\%Y\%m\%d).log 2>&1
```

> 条目中的脚本绝对路径由安装脚本按自身所在位置自动推导（`$DIR/scripts/embedding_pipeline.sh`），非硬编码；若项目整体迁移部署位置，请先卸载后重新安装，以刷新条目中的路径。
> **注意**：标记注释与其下执行条目（1~2 条）必须成块连续紧邻（勿手工拆散），卸载/迁移按「标记行 + 其后连续的全部 embedding 执行条目行」删除。

### 2.2 卸载（--uninstall）

```bash
bash scripts/embedding_cron_install.sh --uninstall
```

仅删除带自动管理标记的注释行与其紧邻的执行条目行（**新版与旧版标记均识别删除**，兼容任务1 残留），其余条目原样保留，同样先备份。

### 2.3 状态查询（--status）

```bash
bash scripts/embedding_cron_install.sh --status; echo $?
# 已安装（新版或旧版标记任一命中）：打印命中条目，返回码 0
# 未安装：返回码 1
```

### 2.4 重装（卸载后再安装）

`--install` 支持重复执行（已安装时幂等跳过）与卸载后重新安装；若曾手工改动条目导致标记丢失，重新 `--install` 会追加新条目（人工核实无重复即可）。

---

## 三、手动运行与演练

```bash
# 正常执行（cron 调用形态，默认全部 5 源）
bash scripts/embedding_pipeline.sh

# 只处理指定数据源（逗号分隔，非法源退出码 2）
bash scripts/embedding_pipeline.sh -s news,major_news
bash scripts/embedding_pipeline.sh --sources cctv_news,irm_qa_sh,irm_qa_sz

# 演练：仅打印将执行的命令，不执行、不写状态文件、不发通知
bash scripts/embedding_pipeline.sh --dry-run

# 指定运行日期（影响日志文件名与默认区间终点）
bash scripts/embedding_pipeline.sh --date 2026-08-01

# 覆盖步骤①数据区间（对全部选中源生效；补历史数据，如首次上线补 2026-05-01 至今）
bash scripts/embedding_pipeline.sh --start-date 2026-05-01 --end-date 2026-08-01

# 关闭失败钉钉告警
bash scripts/embedding_pipeline.sh --notify off
```

### 3.1 参数一览

| 参数 | 默认 | 说明 |
|------|------|------|
| `-s, --sources <列表>` | 全部 5 源 | 逗号分隔的数据源过滤（`news,major_news,cctv_news,irm_qa_sh,irm_qa_sz`）；含白名单外源（如 `npr`）退出码 2 并打印合法源列表；合法源按传入顺序去重（保留首现），空值/空结果回退全部 5 源 |
| `--dry-run` | 关 | 演练模式：打印选中源的全部命令（默认 5 源 × 5 条 = 25 条）与 DRY-RUN 汇总，无任何实际副作用 |
| `--date YYYY-MM-DD` | 系统当天 | 运行日期；决定日志文件名与默认区间终点 |
| `--start-date / --end-date` | 状态文件驱动 | 显式覆盖步骤①数据区间（必须成对、且起点不得晚于终点，否则退出码 2；对全部选中源生效） |
| `--notify on\|off` | on | 失败时钉钉告警开关；dry-run 一律不发送 |

退出码：任一源任一步骤失败 → 1；全部成功或 dry-run → 0；参数错误 / 非法数据源 → 2。

### 3.2 数据区间计算规则（calc_range，按源独立计算）

| 场景 | 步骤①区间 |
|------|-----------|
| 显式传 `--start-date/--end-date` | 以显式值为准（优先级最高，全部选中源同一区间） |
| 该源状态文件存在且合法（如 `last_run.news.date` 内容为 `2026-07-31`） | `2026-08-01`（last+1 天）~ 当天 |
| 该源状态文件缺失 / 内容非法（该源首次运行） | 当天单日（避免一次性全量提交造成 Batch 拥堵与费用风险） |

每源生成成功（退出码 0，含 0 文件场景）后**仅更新该源状态文件**为本次 END 日期，次日自动进入增量、各源进度互不影响。需要补历史数据时用 `--start-date` 显式触发一次（对所有选中源生效）。

---

## 四、日志与状态文件

| 文件 | 说明 |
|------|------|
| `/mnt/e/logs/embedding_pipeline/<YYYYMMDD>.log` | 流水线步骤日志（每源每步一行 + 二维汇总块），追加写入 |
| `/mnt/e/logs/embedding_pipeline/cron_<YYYYMMDD>.log` | crontab 重定向输出（23:30 全流程 cron 调用 stdout/stderr） |
| `/mnt/e/logs/embedding_pipeline/cron_poll_<YYYYMMDD>.log` | crontab 重定向输出（02:00 轮询补齐 cron 调用 stdout/stderr） |
| `/mnt/e/logs/embedding_pipeline/last_run.<source>.date` | 按源增量区间状态文件（内容为该源上次生成成功 END 日期；5 源各一，互不覆盖） |
| `/mnt/e/logs/embedding_pipeline/crontab.bak.<时间戳>` | crontab 安装/卸载前备份 |

日志行格式：`[YYYY-MM-DD HH:MM:SS] [<源>_<步骤名>] SUCCESS|FAILURE|DRY-RUN | 描述`（步骤名带源前缀，如 `[news_生成JSONL]`）；运行结束追加汇总块（每源一行 5 步状态 + 失败源明细 + 总体结论 + 各源区间）。

日志按日命名，建议保留最近 30 天（与 hetu 系列日志留存惯例一致）。

### 4.1 旧版（任务1 major_news 专用）迁移说明

| 项 | 迁移动作 |
|------|------|
| crontab 旧标记条目 | `embedding_cron_install.sh --install` 自动迁移（先卸旧再装新）；`--uninstall`/`--status` 兼容识别旧标记 |
| 旧状态文件 `/mnt/e/logs/major_news_cron/last_run.date` | 编码节点执行一次性手动迁移：`mkdir -p /mnt/e/logs/embedding_pipeline && mv /mnt/e/logs/major_news_cron/last_run.date /mnt/e/logs/embedding_pipeline/last_run.major_news.date`（major_news 源增量进度不丢；源文件不存在则视为首次运行，跳过） |
| 旧日志目录 `/mnt/e/logs/major_news_cron/` 历史日志 | 保留不清理（删除属破坏性操作，需人工确认） |

---

## 五、钉钉告警

- 存在失败步骤且 `--notify on`（默认）且非 dry-run 时，通过 hetu-aether `utils/util_dingtalk.py` 的 `send_text` 发送失败汇总（**含失败源 × 步骤明细**、运行日期、日志路径）；
- 全部成功不发送（避免深夜噪音）；dry-run 不发送；`--notify off` 不发送；
- 告警发送失败仅打印 WARNING，不影响主流程退出码。

> **运维须知**：`finalize_batch_tasks.sh`（下载结果）成功完成时，其既有实现会自行发送一条钉钉成功通知（`submit_batch_embedding.py` 内建 `send_markdown`，属既有行为，本流水线只调用不修改、无法拦截）。因此「下载结果成功」场景可能出现一条来源为 finalize 的通知，与流水线自身的告警规则无关，属预期现象。

---

## 六、故障排查

| 现象 | 排查步骤 |
|------|---------|
| cron 未执行 | `crontab -l` 检查条目是否被误删；查看 `cron_<日期>.log` 有无报错；确认 `/mnt/e/logs/embedding_pipeline/` 目录可写 |
| 某源步骤①重复产出 | 内置 `_check_existing_coverage` 会跳过同 source+日期范围已有 active 记录的任务；如确认重复，检查该源 `last_run.<source>.date` 是否被手工改小 |
| 某源数据区间不对 | 检查该源 `last_run.<source>.date` 内容与 `--start-date/--end-date` 是否误传；状态文件内容非法时自动退化为当天单日；显式区间对全部选中源生效（无法按源单独指定） |
| 某源失败但其余源正常 | 属设计行为（源间容错）：汇总与钉钉告警含失败源明细；按「退出码 + 日志关键字」双重核对（可 grep 当日日志中的 FAILURE/ERROR 字样定位失败源与步骤） |
| 步骤②③④退出码 0 但疑似漏处理 | 既有实现中单任务失败仅 `logger.error + continue`，进程仍以 0 退出（仅 DB 连接失败、参数错误等场景才非 0）；此时按「退出码 + 日志关键字」双重核对 |
| 想重跑某源某天数据 | `echo 2026-07-30 > /mnt/e/logs/embedding_pipeline/last_run.<source>.date` 后运行流水线（该源步骤①从 07-31 起增量），或直接 `--start-date/--end-date` 指定区间（全部选中源生效） |
| 钉钉没收到告警 | 确认 `--notify` 未设为 off、存在 FAILURE 步骤、`~/.config/opencode/dingtalk-notify.json` 配置有效 |

---

## 七、环境变量注入点（测试/运维用）

生产环境不设置，均走默认值；单元测试通过注入桩实现隔离：

| 变量 | 默认 | 用途 |
|------|------|------|
| `THOTH_SCRIPTS_DIR` | `<项目>/scripts` | 步骤脚本目录（测试注入桩脚本） |
| `THOTH_STATE_DIR` | `/mnt/e/logs/embedding_pipeline` | 增量状态目录（内部按源存 `last_run.<source>.date`；任务1 的 `THOTH_STATE_FILE` 单文件注入点已废弃） |
| `THOTH_LOG_DIR` | `/mnt/e/logs/embedding_pipeline` | 日志/备份目录 |
| `THOTH_NOTIFY_BIN` | `<父目录>/venv-hetu/bin/python` | 钉钉通知执行器（测试注入桩，避免真实网络请求） |
| `THOTH_CRONTAB_BIN` | `crontab` | crontab 命令（cron 管理脚本，测试注入桩） |
