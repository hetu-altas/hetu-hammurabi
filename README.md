# hetu-hammurabi

> *河出图，洛出书，圣人则之。*
>
> 上古伏羲氏时，龙马负图出于黄河，是为**河图**——宇宙秩序的原始图谱，万物规律的终极抽象。它不是律法本身，却是律法得以成文的元秩序。
>
> 而在幼发拉底河畔，**汉谟拉比**（Hammurabi）将散落的习俗与裁决铭刻于玄武岩石柱，颁布了人类历史上第一部成文法典——《汉谟拉比法典》。法律自此不再寄居于君王的记忆，而是立于石上，人人可见，人人可循。他立法，亦执法：法度之内，万物有序；法度之外，寸步难行。
>
> 当东方的秩序图谱遇见西方的立法者，便有了 **河图·汉谟拉比**——宪章编程的驭具模块。
>
> 它将散落的宪章铸成法典，为模型的每一次行为划定边界；把研发流程镌刻为一道工序流水，令每个节点有据可依；以硬门禁执法，不容侥幸，不随心意。它不写业务代码，却让每一行业务代码都行于法度之内；它不产出数据，却让每一次研发沉淀为可循的成卷之律。
>
> 不作预测，不言涨跌，只做模型最忠实的立法者。

---

hetu 系列「宪章编程」harness 模块。通过 opencode 的 Commands / Agents / Skills / Plugins 将研发流程固化为可自动执行的节点流水线：输入**任务书路径或一句话需求**，自动完成 任务书生成(按需) → 分析 → 编码 → 单元测试（硬门禁）→ 代码评审 → 研发日志 → 资产沉淀 → 钉钉通知。

## 宪章编程 · 核心理念

> **人是立法者，AI是执行者。**
> 我们的角色不是"告诉AI做什么"，而是"定义AI不能做什么"。立法者定义边界，执行者在边界内行动。
>
> **宪法高于对话。**
> 一次对话的效力，随着上下文窗口的关闭而消散；一部宪法的效力，随着项目的存续而持续生效。聊出来的叫"感觉"，写进宪法的叫"规矩"。
>
> **约束是资产，不是负担。**
> 一次宪章的修正，触发所有 AI 产出物的自动合规。约束不是限制创造力的枷锁，而是让创造力规模化复制的模具。
>
> **先立法，后编码。**
> 用宪章约束，而非用提示语修补——不要治一个 Bug，要治一类 Bug；不要纠正一个违规，要杜绝一类违规。

> —— 摘引自[《宪章编程宣言》](宪章编程宣言.md)

> 氛围程序员问："AI，你能做什么？"
> 宪章程序员说："AI，在我的规矩里，你只能这么做。"

---

## 生态定位

> **开源 harness + 国产模型**：行政机构与执行官员均可替换，唯宪法不灭。

