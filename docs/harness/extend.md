# 扩展与维护

> 本文阐述 harness 的安装分发、日常运维、扩展开发与 FAQ。

## 一、安装与分发

### 1.1 安装到业务项目

```bash
bash scripts/install_harness.sh                # 安装到全部平级 hetu-* 项目
bash scripts/install_harness.sh hetu-sybil     # 仅安装到指定项目（支持非 hetu-* 前缀项目）
```

安装流程（宿主判定与目标发现由 `scripts/harness_topology.py` 纯函数解析，不写死项目名）：

1. **宿主校验**：结构特征判定（`.opencode/agents/` + `constitution/constitution.md` + `docs/资源地图.md`）
2. **目标发现**：同父目录下除宿主外的全部 `hetu-*` 项目（+ 可选参数追加指定项目）
3. **生成 `.opencode/.harness-env`**：六字段契约（PROJECT_NAME / PROJECT_DIR / WORKSPACE_DIR / HARNESS_DIR / AETHER_DIR / VENV_BIN，均为绝对路径，详见 [topology.md](topology.md)）
4. **软链补全**：`agents`、`commands`、`skills`、`plugin`、`package.json`、`package-lock.json` 共 6 项（`node_modules` 不软链，各项目自行 `npm install`）
5. **.gitignore 补齐**：各项目 `.opencode/.gitignore` 追加 `.harness-env`（含绝对路径，禁止入库）

### 1.2 分发范围与限制

| 方式 | 生效范围 | 跨机器 |
|------|---------|--------|
| 项目软链（本方案） | 当前机器上的各业务项目 | 需重跑 install 脚本 |
| 全局 `~/.config/opencode/` | 本机所有项目 | 机器级，不进 git |
| 项目实体副本 | 单项目 | 可跨机器但需维护多份 |

> 当前软链为绝对路径，换机器克隆后需重新执行 `scripts/install_harness.sh`（重新生成各项目 `.opencode/.harness-env`；该文件由脚本静态重写，勿手改）。

### 1.3 新项目接入三步

1. 创建项目目录并 clone/初始化（项目名建议 `hetu-*` 前缀，便于自动发现）
2. 在宿主内运行 `bash scripts/install_harness.sh <项目名>`（或全量安装 `bash scripts/install_harness.sh`）
3. 重启 opencode（配置启动时加载、不热更新），在项目目录内验证 `/cc` 命令可用、charter-* 代理与技能可见

### 1.4 验证安装

```bash
opencode agent list            # 应看到 charter-* 全部代理
opencode debug skill           # 应看到 charter-* 技能
opencode debug config          # plugin 列表应含 charter-gate.ts
```

## 二、日常使用

### 2.1 启动一次研发

```bash
# 1. 按 templates/task_book.md 编写任务书
# 2. 放入业务项目 opencode_schedule/<YYYYMMDD>/<任务目录>/（任务目录以任务书名命名）
# 3. 业务项目目录内启动 opencode
/cc opencode_schedule/20260801/20260801任务1xxx/20260801任务1xxx.md
```

### 2.2 无人工干预的运行前提

- 任务书按模板填写完整（文件清单、接口格式、单测要求）
- `.gate.json` 由测试节点自动生成
- 测试/评审回退自动执行（各最多 3/2 轮）

### 2.3 观察与干预点

| 时机 | 可干预操作 |
|------|-----------|
| 任意时刻 | 中断会话，问题反馈后重跑 `/cc` |
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
3. 如需要硬约束：在 `harness/gate_rules.yaml` 增加拦截规则（或 `harness/core/gate.py` 扩展判定，插件适配见 `harness/plugins/charter-gate.ts`）
4. 同步更新：根宪法第十三章、README 流程表、本文档
5. 重启 opencode 验证

### 4.2 修改宪章

- 只改 `constitution/` 源文件（Skill 引用路径，自动生效）
- 顶层宪法新增领域章节：加"详见 xxx.md"行 + 文首索引表行

