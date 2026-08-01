# 扩展与维护

> 本文阐述 harness 的安装分发、日常运维、扩展开发与 FAQ。

## 一、安装与分发

### 1.1 安装到业务项目

```bash
bash scripts/install_harness.sh
```

将 `.opencode/{agents,commands,skills,plugin}` 软链到同级各 `hetu-*` 项目。

### 1.2 分发范围与限制

| 方式 | 生效范围 | 跨机器 |
|------|---------|--------|
| 项目软链（本方案） | 当前机器上的各业务项目 | 需重跑 install 脚本 |
| 全局 `~/.config/opencode/` | 本机所有项目 | 机器级，不进 git |
| 项目实体副本 | 单项目 | 可跨机器但需维护多份 |

> 当前软链为绝对路径，换机器克隆后需重新执行 `scripts/install_harness.sh`。

### 1.3 验证安装

```bash
opencode agent list            # 应看到 charter-* 全部代理
opencode debug skill           # 应看到 charter-* 技能
opencode debug config          # plugin 列表应含 charter-gate.ts
```

## 二、日常使用

### 2.1 启动一次研发

```bash
# 1. 按 templates/task_book.md 编写任务书
# 2. 放入业务项目 opencode_schedule/<YYYYMMDD>/
# 3. 业务项目目录内启动 opencode
/dev opencode_schedule/20260801/20260801任务1xxx.md
```

### 2.2 无人工干预的运行前提

- 任务书按模板填写完整（文件清单、接口格式、单测要求）
- `.gate.json` 由测试节点自动生成
- 测试/评审回退自动执行（各最多 3/2 轮）

### 2.3 观察与干预点

| 时机 | 可干预操作 |
|------|-----------|
| 任意时刻 | 中断会话，问题反馈后重跑 `/dev` |
| 节点3 连续失败 | 手动检查实现与测试，修正后重跑 |
| 评审 REVISE 2 轮不过 | 人工介入修改，或调整任务书范围 |

## 三、配置变更生效规则

opencode 的配置（agents/skills/commands/plugin）**启动时加载、不热更新**：

1. 修改配置后必须**退出并重启 opencode**
2. 运行中会话继续使用旧配置

## 四、扩展开发

### 4.1 新增流程节点

1. 新建 `.opencode/agents/charter-xxx.md`（subagent，定义输入/产出/权限）
2. 更新 `charter-orchestrator.md` 流程定义（插入节点、重编号、门禁规则）
3. 如需要硬约束：在 `charter-gate.ts` 增加拦截规则
4. 同步更新：根宪法第十二章、README 流程表、本文档
5. 重启 opencode 验证

### 4.2 修改宪章

- 只改 `constitution/` 源文件（Skill 引用路径，自动生效）
- 顶层宪法新增领域章节：加"详见 xxx.md"行 + 文首索引表行

### 4.3 修改硬约束

编辑 `.opencode/plugin/charter-gate.ts`，在 `tool.execute.before` 中：

```ts
if (命中条件) {
  throw new Error("[charter-gate] 说明文字")
}
```

⚠️ 注意：插件块注释内禁止出现 `*/` 序列（会截断注释导致插件静默加载失败）。

### 4.4 新技能

`.opencode/skills/<name>/SKILL.md`（frontmatter 必须含 `name` + `description`），描述要写明"何时使用"，模型按描述决定加载。

## 五、已知限制

| 限制 | 说明 | 缓解 |
|------|------|------|
| 门禁覆盖路径有限 | 插件按命令/文件名模式匹配，绕过模式（如用 `send_dingtalk` 工具）可逃逸 | 通知节点提示词固定走被拦截的路径 |
| 软约束存在概率性 | 节点顺序、合规靠 prompt | 评审节点兜底 + 后续可加 CI 门禁 |
| 无失败数据度量 | 节点通过率/失败原因未采集 | 可加统计脚本，反哺宪章修改 |
| 语义检索未启用 | 资源匹配靠关键词 | 文档量 >500 或模糊检索需求出现时上 Milvus |

## 六、FAQ

**Q1：为什么子项目里还保留旧 constitution 目录？**
A：已停更。`constitution/` 归 hammurabi 唯一维护，子项目目录原样保留避免破坏历史。

**Q2：任务书必须用模板吗？**
A：强烈建议。编排器从任务书文件名解析日期/序号，模板章节保证节点产出齐全。

**Q3：测试节点没有写 .gate.json 怎么办？**
A：门禁保持关闭（fail-closed），日志/通知会被硬拦截——这正是设计意图：宁可不产出，也不产出未验证结果。

**Q4：可以在非 hetu 项目用这套 harness 吗？**
A：可，但 skills/资源地图中的相对路径（`../hetu-hammurabi/...`）依赖"同父目录部署"约定；跨目录部署需调整路径引用。

**Q5：改了宪章需要重新装 harness 吗？**
A：不需要。skill 引用的是 `constitution/` 源文件路径；重启 opencode 即可生效。
