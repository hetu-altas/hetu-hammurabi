# harness 硬约束体系优化设计（20260815任务1）

> 登记：20260815 任务1（harness硬约束体系优化）· 宿主 hetu-hammurabi
> 范围：规则外置 / 绕过面收窄 / 落闸可信 / 续签机制 / 脱敏回归 / 资产检查回归 / 密钥管理 / 并发安全

## 一、优化点核实与修复对照（H1-H9）

| 编号 | 优化点 | 修复位置 | 验证 |
|------|--------|---------|------|
| H1 | 判定规则硬编码 | `harness/gate_rules.yaml` 新建（规则外置）+ `harness/core/gate.py` 加载器（mtime 缓存重载 / 非法 fail-closed / 内置默认回退） | `unit_test/test_gate_rules.py`（16 用例） |
| H2 | 绕过面残留（rm 变体/销毁类/URL 混淆/备份假声明） | `gate_rules.yaml` dangerous_commands 扩展 + backup 语义校验（剥离 echo/printf/注释后搜索） | `unit_test/test_gate_bypass.py`（31 用例） |
| H3 | seal-gate 数字可任意填报 | `harness/core/seal.py` 新建：result 双格式解析核对 + build_gate_v2 落盘；`cli.py` 删 `--total/--passed` | `unit_test/test_seal_gate.py`（22 用例） |
| H4 | 10 分钟窗口与长流程冲突 | `seal.re_seal` 续签（只刷 updated_at 重签 token）+ `cli.py re-seal` 子命令 + `recorder.VALID_EVENT_TYPES` 追加 `re_seal` + 插件 GATE_STALE 提示 | `unit_test/test_gate_lease.py`（10 用例） |
| H5 | 脱敏约束丢失 | `harness/core/redact.py` 新建（迁移旧插件 L80-96）+ `cli.py redact` + charter-gate.ts chat 钩子 | `unit_test/test_gate_redact.py`（8+3 用例，含 REVISE 第1轮补 TestRulesSecretPatterns 3 例） |
| H6 | 资产登记检查丢失 | `harness/core/assets_check.py` 新建（迁移旧插件 L56-78/L148-158）+ `cli.py assets-check` + charter-gate.ts after 钩子 | `unit_test/test_gate_assets.py`（9 用例） |
| H7 | 密钥权限 777、无轮换 | `harness/core/secret.py` 新建（600 强制校验 + rotate-secret 原子轮换）+ `scripts/install_dsh.sh` chmod 600 | `unit_test/test_gate_concurrency.py`（权限用例） |
| H8 | 日志变体误伤 | `gate_rules.yaml` log_file.allowlist 放行名单（精确文件名，默认预置 `数据日志说明.md`） | `test_gate_bypass.py` TestGateLogAllowlist |
| H9 | 多会话并发后写者胜 | `seal.write_gate_locked` flock 独占锁 + 锁内重读比对（后写者报「已被并发更新，请重试」） | `unit_test/test_gate_concurrency.py`（双进程实测） |

**回归基准**：改造前 110/110（实测，20260815 任务2 后基线）；改造后全量 **221/221**（`discover` 全量 201 用例 + 存量 `test_harness_topology_result.txt` 20 用例，落闸口径 = 两 result 文件合计；含 H3 回归修复 1 例、REVISE 第1轮修复反例 6 例），全绿。

## 二、规则外置 schema（gate_rules.yaml，schema_version=1）

