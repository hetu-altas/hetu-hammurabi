# 运行时拓扑解析机制设计（topology.md）

> 本文阐述 harness 体系的「运行时项目拓扑解析」机制：`.harness-env` 字段契约、回退规则、`scripts/harness_topology.py` 纯函数库、安装流程与门禁联动。
> 相关实现：`scripts/harness_topology.py`、`scripts/install_harness.sh`、`.opencode/plugin/charter-gate.ts`。
> 20260809 任务1（harness 体系泛化）新增登记。
> 20260815 任务2 更新：门禁插件（opencode 入口）升级为 env 解析 + 三钩子委托，opencode 与 DSH 双体系并行（见「六、门禁联动」）。

## 一、背景与动机

改造前，harness 体系（9 个代理提示词、6 个技能、安装脚本、资源地图、宪法、模板、harness 文档）中大量**写死具体项目名与相对路径**：

- `../hetu-hammurabi/constitution/...`、`../hetu-hammurabi/docs/资源地图.md`（跨项目引用写死宿主名）
- `hetu-aether`、`hetu-mercury`、`hetu-thoth`（业务项目清单与工具项目写死）
- `../venv-hetu/bin/python`（共享环境写死）

由此产生三个问题：

1. **新平级项目无法直接获得 harness 支持**（如 2026-08-09 新建的 hetu-sybil），安装脚本宿主判定写死、软链范围不全；
2. **资源匹配规则只认 mercury/thoth，不通用**（charter-analysis / charter-taskbook 技能板块路径写死）；
3. **软链范围不全**（`package.json` / `package-lock.json` 不在软链范围，各项目手工拷贝，版本易漂移——实测 mercury 的 `@opencode-ai/plugin` 曾漂移为 1.18.11 而宿主为 1.18.10）。

本机制的目标：将全部写死路径改为「运行时解析 + 回退规则」，使 harness 支持所有与宿主平级的 hetu-* 项目。

## 二、.harness-env 字段契约

`.opencode/.harness-env` 由 `install_harness.sh` 每次执行时**静态重写**生成（文件头注明「由 install_harness.sh 自动生成，勿手改」），含绝对路径、**禁止入库**（install 时自动追加各项目 `.opencode/.gitignore` 忽略）：

```bash
# 由 install_harness.sh 自动生成，勿手改
PROJECT_NAME=<当前项目名，如 hetu-sybil>
PROJECT_DIR=<当前项目绝对路径>
WORKSPACE_DIR=<同父目录（所有 hetu-* 平级项目的根）绝对路径>
HARNESS_DIR=<harness 宿主项目绝对路径>
AETHER_DIR=<公共工具项目绝对路径，缺省回退：同父目录下 hetu-aether>
VENV_BIN=<共享虚拟环境 python 绝对路径，缺省回退：同父目录下 venv-hetu/bin/python>
```

约定：

| 字段 | 含义 | 缺省回退 |
|------|------|---------|
| PROJECT_NAME | 当前项目名（目录 basename） | 当前工作目录 basename |
| PROJECT_DIR | 当前项目绝对路径 | — |
| WORKSPACE_DIR | 同父目录（所有 hetu-* 平级项目的根） | 当前项目父目录 |
| HARNESS_DIR | harness 宿主项目绝对路径 | 见「三、回退规则」① |
| AETHER_DIR | 公共工具项目绝对路径 | 见「三、回退规则」② |
| VENV_BIN | 共享虚拟环境 python 绝对路径 | 见「三、回退规则」③ |

- 路径含空格时字段值以双引号包裹（`KEY="value with space"`），解析方需剥离引号；
- AETHER_DIR / VENV_BIN 在对应目录缺失时写**空值**并附 `#` 注释说明，由读取方按回退规则查找。

## 三、回退规则

`.harness-env` 缺失或字段缺失时，agents/skills/插件按以下规则动态查找（写入全部代理与技能的统一措辞模板）：

