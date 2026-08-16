# 宪章体系 DSH 迁移架构（dsh-migration）

> 20260814 任务1（宪章体系DSH重构与运行看板）登记。
> 本文记录宪章编程体系从 opencode 载体迁移到 DSH（DeepSeek Harness）的历史架构决策、
> 机制映射与缺陷修复对照（20260814 任务1）；20260815 任务2 起，opencode 入口与
> DSH 入口**双体系并行**长期维护，共享同一 Python 判定核心与 `gate_rules.yaml`
> （现状策略见第六节）。看板使用见 [dashboard.md](dashboard.md)。
> 20260815 任务3 更新：命令引用 /dev 更名 /cc（L68/L73/L75 命令引用同步）。
> 20260815 任务4 更新：DSH 命令插件命令名统一小写 cc（charter-command.ts
> 命令名大写改小写，L73/L75 命令引用同步；DSH 命令名校验要求小写字母开头）。

## 一、迁移目标与原则

1. **宪章不变**：`constitution/` 单一权威零改动；"人是立法者、宪法高于对话、软硬分层"信条完整保留
2. **载体可换**：宪章与 harness 解耦——换载体只迁移 `harness/` 适配层，宪章零改动
3. **缺陷全修复**：20260814 任务1 评审发现的 6 项机制级缺陷（D1-D6）全部关闭并有回归测试固化
4. **历史兼容**：`opencode_schedule/` 目录契约不变，存量任务数据可静态解析并入看板统计

## 二、机制映射（opencode → DSH）

| opencode 机制 | DSH 对应机制 | 迁移产物 |
|--------------|-------------|---------|
| Commands（`/cc`） | DSH profile + 会话入口（`dsh --profile hetu-hammurabi "<任务书|一句话需求>"`） | `harness/dsh.profile`、`harness/cordis.patch.yml` |
| Agents（charter-* 8 节点） | DSH agent 机制（子代理按 workflow.yaml 调度） | `harness/agents/charter-*.md` |
| Skills（6 个 SKILL.md） | DSH skill 机制（按需加载，引用 constitution/ 不变） | `harness/skills/charter-*/SKILL.md` |
| Plugins hooks（tool.execute.before） | DSH cordis 插件（工具执行前置钩子，骨架见 `harness/plugins/`） | `harness/plugins/charter-gate.ts` 等 |
| `.harness-env` 拓扑契约 | 保留不变（install 脚本生成，插件读取） | `scripts/install_dsh.sh` |
| 任务目录 `opencode_schedule/` | 保留不变（历史兼容） | — |

## 三、缺陷修复对照（D1-D6）

| 缺陷 | 修复机制 | 核心代码 | 回归测试 |
|------|---------|---------|---------|
| D1 门禁跨任务串门 | gate 判定只扫描**当前任务目录**自身的 `.gate.json`，`run_id` 必须与任务目录一致 | `harness/core/gate.py`（`find_gate_file`/`gate_open`） | `unit_test/test_gate_task_isolation.py` |
| D2 门禁自写自验 | **写/验分离**：tester 只产 result 文件；编排器核对后落闸并计算 HMAC `gate_token`（覆盖 run_id + 结果摘要 + 关键声明字段）；篡改/伪造/陈旧一律拒绝 | `harness/core/gate.py`（`build_gate_v2`/`verify_gate_token`）、`harness/core/cli.py`（`seal-gate`） | `unit_test/test_gate_token.py` |
| D3 编排指令与门禁冲突 | `研发流程状态.md` 判定为审计记录**放行**，门禁只拦研发日志与通知 | `harness/core/gate.py`（`is_log_file_write`） | `unit_test/test_gate_bypass.py` |
| D4 硬拦截覆盖面窄 | 通知按 URL/函数特征检测（覆盖 curl/requests 直发），仅放行唯一出口 `harness.core.notify`（`HARNESS_NOTIFY` 标记）；危险命令**任意位置**匹配；日志文件按模式识别变体命名 | `harness/core/gate.py`（`is_notify_call`/`is_destructive`）、`harness/core/notify.py` | `unit_test/test_gate_bypass.py` |
| D5 流程定义硬编码 | 节点顺序/回退轮次/门禁挂载点外置 `harness/workflow.yaml`，解析校验见 `harness/core/workflow.py`；编排插件按 `requires`/`retry` 推进 | `harness/workflow.yaml`、`harness/core/workflow.py`、`harness/plugins/charter-orchestrator.ts` | `unit_test/test_workflow_parser.py` |
| D6 无运行度量 | 全节点事件（start/end/门禁/重试/通知）按 `run_id` 落盘 `runlog/events/YYYYMMDD/<run_id>.jsonl`；存量任务静态解析（`source=history`） | `harness/core/recorder.py`、`harness/core/history.py`、`harness/core/stats.py` | `unit_test/test_recorder.py`、`unit_test/test_dashboard_api.py` |

