# 代理与技能体系

> 本文阐述 Agents（编排 + 节点子代理）与 Skills（宪章按需加载）两个机制。
> 相关实现：`.opencode/agents/`、`.opencode/skills/`。

## 一、代理总览

| 代理 | 模式 | 职责 | 关键权限 |
|------|------|------|---------|
| charter-orchestrator | primary | 节点 -1~7 调度、输入判别、回退、状态固化 | edit/bash 允许；task 限定 `charter-*` |
| charter-taskwriter | subagent | 一句话需求 → 生成任务书（节点 -1） | edit 允许（仅任务书文件） |
| charter-analyst | subagent | 解析任务书 → 实施计划 + 资源匹配清单 | edit 允许（仅产出文件） |
| charter-coder | subagent | 按宪章实现源码/脚本/依赖 | edit/bash 允许 |
| charter-tester | subagent | 编写并运行单测 → 写结果 + `.gate.json` | edit/bash 允许 |
| charter-reviewer | subagent | 只读评审，产出评审报告 | **edit 禁止**（deny） |
| charter-logger | subagent | 撰写研发日志 | edit 允许（仅日志文件） |
| charter-assetter | subagent | docs 新增/更新 + 资源地图登记 | edit 允许（仅 docs） |
| charter-notifier | subagent | 钉钉完成通知 | bash 允许（调 util_dingtalk） |

设计原则：

1. **单节点单代理**：每个流程节点对应一个专职子代理，提示词聚焦单一职责
2. **最小权限**：评审代理 `edit: deny`；日志/沉淀代理只在各自输出域内写文件
3. **委托而非并行**：编排器串行调度节点，保证门禁顺序确定
4. **子代理上下文隔离**：子代理独立上下文，不污染主会话，结果以结构化形式回传

## 二、编排器（charter-orchestrator）

- **输入**：任务书路径（来自 `/cc` 命令 `$ARGUMENTS`）
- **职责**：校验 → 按序调用节点子代理 → 执行回退规则 → 维护 `研发流程状态.md`
- **回退闭环**：

```
节点3 单测 ──FAIL──▶ 节点2 编码(修复) ──▶ 节点3(重测)   最多3轮
节点4 评审 ──REVISE─▶ 节点2 编码(修复) ──▶ 节点3 ──▶ 节点4(重审)  最多2轮
```

## 三、Skills：宪章按需加载

Skill 是"宪章的可加载封装"：模型只在对应节点调用 `skill` 工具加载，避免把全部规范常驻上下文。

| Skill | 加载节点 | 引用宪章源文件 |
|-------|---------|---------------|
| charter-taskbook | 节点 -1 任务书生成 | `templates/task_book.md`、`docs/资源地图.md` |
| charter-analysis | 节点1 分析 | `docs/资源地图.md`（匹配流程） |
| charter-coding | 节点2 编码 / 节点4 评审 | `constitution/constitution.md`、`coding/coding.md`、`project/project.md` |
| charter-testing | 节点3 单测 | `constitution/unit_test/unit_test.md` |
| charter-logging | 节点5 日志 | 日志模板与历史示例 |
| charter-assets | 节点6 沉淀 | 新增/更新判定流程 |

### 设计要点

1. **Skill 指向源文件而非复制内容**：宪章修改后无需改 Skill，天然同步
2. **on-demand**：每个节点只加载自己需要的 1-2 个 Skill
3. **description 触发**：模型根据 Skill 描述自主判断何时加载
4. **权限隔离**：Skill 访问可通过 `permission.skill` 按代理控制

## 四、Commands：入口

`.opencode/commands/cc.md`：

```markdown
---
description: 宪章编程：输入任务书，自动执行分析→编码→单测→评审→日志→沉淀→通知
agent: charter-orchestrator
---
启动宪章研发流程，任务书路径：$ARGUMENTS
```

- `agent: charter-orchestrator` → 命令直接切换到编排代理
- `$ARGUMENTS` → 传入任务书路径；为空时扫描 `opencode_schedule/` 供用户选择

## 五、节点间传参约定

编排器以对话形式向子代理传递：

| 传参 | 来源 | 消费方 |
|------|------|--------|
| 任务书路径 | /cc 输入 | analyst |
| 实施计划路径 | analyst 产出 | coder |
| 改动文件清单 | coder 返回 | tester / reviewer |
| 测试结果 + .gate.json | tester 产出 | 编排器（门禁判定） |
| 评审结论 | reviewer 返回 | 编排器（放行判定） |
| 任务名/结果汇总 | 编排器 | logger / assetter / notifier |
