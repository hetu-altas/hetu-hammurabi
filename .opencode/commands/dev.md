---
description: 宪章编程：输入任务书，自动执行分析→编码→单测→日志→通知 完整研发流程
agent: charter-orchestrator
---
启动宪章研发流程，任务书路径：$ARGUMENTS

请严格按编排流程执行：校验 → 分析 → 编码 → 单元测试(门禁) → 研发日志 → 钉钉通知，并在 `opencode_schedule/<YYYYMMDD>/研发流程状态.md` 固化每个节点状态。

若 `$ARGUMENTS` 为空，请扫描当前项目的 `opencode_schedule/` 与 `docs/` 目录，列出可用任务书文件并请用户选择。