```yaml
schema_version: 1
freshness_seconds: 600            # H4 可调阈值（原 gate.py L35 硬编码）
log_file:
  main_pattern: "研发日志"          # 主模式（原 L38）
  ext_pattern: "日志"              # 扩展模式（原 L39）
  allowlist: ["数据日志说明.md"]    # H8 放行名单（精确文件名）
  task_dir_pattern: "opencode_schedule[/\\]\d{8}[/\\][^/\\]+[/\\]"  # 原 L42 外置
audit_files: ["研发流程状态.md"]    # 审计放行（原 L45）
notify:
  url_patterns:                    # H2c URL 级（字符类点/变量拼接混淆识别）
    - "oapi\s*[.\[\]]\s*dingtalk\s*[.\[\]]\s*com"
    - "oapi\s*[.\[\]'\"+-]*\s*dingtalk\s*[.\[\]'\"+-]*\s*com"   # 宽松式（跨 " + 拼接）
    - "robot\s*/\s*send"
  func_patterns: ["util_dingtalk", "send_markdown|send_text", "HARNESS_NOTIFY", "harness\.core\.notify"]
  allow_patterns: ["HARNESS_NOTIFY", "harness\.core\.notify"]
dangerous_commands:
  rm_recursive: "(?:\brm|/bin/rm|\\rm)\s+(?:-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*|-r\s+-f|--recursive\s+--force|-fr|-rf)\b"
  shred: "\bshred\b"
  unlink: "\bunlink\b"
  rmdir_recursive: "\brmdir\s+-[a-zA-Z]*r"
  mv_trash: "\bmv\b.*(?:回收站|trash)"
  drop_table: "\bDROP\s+(TABLE|STABLE)\b"
  delete_from: "\bDELETE\s+FROM\b"
  truncate: "\bTRUNCATE\b"
  drop_collection: "\bdrop_collection\b"
backup:
  pattern: "backup|备份"
  semantic: enforce               # H2d 语义校验
secret_patterns:                  # 可选：redact.py 脱敏模式（缺省用内置三类，C 阶段）
  - "sk-[a-zA-Z0-9]{16,}"
  - "Bearer\s+[a-zA-Z0-9._~+/=-]+"
  - "(?:password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|access_token)\s*[=:]\s*['\"]?[^\s'\"]{8,}"
```

**设计决策**：
1. 加载器按文件 mtime（纳秒）检测变更，**改配置不重启即生效**；
2. 文件缺失 / YAML 解析失败 / schema 非法（缺字段、类型错、非法正则）→ 回退内置默认并告警（fail-closed，内置默认与默认文件行为一致，含绕过面完整规则，防止规则文件损坏时绕过面退化）；
3. 正则全部 `re.IGNORECASE` 编译（与 20260814 行为一致）；日志模式不带 flag（中文大小写无意义）；
4. 三处正则修正（对照任务书 4.1）：① `rm_recursive` 前缀 `(?:\brm|/bin/rm|\\rm)`（`\b` 前缀对 `/bin/rm`、`\rm` 无效）；② URL 拼接宽松模式 `[.\[\]'"+-]*`（原式无法跨 `."+"`）；③ yaml 双引号转义（`\\b`、`\\\\rm`）。

## 三、绕过面样本清单（H2，全部拦截断言）

| 类别 | 样本 | 判定 |
|------|------|------|
| rm 变体 6 样本（5 选项 × 3 前缀） | `rm -rf` / `rm -fr` / `rm -r -f` / `rm --recursive --force` / `/bin/rm -rf` / `\rm -rf` | 全拦（5 选项：`-rf`/`-fr`/`-r -f`/`--recursive --force`/`-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*`；3 前缀：裸 `rm`/`/bin/rm`/`\rm`） |
| 销毁类 | `shred -u` / `unlink` / `rmdir -r` / `mv` → trash/回收站 | 全拦 |
| URL 混淆 | `oapi[.]dingtalk[.]com`（字符类点）、`"oapi."+"dingtalk.com"`（变量拼接） | 识别为通知外呼（须唯一出口） |
| 假备份 | `rm -rf /data && echo backup`、`echo "backup" && rm -rf /data`、`rm -rf /data # 已备份 /backup/a` | 拦截（剥离后无 backup） |
| 真备份 | `cp -r /data /backup/data && rm -rf /data`、`rm -rf /data --backup=/backup/a`、`tar czf /backup/x.tgz /data && rm -rf /data` | 放行 |
| 边界 | `rm -rf` 写在 echo 文本中（`echo "rm -rf /data"`） | 销毁判定用原始 cmd → 仍拦 |
| 已知限制 | `rmdir --recursive`（双横线长选项）不在 `-[a-zA-Z]*r` 覆盖内 | 不拦（登记已知限制） |

## 四、seal 双格式核对（H3）

