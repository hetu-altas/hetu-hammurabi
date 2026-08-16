---
description: 宪章编程（cc = constitution coding）：输入任务书路径或一句话需求，自动执行完整研发流程
agent: charter-orchestrator
---
启动宪章研发流程（/cc = constitution coding，宪章编程），输入：$ARGUMENTS

## 输入判别（三种模式）
- **任务书路径**：`$ARGUMENTS` 是已存在的 `.md` 文件路径 → 直接作为任务书，从节点 0 开始执行。
- **一句话需求**：`$ARGUMENTS` 非空且不是已有文件路径 → 先执行节点 -1（charter-taskwriter 生成任务书），再按节点 0-7 执行。
- **空输入**：`$ARGUMENTS` 为空 → 扫描当前项目 `opencode_schedule/` 与 `docs/` 目录，列出可用任务书文件请用户选择。

## 执行要求
严格按编排流程执行：任务书生成(按需) → 校验 → 分析 → 编码 → 单元测试(硬门禁) → 评审 → 研发日志 → 资产沉淀 → 钉钉通知，并在任务目录 `opencode_schedule/<YYYYMMDD>/<任务目录>/研发流程状态.md` 固化每个节点状态。
