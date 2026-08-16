# 门禁与硬约束

> 本文阐述体系的"软硬结合"约束模型：哪些环节靠 prompt 约束（软），哪些靠插件确定性拦截（硬）。
> 相关实现：`harness/core/gate.py`（判定核心）+ `harness/gate_rules.yaml`（外置规则）
> + `harness/core/seal.py`（落闸/续签）+ `harness/core/redact.py`（脱敏）
> + `harness/core/assets_check.py`（资产登记检查）+ `harness/plugins/charter-gate.ts`（DSH 插件适配）
> + `.opencode/plugin/charter-gate.ts`（opencode 入口插件适配，双体系并行共享判定，20260815 任务2）。
> 设计背景与优化对照见 `docs/hetu-hammurabi/hard-gate-optimize.md`（20260815任务1）。

## 一、软硬约束矩阵

| 环节 | 软/硬 | 机制 | 违约后果 |
|------|-------|------|---------|
| 节点顺序 | 软 | 编排器系统提示词 | 可能被模型忽略（概率性） |
| 编码规范合规 | 软 | charter-coding Skill | 需评审节点兜底 |
| 节点3 测试门禁 | **硬** | charter-gate 拦截日志/通知写入 | 工具调用被拒，无法绕过 |
| 节点5/6/7 准入 | **硬** | 同上（`.gate.json` 未开/过期） | 日志/钉钉操作被拒 |
| 数据销毁需备份 | **硬** | charter-gate 命令扫描（语义校验） | 命令被拒执行 |
| 密钥不落明文 | **硬** | charter-gate 消息脱敏 | 自动脱敏 + 告警 |
| 资产登记一致性 | 软(告警) | charter-gate 事后检查 | 告警提示，不阻断 |
| 任务书/宪章校验 | 软 | 编排器节点0 | 提示错误 |

## 二、体系结构（20260815任务1 起）

硬约束判定为**三层架构**，判定逻辑唯一在 Python 核心，插件只做薄适配：

```
DSH 插件 charter-gate.ts / 旧 opencode 插件
        （旧 opencode 插件已薄适配新核心，20260815 任务2：双体系并行、共享判定）
        │ 子进程调用（参数透传，阻断/告警）
        ▼
Python 核心 harness/core（判定唯一）
        ├── gate.py        判定核心：gate_open / decide / is_*（规则来自外置 yaml）
        ├── gate_rules.yaml 外置规则：危险命令/通知特征/日志模式/放行名单/新鲜度窗口
        ├── seal.py        落闸：result 双格式解析核对 + 签名落盘（flock 锁）
        ├── secret.py      密钥：权限 600 强制 + rotate-secret 轮换
        ├── redact.py      脱敏：明文凭据扫描替换（纯函数）
        └── assets_check.py 资产登记检查（纯函数）
```

- **规则外置**：全部判定规则在 `harness/gate_rules.yaml`，按文件 mtime 检测变更，**改配置即生效（不重启 Python 进程）**；文件缺失/非法 → 回退内置默认（fail-closed）。
- **CLI 入口**：`python -m harness.core.cli <decide|seal-gate|re-seal|rotate-secret|record|redact|assets-check>`。

## 三、测试门禁（核心）

### 3.1 信任模型（.gate.json v2，契约不变）

- **事实来源**：任务目录下的 `.gate.json`（`opencode_schedule/<YYYYMMDD>/<任务目录>/.gate.json`，只认当前任务目录，不递归扫描）。
- **写入方**：编排器（charter-orchestrator）核对 result 文件后调用 `seal-gate` 签名落闸；tester 只产 result 文件，自写不被信任。
- **校验链**（gate_open，fail-closed）：GATE_MISSING → GATE_SCHEMA → GATE_RUN_ID_MISMATCH → GATE_NOT_PASSED → GATE_NO_RESULTS → GATE_TOKEN_INVALID → GATE_STALE。
- **token**：HMAC-SHA256（run_id + result 摘要 + 声明字段含 updated_at），篡改任一字段即失效。
- **新鲜度**：默认 10 分钟（`gate_rules.yaml` freshness_seconds 可调），超时 GATE_STALE。

### 3.2 seal-gate 落闸（自动核对，H3）

- 命令行**不再接受 `--total/--passed`**，数字以 result 文件解析值为准：
  - 八格式（`测试总数/成功/失败/错误` 四数字）优先；
  - unittest 原生格式（`Ran N tests` + `OK`）回退；
  - 同一文件双格式交叉核对不一致 → 拒绝；多文件「任一拒绝即整体拒绝」。
- 落盘走 **flock 独占锁 + 锁内重读比对**（H9）：并发 seal-gate 串行化，后写者报「已被并发更新，请重试」。