| 格式 | 样例 | 解析规则 |
|------|------|---------|
| ① unit_test 八格式 | `测试总数: 20` / `成功: 20` / `失败: 0` / `错误: 0` | 四数字齐全才算命中；passed=成功数；失败+错误>0 → 拒绝 |
| ② unittest 原生 | `Ran 106 tests` + `OK`（或 `FAILED (failures=1)`） | `Ran N tests` + OK → passed=total；FAILED → 拒绝 |

- 八格式优先、原生格式回退；同一文件双格式交叉核对不一致 → 拒绝（防伪造）；
- **汇总段判定**（H3 回归修复）：原生格式的 OK/FAILED 判定**仅限 "Ran N tests" 行之后的
  汇总段**——unittest -v 输出中反案例测试的 docstring/测试名可能含 "FAILED" 字样
  （如 test_parse_native_format_failed），全文搜索会把真实通过结果误判为失败；
  截取汇总段后正文字样不再影响判定，汇总段缺失/无法判定 → 拒绝（fail-closed）；
- 多 result 文件「任一拒绝即整体拒绝」，落闸数字 = 各文件解析值合计；
- 落闸走 `build_gate_v2`（契约零改动），落盘后 `.gate.json` 的 total/passed 与 result 一致，可被 gate_open 与 token 摘要复证；
- 真实样例验证：`unit_test/test/test_harness_topology_result.txt` 同时含原生（Ran 20 tests）+ 八格式（20/20）→ 交叉核对一致通过。

## 五、续签机制 re-seal（H4）

语义（任务书 4.5 + 编排决策 3）：
1. 读现有 `.gate.json`；不存在/不可解析 → 拒绝（无闸可续）；
2. `schema_version==2` 且 `run_id` 一致（拒绝跨任务续签）；
3. 重读 result 文件重新核对：数字与 .gate.json 不符 / 文件缺失 → 拒绝（防 result 被改后沿用旧闸）；
4. 构造新 gate：仅 `updated_at=now` 并重算 `gate_token`，其余字段（run_id/task_dir/test_passed/total/passed/written_by/result_files）全部原样；
5. flock 独占锁落盘（与 seal 同锁）；
6. 写 `event_type=re_seal` 审计事件（`runlog/events/YYYYMMDD/<run_id>.jsonl`，recorder schema，`VALID_EVENT_TYPES` 已追加 `re_seal`）。

CLI：`python -m harness.core.cli re-seal --task-dir ... --run-id ... --secret-file ... [--runlog ...] [--project ...] [--json]`
编排器：`charter-orchestrator.reSeal()`（GATE_STALE 时自主执行）；插件阻断消息附续签提示。

## 六、脱敏迁移对照（H5）

| 旧版（.opencode/plugin/charter-gate.ts，只读参考） | 新版（harness 体系） |
|------|------|
| L80-84 `SECRET_PATTERNS`（3 类正则） | `harness/core/redact.py` `DEFAULT_SECRET_PATTERNS`（语义零改动）+ `gate_rules.yaml` `secret_patterns` 可选段 |
| L86-96 `redactSecrets`（依次 replace + 计数） | `redact.redact_secrets(text, patterns=None) -> (text, hits)`（纯函数，`re.subn` 累计） |
| L132-146 `chat.message` 钩子（脱敏 + warn） | `harness/plugins/charter-gate.ts` `chatMessage` 钩子（子进程调 `cli.py redact`） |
| 告警文本 | 与旧版一致：「检测到 N 处疑似明文凭据，已脱敏」 |

## 七、资产检查迁移对照（H6）

| 旧版（.opencode/plugin/charter-gate.ts） | 新版（harness 体系） |
|------|------|
| L56-78 `resolveResourceMapPath`（.harness-env HARNESS_DIR → 宿主地图，回退当前项目） | `harness/core/assets_check.py` `resolve_resource_map_path(project_dir)`（纯函数） |
| L148-158 `tool.execute.after`（docs/hetu-*/ + includes(basename)） | `check_registered(file_path, map_path) -> (ok, reason)` + charter-gate.ts `after` 钩子（软告警） |
| 匹配语义 | 仅 `docs/hetu-*/` 前缀路径检查；basename 出现在资源地图文本即已登记 |