1. **宿主定位**：同父目录（WORKSPACE_DIR）下同时含 `constitution/constitution.md` + `.opencode/agents/` + `docs/资源地图.md` 的 `hetu-*` 目录为 harness 宿主 → HARNESS_DIR；
2. **公共工具**：同父目录下 `hetu-aether` 为公共工具项目 → AETHER_DIR；
3. **共享环境**：同父目录下 `venv-hetu/bin/python` 为共享环境 → VENV_BIN；
4. **项目名**：当前工作目录 basename 为 PROJECT_NAME。

## 四、harness_topology.py 函数说明

`scripts/harness_topology.py` 为**纯函数库**（无文件写入、路径参数化、无副作用），供 install 脚本调用与单元测试断言：

| 函数 | 签名 | 行为 |
|------|------|------|
| `detect_host_dir` | `(workspace_dir: str) -> str` | 判定宿主：`hetu-*` 目录且同时含三要件；多命中取要件数最多者，同级按目录名升序取第一个（确定性）；无命中抛 `ValueError`（含候选列表） |
| `list_target_projects` | `(workspace_dir, host_dir, extra=None) -> (targets, skipped)` | 返回同父目录下 `hetu-*` 目录（非宿主）按名称排序的绝对路径列表；`extra` 追加指定项目（非 hetu-* 前缀亦可），不存在时记入 skipped |
| `resolve_aether_dir` | `(workspace_dir) -> str \| None` | 返回 `workspace_dir/hetu-aether`（目录存在时），否则 None |
| `resolve_venv_bin` | `(workspace_dir) -> str \| None` | 返回 `workspace_dir/venv-hetu/bin/python`（存在时），否则 None |
| `build_env_content` | `(project_dir, workspace_dir, host_dir) -> str` | 生成 .harness-env 文本（六字段、绝对路径、头注释；缺失字段写空值并注释） |
| `parse_env_content` | `(text: str) -> dict` | 解析 .harness-env 文本：跳过空行与 `#` 注释、`KEY=VALUE` 拆分、支持引号值、重复键后者覆盖 |

命令行入口（只读）：

```bash
python scripts/harness_topology.py --dump /path/to/project            # 调试输出拓扑解析结果
python scripts/harness_topology.py --json detect-host --workspace <dir>
python scripts/harness_topology.py --json list-targets --workspace <dir> --host <dir> [--extra <name>]
python scripts/harness_topology.py --build-env --project <dir> --workspace <dir> --host <dir>   # 输出 env 文本供脚本重定向
```

## 五、安装流程（install_harness.sh）

`bash scripts/install_harness.sh [<项目名>]`，保持 `set -euo pipefail`：

1. **宿主定位与校验**：脚本自身所在目录即宿主（`$BASH_SOURCE` 定位），调用 `harness_topology.py --json detect-host` 验证满足三要件，防止脚本被拷贝到非宿主目录误用；脚本主体不出现任何具体项目名字面量；
2. **目标范围**：`--json list-targets` 发现同父目录下除宿主外全部 `hetu-*` 项目（+ 可选参数追加指定项目，不存在的在输出中提示忽略）；
3. **逐项目安装**（幂等）：
   - `mkdir -p $proj/.opencode`
   - `--build-env` 生成 `.opencode/.harness-env`（每次重写）
   - `ln -sfn` 软链 `agents` / `commands` / `skills` / `plugin` / `package.json` / `package-lock.json` 共 6 项（`node_modules` **不软链**，各项目自行 `npm install`）
   - 确保 `.opencode/.gitignore` 存在且含 `.harness-env`
4. **宿主自身** `.opencode/.gitignore` 同步追加 `.harness-env`；
5. **输出对照表**：`项目名 → HARNESS_DIR / AETHER_DIR / VENV_BIN` 便于核查。

## 六、门禁联动（charter-gate 插件）

**双体系并行**（20260815 任务2）：opencode 入口（`.opencode/plugin/charter-gate.ts`）与 DSH 入口（`harness/plugins/charter-gate.ts`）并行维护，两插件均为薄适配层，判定逻辑唯一在 Python 核心（`harness/core/cli.py` → gate.py / redact.py / assets_check.py + `gate_rules.yaml`）。