### 3.3 续签 re-seal（H4）

- 门禁过期（GATE_STALE）时由编排器执行 `re-seal`：**仅刷新 updated_at 并重签 token**，run_id/result_files/total/passed/test_passed 全部原样；
- 续签前重读 result 重新核对（result 被改/缺失 → 拒绝）；
- 每次续签写 `event_type=re_seal` 审计事件到 `runlog/events/YYYYMMDD/<run_id>.jsonl`；
- 插件判定命中 GATE_STALE 时，阻断消息附「提示：可执行 re-seal 续签（由编排器执行）」。

### 3.4 拦截规则

- 仅拦截写入/通知/危险命令，读取（read/cat/grep）放行；
- 研发日志（`*研发日志*.md`、任务目录内含「日志」的 .md）须门禁开启；
- 审计文件（`研发流程状态.md`）与放行名单（`log_file.allowlist`，如 `数据日志说明.md`）放行；
- 钉钉通知须过唯一出口 `harness.core.notify`（HARNESS_NOTIFY 标记）。

## 四、数据安全（H2）

- 拦截命令（外置 `dangerous_commands`，任意位置匹配、大小写不敏感）：
  - rm 递归删除变体（6 样本 = 5 选项 × 3 前缀，全拦）：`rm -rf` / `rm -fr` / `rm -r -f` / `rm --recursive --force` / `/bin/rm -rf` / `\rm -rf`
  - 销毁类：`shred` / `unlink` / `rmdir -r` / `mv` 到回收站（trash/回收站）
  - 数据库/向量库：`DROP TABLE/STABLE` / `DELETE FROM` / `TRUNCATE` / `drop_collection`
- **备份语义校验**（H2d）：销毁判定用原始命令；备份声明在**剥离 echo/printf 文本与 `#` 注释后**搜索 `backup|备份`——`rm -rf /data && echo backup`、`rm -rf /data # 已备份` 均视为假声明拦截；真实备份动作（`cp -r /data /backup/data && rm -rf /data`、`--backup=` 参数）放行。
- 通知 URL 混淆识别：`oapi[.]dingtalk[.]com`（字符类点）、`"oapi."+"dingtalk.com"`（变量拼接）均被识别为通知外呼。

## 五、密钥管理（H7）

- 密钥文件 `conf/gate_secret`：install 脚本强制 `chmod 600`（含已存在文件修正）；
- `rotate-secret` 轮换：openssl rand（回退 /dev/urandom）→ 原子写入（临时文件 + rename）→ chmod 600；轮换后旧闸 token 自然失效（HMAC 密钥更换）；
- 权限非 600 时 decide/seal 路径告警，rotate 默认拒绝（`--force` 跳过前置检查）。

## 六、密钥脱敏（H5）

- 对象：chat 消息中的明文凭据（`sk-<16+位>`、`Bearer <token>`、`password|secret|token|api_key|access_key|access_token = 值`）；
- 行为：自动替换为 `[REDACTED]` + warn 告警（模式可在 `gate_rules.yaml` `secret_patterns` 段配置）。

## 七、资产登记一致性（H6）

- 触发：`write`/`edit` 目标位于 `docs/hetu-*/`；
- 检查：目标文件名是否出现在资源地图（宿主 `<HARNESS_DIR>/docs/资源地图.md`，.harness-env 缺失/字段缺失/宿主地图不存在时回退当前项目 `docs/资源地图.md`）；
- 行为：未登记 → warn 软告警（不阻断）。

## 八、为什么需要硬约束

| 场景 | 纯 prompt 的失败模式 | 硬约束的结果 |
|------|---------------------|-------------|
| 测试没跑就写日志/发通知 | 模型声称"已通过" | `.gate.json` 缺失 → 工具被拒 |
| 误删数据 | 模型直接执行危险命令 | 无真实备份动作 → 命令被拒 |
| 密钥入日志 | 模型把 token 打印出来 | 自动脱敏 + 告警 |
| 落闸数字造假 | 模型声称"全过" | result 解析核对，声明不符拒绝 |

## 九、扩展硬约束

1. 修改 `harness/gate_rules.yaml` 中的模式/阈值（不重启即生效，无需改代码）；
2. 新增判定逻辑：修改 `harness/core/gate.py`（纯函数，Python 单测守护）；
3. 修改插件适配：`harness/plugins/charter-gate.ts` 调整 DSH 插件适配（**需重启 DSH 生效**）；opencode 入口改 `.opencode/plugin/charter-gate.ts`（**需重启 opencode 生效**），两入口独立维护、共享判定（20260815 任务2 双体系并行）。

> 注意：插件内注释禁止出现 `*/` 序列（会截断块注释导致插件加载失败，曾踩坑）。