## 八、密钥与并发方案（H7/H9）

**密钥（H7）**：
- `secret.check_permission`：600 强制校验（decide/seal 路径告警）；
- `secret.load_secret(enforce_600=True)`：权限非 600 自动修正后重读；
- `secret.rotate_secret`：openssl rand -hex 32（回退 /dev/urandom 64 字节，同 install_dsh.sh L56-60）→ 原子写入（临时文件 + rename，防半写）→ chmod 600；轮换后旧闸 token（旧密钥 HMAC）自然失效；
- `scripts/install_dsh.sh`：密钥生成/已存在均强制 `chmod 600`（修正历史 777）；`gate_rules.yaml` 缺失时从默认模板生成（已存在不覆盖，保留用户配置）。

**并发（H9）**：
- `seal.write_gate_locked(gate_file, gate_dict, expected_updated_at)`：`open(a+)` + `fcntl.flock(LOCK_EX)` → 锁内重读 → 非法 JSON 拒绝「文件损坏」/ updated_at 与预期不符拒绝「已被并发更新，请重试」→ truncate 写入 → 解锁；
- seal-gate 与 re-seal 共用同一锁与比对逻辑（expected 为落盘前读取的现有 updated_at，首次落闸为 None）；
- 双进程实测（WSL 环境）：并发 seal 串行化成功或后写者报并发更新，`.gate.json` 内容完整合法（JSON + token 校验通过）；
- 平台注意：`fcntl` 仅 linux/unix；Windows 分支（msvcrt.locking）留注释不实现（当前无 Windows 运行需求）。

## 九、测试与回归

- 运行：`../venv-hetu/bin/python -m unittest discover -s unit_test -p "test_*.py"`
- 结果：`discover` 全量 **201/201** 全绿（原 110/110 + 新增 91；`unit_test/test/test_harness_dsh_result.txt` 已更新；
  含 H3 回归修复 1 例 `test_dual_format_body_contains_failed_word`、REVISE 第1轮修复反例
  `test_backup_section_missing_rejected` / `test_backup_pattern_missing_rejected` / `test_real_mtime_reload_without_reset` /
  `TestRulesSecretPatterns` 3 例）；落闸口径 = dsh 201 + topology 20 = **221/221**
- 契约守护：`test_gate_token.py` 直接依赖 `build_gate_v2`（L40/60/76/128/165/207/226），契约零改动回归；历史 `.gate.json`（20260804 系列为 v1 格式）按既有 GATE_SCHEMA 语义拒绝，20260814+ v2 格式正常 gate_open。

## 十、已知限制与遗留

1. `rmdir --recursive` 双横线长选项不在拦截覆盖内（`-[a-zA-Z]*r` 仅单横线变体），如需纵深可后续扩展规则；
2. `rm -r`（递归但不带 -f）不拦截（与现状语义一致，未扩大拦截面）；
3. DSH 运行时 `chatMessage` / `tool.after` 等价中间件名未在运行时确认（按与 before 同机制接入）；若运行时无等价钩子，脱敏/资产检查以纯函数核心 + CLI 为准（单测守护），钩子按运行时实际机制补挂；
4. 插件与 .opencode 旧配置修改后需**重启 DSH/opencode 生效**，不影响 Python 核心（判定逻辑即时生效）；
5. **WSL 环境限制（REVISE 第1轮登记）**：`/mnt/d` 为 9p/drvfs 挂载且无 `metadata` 选项，`chmod` 权限位不生效——`conf/gate_secret` 实测仍 777（`bash scripts/install_dsh.sh` 的 `chmod 600` 已就位且逻辑正确，权限断言单测在 /tmp（ext4）验证通过），在原生 Linux 部署环境 install 后即为 600；
6. **resolveEnv 宿主自身场景（REVISE 第1轮登记，20260814 既有模式）**：`.harness-env` 缺失时 `charter-gate.ts`/`charter-orchestrator.ts` 的 `VENV_BIN` 回退 `python3`，宿主自身 python3 可能缺 pyyaml 导致子进程调用失败；后续可在 resolveEnv 增加「宿主自身时探测 `../venv-hetu/bin/python`」。