opencode 入口 `.opencode/plugin/charter-gate.ts` 的钩子实现（resolveEnv 解析 + 三钩子委托）：

- **resolveEnv**：优先读当前项目 `.opencode/.harness-env` 的 `HARNESS_DIR` / `VENV_BIN` 字段（K=V 逐行解析、跳过注释、剥离引号）；`.harness-env` 缺失或字段缺失时回退——`VENV_BIN` → `python3`，`HARNESS_DIR` → 同父目录下同时含 `constitution/constitution.md` + `.opencode/agents/` + `docs/资源地图.md` 三要件的 `hetu-*` 目录（宿主自身三要件齐全时命中自身，如 hetu-hammurabi）→ 仍无则当前项目自身。
- **tool.execute.before**（write/edit/apply_patch/bash）→ 委托 `decide`（`--task-dir`/`--run-id` 从工具参数按 `opencode_schedule/<YYYYMMDD>/<任务目录>` 路径模式推导）；`blocked=true` 抛错硬拦截，GATE_STALE 附 re-seal 续签提示；判定子进程异常 **fail-closed** 拦截 + error 告警。
- **chat.message** → 委托 `redact`；`hits>0` 替换 text parts + warn 告警（含 sessionID）；调用失败返回原文 + error 告警。
- **tool.execute.after**（write/edit 且目标在 `docs/hetu-*/`）→ 委托 `assets-check`（`--project-dir` 传当前项目目录）；`ok=false` → warn 软告警（不阻断）。

> 插件改动后需**重启 opencode** 生效（配置启动时加载、不热更新）。

## 七、扩展点登记（20260809 任务1 决策预留，本次未实现）

| 扩展点 | 现状 | 未来方案 |
|--------|------|---------|
| venv 按项目差异 | 仅默认回退（同父目录 `venv-hetu`） | .harness-env 预留按项目覆盖字段或独立生成 |
| 多宿主 / 歧义场景 | `detect_host_dir` 多命中取要件最完整者 + 名称排序（确定性） | 如需显式指定宿主，可扩展 install 参数或 env 字段 |
| 跨目录部署 | FAQ Q4：手动复制/软链 `.opencode` + 自定义 `.harness-env` | 可提供 `--host <path>` 显式宿主参数 |
| node_modules 策略 | 不软链，各项目 `npm install`（避免二进制跨项目软链解析风险） | 如出现版本频繁漂移，可评估统一软链 + 锁定版本 |

## 八、FAQ

**Q1：.harness-env 会被误提交入库吗？**
A：不会。install 脚本自动在各项目（含宿主自身）`.opencode/.gitignore` 追加 `.harness-env`；该文件含绝对路径，只在本机生效。

**Q2：业务项目手工改了 .harness-env 会怎样？**
A：下次执行 install 脚本会被静态重写覆盖（文件头已注明勿手改）；如需自定义，请走「七、扩展点」或 FAQ Q4 的跨目录方案。

**Q3：新增一个 hetu-* 项目需要做什么？**
A：三步——创建项目目录并初始化 → 宿主内运行 `bash scripts/install_harness.sh <项目名>` → 重启 opencode 验证 `/cc`。

**Q4：detect_host_dir 判错宿主怎么办？**
A：判定基于三要件（`.opencode/agents/` + `constitution/constitution.md` + `docs/资源地图.md`），要件齐全的项目才可作宿主；多候选时取要件最完整者、同级按名称升序，行为确定。出现歧义说明多个项目同时具备三要件，请按「七、扩展点」显式指定。

**Q5：改了这个机制需要重新装 harness 吗？**
A：需要。拓扑机制改动（topology.py / install_harness.sh / 代理技能措辞）后，执行一次 `bash scripts/install_harness.sh` 刷新各项目 `.harness-env` 与软链，并重启 opencode。