### 4.3 修改硬约束

> 20260815 任务1 起为三层体系（详见 [gates.md](gates.md) 与 `docs/hetu-hammurabi/hard-gate-optimize.md`），按需修改对应层：

1. **改规则（最常见）**：编辑 `harness/gate_rules.yaml`（危险命令/通知特征/日志模式/放行名单/新鲜度窗口/备份语义/脱敏模式），**改配置即生效，无需重启**；文件缺失/非法 → 回退内置默认（fail-closed）。
2. **改判定逻辑**：编辑 `harness/core/gate.py`（纯函数，Python 单测守护）；落闸/续签/密钥/脱敏/资产检查分别见 `harness/core/{seal,secret,redact,assets_check}.py`。
3. **改插件适配**：编辑 `harness/plugins/charter-gate.ts`（DSH 插件，薄适配：子进程调 `cli.py`，阻断/告警语义不变），改后需**重启 DSH** 生效。

⚠️ 注意：插件块注释内禁止出现 `*/` 序列（会截断注释导致插件静默加载失败）。

### 4.4 双体系并行（opencode 入口 + DSH 入口）

> 20260815 任务2 起为**双体系并行**：opencode 入口（/cc）与 DSH 入口长期并行维护，
> 旧体系不弃用、不迁移，两入口均为薄适配层。

1. **两个入口**：
   - opencode 入口：`.opencode/plugin/charter-gate.ts`（/cc 流程，已薄适配新核心，见 [topology.md](topology.md) 六）；
   - DSH 入口：`harness/plugins/charter-gate.ts`（DSH profile 流程，原生适配层）。
2. **共享核心**：判定逻辑唯一在 Python（`harness/core/cli.py` → gate.py / redact.py / assets_check.py + `harness/gate_rules.yaml`），两插件均为参数透传 + 阻断/告警的薄适配层，对同一输入判定结论逐字段一致。
3. **何时用哪个**：按运行载体选——opencode 会话加载 `.opencode/plugin/`，DSH 会话加载 `harness/plugins/`；业务项目两套入口均已安装，互不冲突。
4. **维护与升级规则**：
   - 改规则（`harness/gate_rules.yaml`）/ 改核心（`harness/core/*.py`）：**一处生效**，两入口自动生效（规则按 mtime 重载，不重启）；
   - 改插件适配：opencode 入口改 `.opencode/plugin/charter-gate.ts` 后**重启 opencode**；DSH 入口改 `harness/plugins/charter-gate.ts` 后**重启 DSH**——两入口独立重启，互不影响。
5. 与「4.3 修改硬约束」衔接：三层体系（核心 / 规则 / 插件适配）不变，仅插件适配层按入口分别维护。

### 4.5 新技能

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
A：已停更。`constitution/` 归 harness 宿主唯一维护，子项目目录原样保留避免破坏历史。

**Q2：任务书必须用模板吗？**
A：强烈建议。编排器从任务书文件名解析日期/序号，模板章节保证节点产出齐全。

**Q3：测试节点没有写 .gate.json 怎么办？**
A：门禁保持关闭（fail-closed），日志/通知会被硬拦截——这正是设计意图：宁可不产出，也不产出未验证结果。

**Q4：可以在非 hetu 项目或跨目录部署用这套 harness 吗？**
A：安装脚本基于「同父目录」约定自动发现目标项目（`hetu-*` 前缀），并为每个项目生成 `.opencode/.harness-env` 记录宿主/公共工具/共享环境位置；同父目录的 hetu-* 项目执行一次 install 即装即用。跨目录部署（非 hetu 项目、或与宿主不同父目录）时，可手动复制/软链 `.opencode` 并自定义 `.harness-env`（指向宿主与公共工具项目）获得 harness 能力，但需自行保证各字段路径正确、随部署位置更新。

**Q5：改了宪章需要重新装 harness 吗？**
A：不需要。skill 引用的是 `constitution/` 源文件路径；重启 opencode 即可生效。
