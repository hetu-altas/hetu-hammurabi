# hetu-hammurabi

> *河出图，洛出书，圣人则之。*
>
> 上古伏羲氏时，龙马负图出于黄河，是为**河图**——宇宙秩序的原始图谱，万物规律的终极抽象。它不是律法本身，却是律法得以成文的元秩序。
>
> 而在幼发拉底河畔，**汉谟拉比**（Hammurabi）将散落的习俗与裁决铭刻于玄武岩石柱，颁布了人类历史上第一部成文法典——《汉谟拉比法典》。法律自此不再寄居于君王的记忆，而是立于石上，人人可见，人人可循。他立法，亦执法：法度之内，万物有序；法度之外，寸步难行。
>
> 当东方的秩序图谱遇见西方的立法者，便有了 **河图·汉谟拉比**——宪章编程的驭具模块。
>
> 它将散落的宪章铸成法典，为模型的每一次行为划定边界；把研发流程镌刻为七道工序，令每个节点有据可依；以硬门禁执法，不容侥幸，不随心意。它不写业务代码，却让每一行业务代码都行于法度之内；它不产出数据，却让每一次研发沉淀为可循的成卷之律。
>
> 不作预测，不言涨跌，只做模型最忠实的立法者。

---

hetu 系列「宪章编程」harness 模块。通过 opencode 的 Commands / Agents / Skills / Plugins 将研发流程固化为可自动执行的节点流水线：输入任务书，自动完成分析 → 编码 → 单元测试（硬门禁）→ 代码评审 → 研发日志 → 资产沉淀 → 钉钉通知。

> **先立法，后编码。宪法高于对话。约束是资产，不是负担。**
> —— 详见[《宪章编程宣言》](宪章编程宣言.md)，本项目是宪章编程范式的执行机构。

## 目录结构

```
.
├── .opencode/
│   ├── commands/
│   │   └── dev.md                     # /dev <任务书> 入口命令
│   ├── agents/
│   │   ├── charter-orchestrator.md    # 主编排代理（primary）
│   │   ├── charter-analyst.md         # 节点1 分析 → 实施计划
│   │   ├── charter-coder.md           # 节点2 编码
│   │   ├── charter-tester.md          # 节点3 单元测试（门禁）
│   │   ├── charter-reviewer.md        # 节点4 代码评审（APPROVE/REVISE）
│   │   ├── charter-logger.md          # 节点5 研发日志
│   │   ├── charter-assetter.md        # 节点6 资产沉淀（docs 新增/更新）
│   │   └── charter-notifier.md        # 节点7 钉钉通知
│   └── skills/
│       ├── charter-coding/SKILL.md    # 编码宪章（引用 coding.md）
│       ├── charter-testing/SKILL.md   # 单测宪章（引用 unit_test.md）
│       ├── charter-logging/SKILL.md   # 研发日志规范
│       └── charter-assets/SKILL.md    # 资产沉淀（新增/更新判定）
│   └── plugin/
│       └── charter-gate.ts            # 硬约束插件（测试门禁/数据安全/密钥脱敏/资产登记）
├── constitution/                      # 通用宪章规范（唯一权威，各项目不再各自维护）
├── docs/hetu-aether|mercury|thoth/    # 归集自各项目的文档
├── scripts/
│   └── install_harness.sh             # 软链 harness 到同级 hetu-* 项目
├── templates/
│   └── task_book.md                   # 任务书模板
```

## 快速开始

体系完整说明文档见 [docs/harness/](docs/harness/README.md)（总览 / 工作流编排 / 代理与技能 / 门禁与硬约束 / 资产体系 / 扩展维护）。

1. 安装 harness 到各业务项目：

```bash
bash scripts/install_harness.sh
```

2. 按 `templates/task_book.md` 编写任务书，放入业务项目（如 `hetu-thoth`）的 `opencode_schedule/YYYYMMDD/` 下。

3. 在业务项目目录启动 opencode，执行：

```
/dev <任务书路径>
```

编排代理会自动按节点执行并在 `opencode_schedule/<YYYYMMDD>/研发流程状态.md` 固化每个节点的状态。

## 流程节点

| 节点 | 代理 | 产出 | 门禁 |
|------|------|------|------|
| 0 校验 | charter-orchestrator | 任务书/宪章/输出目录确认 | - |
| 1 分析 | charter-analyst | `实施计划.md` | - |
| 2 编码 | charter-coder | 源码/脚本/依赖 | - |
| 3 单元测试 | charter-tester | `unit_test/test_*_result.txt` + `.gate.json` | 硬门禁：必须全部通过并写入 `.gate.json`，失败回节点2，最多3轮 |
| 4 代码评审 | charter-reviewer | `评审报告.md` | APPROVE 才放行，REVISE 回节点2，最多2轮 |
| 5 研发日志 | charter-logger | `任务N研发日志.md` | 仅当节点3、4通过（charter-gate 硬拦截） |
| 6 资产沉淀 | charter-assetter | `docs/hetu-<项目>/**` 新增/更新 | 仅当节点3、4通过 |
| 7 通知 | charter-notifier | 钉钉完成通知 | 仅当节点3、4通过（charter-gate 硬拦截） |

## 硬约束（charter-gate 插件）

`.opencode/plugin/charter-gate.ts` 提供 4 项硬约束：

1. **测试门禁**：`.gate.json` 缺失或 `test_passed=false` 时，写入研发日志/流程状态、钉钉通知的 bash 调用一律被阻断
2. **数据安全**：`rm -rf` / `DROP` / `DELETE FROM` / `TRUNCATE` / `drop_collection` 必须显式带 backup/备份
3. **密钥脱敏**：用户消息中的明文凭据（sk-、Bearer、token/password 等）自动脱敏并告警
4. **资产登记一致性**：`docs/hetu-*/` 新增/修改未登记到 `docs/资源地图.md` 时告警

## 维护

- 宪章内容修改后，对应 Skill 直接引用 `constitution/` 下的源文件，无需改动。
- 新增流程节点：在 `.opencode/agents/` 新增子代理并更新 `charter-orchestrator.md` 的流程定义。
- 修改硬约束：编辑 `.opencode/plugin/charter-gate.ts`（hook 里 `throw` 即硬阻断）。
