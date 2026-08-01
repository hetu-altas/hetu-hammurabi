# 门禁与硬约束

> 本文阐述体系的"软硬结合"约束模型：哪些环节靠 prompt 约束（软），哪些靠插件确定性拦截（硬）。
> 相关实现：`.opencode/plugin/charter-gate.ts`。

## 一、软硬约束矩阵

| 环节 | 软/硬 | 机制 | 违约后果 |
|------|-------|------|---------|
| 节点顺序 | 软 | 编排器系统提示词 | 可能被模型忽略（概率性） |
| 编码规范合规 | 软 | charter-coding Skill | 需评审节点兜底 |
| 节点3 测试门禁 | **硬** | charter-gate 拦截日志/通知写入 | 工具调用被拒，无法绕过 |
| 节点5/6/7 准入 | **硬** | 同上（`.gate.json` 未开） | 日志/钉钉操作被拒 |
| 数据销毁需备份 | **硬** | charter-gate 命令扫描 | 命令被拒执行 |
| 密钥不落明文 | **硬** | charter-gate 消息脱敏 | 自动脱敏 + 告警 |
| 资产登记一致性 | 软(告警) | charter-gate 事后检查 | 告警提示，不阻断 |
| 任务书/宪章校验 | 软 | 编排器节点0 | 提示错误 |

## 二、charter-gate 插件

位于 `.opencode/plugin/charter-gate.ts`，是全部硬约束的载体，基于 opencode hooks 实现（hook 中 `throw` 即硬阻断）。

### 2.1 测试门禁（核心）

- **事实来源**：`opencode_schedule/<YYYYMMDD>/.gate.json`
  ```json
  {"test_passed": true, "total": 41, "passed": 41, "updated_at": "2026-08-01 10:00:00"}
  ```
- **写入方**：charter-tester 运行完测试后写入（true=全过 / false=有失败）
- **拦截规则**：`.gate.json` 缺失或 `test_passed != true` 时，以下操作一律 `throw` 阻断：
  - 写入 `*研发日志.md`、`*研发流程状态.md`
  - bash 中调用钉钉通知（`util_dingtalk` / `send_markdown` / `send_text`）
- **验证结果**：门禁关闭时写入被拒；打开后放行（真实环境双向验证通过）

### 2.2 数据安全

- 拦截命令：`rm -rf`、`DROP TABLE/STABLE`、`DELETE FROM`、`TRUNCATE`、`drop_collection`
- 放行条件：命令中显式包含 `backup` 或 `备份`
- 对应宪法：顶层"数据增删改必须备份"

### 2.3 密钥脱敏

- 拦截对象：`chat.message` 中的明文凭据
- 匹配模式：`sk-...`、`Bearer ...`、`password|secret|token|api_key|access_key|access_token = value`
- 行为：自动替换为 `[REDACTED]` + warn 告警记录

### 2.4 资产登记一致性

- 触发：`write`/`edit` 目标位于 `docs/hetu-*/`
- 检查：目标文件名是否出现在 `docs/资源地图.md`
- 行为：未登记 → warn 告警（软提醒，不阻断，避免误伤手动编辑）

## 三、为什么需要硬约束

| 场景 | 纯 prompt 的失败模式 | 硬约束的结果 |
|------|---------------------|-------------|
| 测试没跑就写日志/发通知 | 模型声称"已通过" | `.gate.json` 缺失 → 工具被拒 |
| 误删数据 | 模型直接执行危险命令 | 无 backup 关键字 → 命令被拒 |
| 密钥入日志 | 模型把 token 打印出来 | 自动脱敏 + 告警 |

## 四、扩展硬约束

1. 打开 `.opencode/plugin/charter-gate.ts`
2. 在 `tool.execute.before` 中新增规则，命中即 `throw new Error("...")`
3. 重启 opencode 生效

> 注意：插件内注释禁止出现 `*/` 序列（会截断块注释导致插件加载失败，曾踩坑）。