## 四、目录结构（新体系）

```
hetu-hammurabi/
├── harness/                       # DSH 适配层（新）
│   ├── package.json / dsh.profile / cordis.patch.yml
│   ├── workflow.yaml              # 流程定义（外置，D5）
│   ├── core/                      # Python 确定性核心（可独立单测）
│   │   ├── gate.py  workflow.py  recorder.py  stats.py
│   │   ├── history.py  notify.py  api.py  cli.py
│   ├── plugins/                   # DSH cordis 插件（薄适配）
│   │   ├── charter-gate.ts  charter-recorder.ts  charter-orchestrator.ts
│   ├── agents/                    # 8 节点代理（迁移自 .opencode/，改写 tester/notifier）
│   ├── skills/                    # 6 技能（迁移，引用 constitution/ 不变）
│   └── dashboard/                 # 看板前端（index.html/style.css/app.js）
├── runlog/events/                 # 运行事件库（新）
├── conf/gate_secret               # 门禁密钥（install 生成，gitignore）
├── scripts/install_dsh.sh         # DSH 安装/注册
├── scripts/start_dashboard.sh     # 看板启动
├── .opencode/                     # 旧配置（双体系并行：opencode 入口插件已薄适配新核心，20260815 任务2）
└── constitution/                  # 宪章（零改动）
```

## 五、安装与使用

```bash
# 安装/注册（DSH profile + .harness-env + 软链）
bash scripts/install_dsh.sh                 # 全部平级 hetu-* 项目
bash scripts/install_dsh.sh hetu-sybil      # 指定项目

# 宪章编程插件包（/cc 命令 + 硬门禁 + 看板面板 + 状态栏，一体化安装/卸载）
npx @deepseek-ai/dsh plugin --profile web add ./plugins/constitution-coding    # 安装（@hetu-altas/ConstitutionCoding-Plugin）
npx @deepseek-ai/dsh plugin --profile web remove @hetu-altas/ConstitutionCoding-Plugin   # 卸载

# 启动一次研发（业务项目目录内，/cc 等价物 C1）
bash <HARNESS_DIR>/scripts/run_charter.sh <任务书路径 或 一句话需求>
#   --dry-run 预览编排提示词；空输入列出可用任务书
#   （内部调 dsh headless，注入 workflow.yaml/宪章/门禁约定）

# GUI 钩子（**/cc 命令，constitution coding，命令名必须小写——大写会导致 dsh web 启动失败**；web profile 注册后重启 dsh web 生效）：
#   在 dsh web GUI 输入框直接输入：
#     /cc <任务书路径 或 一句话需求>
#   命令插件（harness/dsh/plugins/charter-command.ts）生成编排提示词，
#   通过 createUserMessage + agent.followup() 注入当前会话并唤醒模型，
#   模型按 workflow.yaml 执行完整流程，GUI 全程可见

# 命令插件部署注意（charter-command.ts，20260815 任务4 补充）：
#   web profile 为实体拷贝部署（非软链），改宿主后需单独 cp：
#     cp harness/dsh/plugins/charter-command.ts $DSH_HOME/profiles/web/plugins/charter-command.ts
#   （scripts/attach_dashboard_to_dsh.sh 仅部署 dashboard-proxy，不含 command 插件）
#   部署后 md5 双侧核对 + 重启 dsh web；命令名须匹配 /^[a-z][a-z0-9_-]*$/u（小写字母开头）

# 启动看板（默认 8790 端口）
bash scripts/start_dashboard.sh [端口]

# 原生面板一键挂接（DSH web GUI 内嵌看板）
bash scripts/attach_native_panel.sh
```

## 六、双体系并行策略

20260815 任务2 起，opencode 入口与 DSH 入口**双体系并行**长期维护，均共享同一 Python 判定核心（`harness/core/`：gate.py / redact.py / assets_check.py 等）与外置规则 `harness/gate_rules.yaml`：

- **两个入口**：opencode 入口 `.opencode/plugin/charter-gate.ts`（/cc 流程）已升级为薄适配层（resolveEnv 解析 + 三钩子委托 decide/redact/assets-check）；DSH 入口 `harness/plugins/charter-gate.ts` 为原生适配层，两插件行为同构、判定结论逐字段一致。
- **何时用哪个**：按运行载体选择——opencode 会话加载 `.opencode/plugin/`，DSH 会话加载 `harness/plugins/`；业务项目两套入口均已安装，互不冲突。
- **维护与升级规则**：改规则（`gate_rules.yaml`）/ 改核心（`harness/core/`）**一处生效**（两入口自动生效，规则按 mtime 重载）；改插件适配须**分别重启** opencode / DSH。
- **任务3**（双体系并行说明文档补全）：`docs/harness/extend.md` 新增「双体系并行」章节 + README/拓扑文档同步——已在 20260815 任务2 完成。
