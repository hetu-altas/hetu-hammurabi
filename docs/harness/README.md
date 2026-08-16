# hetu-hammurabi · 宪章编程 Harness 体系总览

> 本目录是 hetu 系列「宪章编程」harness 体系的完整说明文档，共 6 篇：

| 文档 | 内容 |
|------|------|
| [README.md](README.md) | 体系总览：定位、架构、组件清单、设计理念（本文） |
| [workflow.md](workflow.md) | 工作流编排：节点流水线（含任务书生成）、门禁链、回退机制、状态固化 |
| [agents-skills.md](agents-skills.md) | 代理与技能体系：编排代理、节点子代理、Skill 按需加载 |
| [gates.md](gates.md) | 门禁与硬约束：软/硬约束矩阵、charter-gate 插件 |
| [assets.md](assets.md) | 宪章与资产体系：通用宪章、资源地图、资产沉淀 |
| [extend.md](extend.md) | 扩展与维护：新增节点、修改宪章、安装分发、FAQ |

---

## 一、定位

`hetu-hammurabi`（harness 宿主）是 hetu 系列的 **harness（驭具）模块**：通过 opencode 的 Commands / Agents / Skills / Plugins 原生能力，叠加 `.harness-env` 运行时拓扑解析（宿主/公共工具/共享环境定位，见 [topology.md](topology.md)），把「宪章约束 + 研发流程节点 + 硬性门禁 + 资产沉淀」固化为可自动执行的 AI coding 流水线。

核心主张：

> **输入一份任务书，模型自动按固化节点完成研发，无需过多人工干预。**

## 二、架构

```
                        ┌──────────────────────────────┐
  用户输入任务书          │   charter-orchestrator        │
  /cc <任务书> ────────▶ │   （主编排代理，节点 -1~7 调度）     │
                        └───┬──┬──┬──┬──┬──┬──┬──┬───┘
                            │  │  │  │  │  │  │  │
            ┌───────────────┘  │  │  │  │  │  │  └──────────┐
            ▼                  ▼  ▼  ▼  ▼  ▼  ▼             ▼
        ┌────────┐  ┌────────┐  ...节点子代理...   ┌────────┐  ┌────────┐
        │ 宪章    │  │ 资源地图 │                     │ 硬门禁   │  │ 资产沉淀 │
        │(约束层) │  │(可寻址层)│                     │(插件层)  │  │(反哺层) │
        └────────┘  └────────┘                     └────────┘  └────────┘
```

三层约束共同工作：

| 层 | 载体 | 作用 |
|----|------|------|
| **宪章层（软约束）** | `constitution/` + Skills | 约束模型"怎么做"：编码、单测、日志、TDengine、Milvus 等规范 |
| **流程层（编排）** | `charter-orchestrator` + 节点子代理 | 约束"按什么顺序做"：节点 -1~7 流水线与门禁链 |
| **插件层（硬约束）** | `charter-gate` 插件 | 约束"不能做什么"：确定性拦截，不依赖模型自觉 |
| **拓扑层（定位）** | `scripts/harness_topology.py` + 各项目 `.opencode/.harness-env` | 约束"资源在哪"：宿主/公共工具/共享环境运行时解析，agents/skills/插件先读 .harness-env，缺失时按回退规则动态查找（详见 [topology.md](topology.md)） |

## 三、组件清单

| 组件 | 位置 | 说明 |
|------|------|------|
| 入口命令 | `.opencode/commands/cc.md` | `/cc <任务书>` 触发编排 |
| 主编排代理 | `.opencode/agents/charter-orchestrator.md` | 节点 -1~7 调度 + 状态固化 |
| 节点子代理 ×7 | `.opencode/agents/charter-{analyst,coder,tester,reviewer,logger,assetter,notifier}.md` | 每节点一个专职代理 |
| 技能 ×6 | `.opencode/skills/charter-{taskbook,analysis,coding,testing,logging,assets}/SKILL.md` | 宪章按节点按需加载 |
| 硬约束（判定核心 + 外置规则 + 插件适配） | `harness/core/gate.py` + `harness/gate_rules.yaml` + `harness/core/{seal,secret,redact,assets_check}.py` + `harness/plugins/charter-gate.ts` + `.opencode/plugin/charter-gate.ts` | 测试门禁/数据安全/密钥脱敏/资产登记/续签（20260815 任务1 三层体系，详见 [gates.md](gates.md)）；**双体系并行**（20260815 任务2）：opencode 入口（/cc）与 DSH 入口两个插件共享同一 Python 判定核心与 `gate_rules.yaml`，判定结论逐字段一致 |
| 通用宪章 | `constitution/` | 唯一权威规范（13 章顶层 + 6 子规范） |
| 资源地图 | `docs/资源地图.md` | 接口/DDL/代码/宪章的可寻址索引 |
| 项目文档 | `docs/hetu-<项目>/` | 归集自各项目的文档资产 |
| 任务书模板 | `templates/task_book.md` | 标准化任务书输入 |
| 运行时拓扑 | `scripts/harness_topology.py` + 各项目 `.opencode/.harness-env` | 宿主定位/目标发现/路径解析（.harness-env 六字段契约） |
| 安装脚本 | `scripts/install_harness.sh` | 软链分发到各业务项目 + 生成 .harness-env |

## 四、研发流水线

输入支持**任务书路径**或**一句话需求**（自动生成任务书）：

```
输入: /cc <任务书路径 或 一句话需求>
          │
          ▼
节点-1 任务书生成 ──▶ 节点0 校验 ──▶ 节点1 分析 ──▶ 节点2 编码
（仅一句话需求时）                                        │
                                                         ▼
节点7 通知 ◀── 节点6 资产沉淀 ◀── 节点5 研发日志 ◀── 节点4 评审 ◀── 节点3 单测(硬门禁)
```

- 单测：**硬门禁**，全部通过并写 `.gate.json` 才放行（插件拦截）
- 评审：**软门禁**，REVISE 回退编码，最多 2 轮
- 产出统一归档到任务目录 `opencode_schedule/<YYYYMMDD>/<任务目录>/`，节点状态固化在 `研发流程状态.md`

## 五、设计理念

1. **宪章一等公民**：规范即资产，集中一处、按需加载，不污染上下文
2. **软硬结合**：流程编排靠 prompt（弹性），底线拦截靠插件（确定）
3. **资产反哺**：每次研发沉淀 docs 并登记资源地图，形成"研发→沉淀→复用"闭环
4. **单一权威**：宪章只维护 `constitution/` 一处，子项目不再各自维护
5. **可扩展**：新增节点 = 新增子代理 + 更新编排器，两步完成