- **执行载体**：基于开源 agent harness 构建，当前适配 [opencode](https://opencode.ai)（≥ 1.16）；**后续将适配更多国产 harness**，配置层（`.opencode/`）随目标 harness 迁移即可
- **模型**：兼容国产模型（DeepSeek、Qwen、GLM、Kimi 等），通过 harness 的 provider 配置接入，无需改宪章
- **架构解耦**：宪章（`constitution/`）与模型、harness 完全解耦——换 harness 只迁移编排层，换模型只改 provider 配置，**宪章零改动**
- 呼应[《宪章编程宣言》](宪章编程宣言.md)信条四："工具可以换，模型可以换，宪法不灭，系统永生。"

---

## 开源适配（部署前必读）

仓库内所有路径均为**相对路径约定**，部署时按你的实际目录布局调整：

| 需自行调整的项 | 当前约定 | 说明 |
|---------------|---------|------|
| 共享 venv | `../venv-hetu/bin/python` | 约定共享 venv 与各项目同父目录；不同布局请替换 `.opencode/` 与 `constitution/` 中的引用 |
| 日志根目录 | `../logs/hetu-altas/` | 约定日志根与各项目同父目录（见 `constitution/log/log.md`） |
| 公共工具项目 | `../hetu-aether/`（示例名） | 编码/测试/通知节点引用公共工具项目，改名请同步替换 `.opencode/` 中的引用 |
| 业务项目名 | `hetu-mercury` / `hetu-thoth`（示例名） | 资源地图（`docs/资源地图.md`）与宪章中的示例项目名，按实际替换 |

> 提示：`hetu-aether/mercury/thoth` 为河图体系的示例命名，可整体保留或替换为你自己的项目命名。

## 目录结构

```
.
├── .opencode/
│   ├── commands/
│   │   └── dev.md                     # /dev 入口命令（任务书路径 或 一句话需求）
│   ├── agents/
│   │   ├── charter-orchestrator.md    # 主编排代理（primary，节点 -1~7 调度）
│   │   ├── charter-taskwriter.md      # 节点-1 任务书生成（一句话需求）
│   │   ├── charter-analyst.md         # 节点1 分析 → 实施计划
│   │   ├── charter-coder.md           # 节点2 编码
│   │   ├── charter-tester.md          # 节点3 单元测试（硬门禁）
│   │   ├── charter-reviewer.md        # 节点4 代码评审（APPROVE/REVISE）
│   │   ├── charter-logger.md          # 节点5 研发日志
│   │   ├── charter-assetter.md        # 节点6 资产沉淀（docs 新增/更新）
│   │   └── charter-notifier.md        # 节点7 钉钉通知
│   ├── skills/
│   │   ├── charter-taskbook/SKILL.md  # 需求→任务书生成
│   │   ├── charter-analysis/SKILL.md  # 资源匹配（接口/DDL/参考代码）
│   │   ├── charter-coding/SKILL.md    # 编码宪章（引用 coding.md）
│   │   ├── charter-testing/SKILL.md   # 单测宪章（引用 unit_test.md）
│   │   ├── charter-logging/SKILL.md   # 研发日志规范
│   │   └── charter-assets/SKILL.md    # 资产沉淀（新增/更新判定）
│   └── plugin/
│       └── charter-gate.ts            # 硬约束插件（测试门禁/数据安全/密钥脱敏/资产登记）
├── constitution/                      # 通用宪章规范（唯一权威，各项目不再各自维护）
│   ├── constitution.md                # 顶层宪法（13 章）
│   └── coding/ unit_test/ log/ project/ tdengine/ milvus/ task_split/   # 子规范
├── docs/hetu-aether|mercury|thoth/    # 归集自各项目的文档
├── scripts/
│   └── install_harness.sh             # 软链 harness 到同级 hetu-* 项目
├── templates/
│   └── task_book.md                   # 任务书模板
```

## 快速开始

体系完整说明文档见 [docs/harness/](docs/harness/README.md)（总览 / 工作流编排 / 代理与技能 / 门禁与硬约束 / 资产体系 / 扩展维护）；新手上路先看[《快速上手指南》](快速上手指南.md)。

1. 安装 harness 到各业务项目：

```bash
bash scripts/install_harness.sh
```

2. 准备输入（二选一）：
   - 按 `templates/task_book.md` 编写任务书，放入业务项目（如 `hetu-thoth`）的 `opencode_schedule/YYYYMMDD/<YYYYMMDD>任务N<名称>/` 任务目录下
   - 或直接用一句话需求，由系统自动生成任务书（节点 -1）

3. 任务书编写前按 `constitution/task_split/task_split.md` 评估任务粒度：超限（> 4000 行）任务先按依赖拆分为多个任务书。

4. 在业务项目目录启动 opencode，执行：

```
/dev <任务书路径 或 一句话需求>
```

编排代理会自动按节点执行并在任务目录 `opencode_schedule/<YYYYMMDD>/<任务目录>/研发流程状态.md` 固化每个节点的状态。

## 流程节点

| 节点 | 代理 | 产出 | 门禁 |
|------|------|------|------|
| -1 任务书生成 | charter-taskwriter | `任务N<名称>.md` | 仅一句话需求时执行 |
| 0 校验 | charter-orchestrator | 任务书/宪章/输出目录确认 | - |
| 1 分析 | charter-analyst | `实施计划.md` | - |
| 2 编码 | charter-coder | 源码/脚本/依赖 | - |
| 3 单元测试 | charter-tester | `unit_test/test_*_result.txt` + `.gate.json` | 硬门禁：必须全部通过并写入 `.gate.json`，失败回节点2，最多3轮 |
| 4 代码评审 | charter-reviewer | `评审报告.md` | APPROVE 才放行，REVISE 回节点2，最多2轮 |
| 5 研发日志 | charter-logger | `任务N研发日志.md` | 仅当节点3、4通过（charter-gate 硬拦截） |
| 6 资产沉淀 | charter-assetter | `docs/hetu-<项目>/**` 新增/更新 | 仅当节点3、4通过 |
| 7 通知 | charter-notifier | 钉钉完成通知 | 仅当节点3、4通过（charter-gate 硬拦截） |

## 产出目录（任务目录）

每个任务的中间产物按任务书建目录归档，同日多任务互不干扰：

```
opencode_schedule/<YYYYMMDD>/
└── <YYYYMMDD>任务N<名称>/          # 任务目录（以任务书名去掉 .md 命名）
    ├── <YYYYMMDD>任务N<名称>.md    # 任务书（输入，或节点-1 生成）
    ├── 实施计划.md                  # 节点1
    ├── .gate.json                   # 节点3（硬门禁状态）
    ├── 评审报告.md                  # 节点4
    ├── 任务N研发日志.md             # 节点5
    └── 研发流程状态.md              # 全流程（编排器维护）
```

## 硬约束（charter-gate 插件）

`.opencode/plugin/charter-gate.ts` 提供 4 项硬约束：

1. **测试门禁**：`.gate.json` 缺失或 `test_passed=false` 时，写入（`write`/`edit`/`apply_patch` 或 bash 重定向）研发日志/流程状态、钉钉通知 bash 调用一律被阻断；**读取不受限**
2. **数据安全**：`rm -rf` / `DROP` / `DELETE FROM` / `TRUNCATE` / `drop_collection` 必须显式带 backup/备份
3. **密钥脱敏**：用户消息中的明文凭据（sk-、Bearer、token/password 等）自动脱敏并告警
4. **资产登记一致性**：`docs/hetu-*/` 新增/修改未登记到 `docs/资源地图.md` 时告警

## 维护

- 宪章内容修改后，对应 Skill 直接引用 `constitution/` 下的源文件，无需改动。
- 新增流程节点：在 `.opencode/agents/` 新增子代理并更新 `charter-orchestrator.md` 的流程定义。
- 修改硬约束：编辑 `.opencode/plugin/charter-gate.ts`（hook 里 `throw` 即硬阻断）。
- 配置变更（agents/skills/commands/plugin）需**退出并重启 opencode** 生效。

## 开源协议

本项目基于 **MIT License** 开源（[LICENSE](LICENSE)），**商用无任何限制**：

- ✅ 自由使用、复制、修改、合并、发布、再分发、出售
- ✅ 商用、闭源使用均允许，无需付费或署名以外的附加义务
- ✅ 唯一的义务：保留版权声明与本许可声明（随分发附上 LICENSE 即可）
- ❌ 本软件按"原样"提供，作者不对使用后果承担任何责任（免责条款见 LICENSE）

Copyright (c) 2026 hetu-altas

联系邮箱：**hetu_altas@163.com**
