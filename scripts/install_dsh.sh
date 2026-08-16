#!/usr/bin/env bash
# ============================================================
# install_dsh.sh · 安装/注册 DSH 宪章体系（DSH 重构版）
#
# 用法：
#   bash scripts/install_dsh.sh               # 注册 profile + 安装到全部平级 hetu-* 项目
#   bash scripts/install_dsh.sh hetu-sybil    # 仅安装到指定项目（支持非 hetu-* 前缀项目）
#
# 步骤：
#   1. 生成宿主 conf/gate_secret（门禁密钥，.gate.json v2 token 签名用，自动 gitignore）
#   2. 注册 DSH profile 到 $DSH_HOME/profiles/hetu-hammurabi（软链 plugins）
#   3. 逐业务项目：.opencode/.harness-env（复用 harness_topology.py 六字段契约）
#      + 软链 harness 组件（agents/skills/plugins/workflow.yaml）到项目 harness/
#   4. 校验输出对照表
#
# 与旧体系并行：本脚本不动业务项目已有的 .opencode/ 软链（迁移期并存，
# 旧 opencode 流程仍可用；下线属任务2）。
# ============================================================
set -euo pipefail

HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKSPACE_DIR="$(cd "$HARNESS_DIR/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$WORKSPACE_DIR/venv-hetu/bin/python}"
if [ ! -x "$PYTHON_BIN" ]; then PYTHON_BIN="python3"; fi
TOPOLOGY_SCRIPT="$HARNESS_DIR/scripts/harness_topology.py"
DSH_HOME="${DSH_HOME:-$HOME/.dsh}"
PROFILE_NAME="hetu-hammurabi"
PROFILE_DIR="$DSH_HOME/profiles/$PROFILE_NAME"
LINK_ITEMS=(agents skills plugins workflow.yaml)

json_field() {
  local data="$1" field="$2"
  "$PYTHON_BIN" -c "import json,sys; print(json.loads(sys.stdin.read()).get('$field',''))" <<< "$data"
}

echo "[dsh-harness] harness 宿主: $HARNESS_DIR"
echo "[dsh-harness] 工作区(同父目录): $WORKSPACE_DIR"
echo "[dsh-harness] DSH home: $DSH_HOME"

# ---------- 1. 宿主校验（结构特征，复用拓扑脚本） ----------
DETECT_JSON="$("$PYTHON_BIN" "$TOPOLOGY_SCRIPT" --json detect-host --workspace "$WORKSPACE_DIR")" || {
  echo "[dsh-harness] 错误: 拓扑解析失败（需含 harness/agents/ 或 .opencode/agents/ + constitution + docs/资源地图.md）" >&2
  exit 1
}
DETECTED_HOST="$(json_field "$DETECT_JSON" host_dir)"
if [ -z "$DETECTED_HOST" ] || [ "$DETECTED_HOST" != "$HARNESS_DIR" ]; then
  echo "[dsh-harness] 错误: 当前目录不是 harness 宿主（拓扑解析结果: ${DETECTED_HOST:-空}）" >&2
  exit 1
fi

# ---------- 2. 生成门禁密钥（token 信任模型 D2 的宿主秘密） ----------
mkdir -p "$HARNESS_DIR/conf"
SECRET_FILE="$HARNESS_DIR/conf/gate_secret"
if [ ! -s "$SECRET_FILE" ]; then
  umask 077
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 32 > "$SECRET_FILE"
  else
    head -c 64 /dev/urandom | od -An -tx1 | tr -d ' \n' > "$SECRET_FILE"
  fi
  echo "[dsh-harness] 已生成门禁密钥: $SECRET_FILE"
else
  echo "[dsh-harness] 门禁密钥已存在: $SECRET_FILE"
fi
# H7（20260815任务1）：密钥权限强制 600（含已存在文件——修正历史 777）
chmod 600 "$SECRET_FILE"
echo "[dsh-harness] 门禁密钥权限: $(stat -c '%a' "$SECRET_FILE")（须为 600）"
# 密钥禁止入库
if [ -f "$HARNESS_DIR/.gitignore" ]; then
  grep -qxF "conf/gate_secret" "$HARNESS_DIR/.gitignore" || printf 'conf/gate_secret\n' >> "$HARNESS_DIR/.gitignore"
fi

# ---------- 2.5 生成默认门禁规则（H1：gate_rules.yaml 缺失时从默认模板生成） ----------
RULES_FILE="$HARNESS_DIR/harness/gate_rules.yaml"
if [ ! -f "$RULES_FILE" ]; then
  cat > "$RULES_FILE" <<'YAML_EOF'
# 宪章门禁判定规则（规则外置，20260815任务1）
# 修改任一模式后不重启即生效（mtime 检测）；文件缺失/非法 → 回退内置默认（fail-closed）
schema_version: 1
freshness_seconds: 600
log_file:
  main_pattern: "研发日志"
  ext_pattern: "日志"
  allowlist:
    - "数据日志说明.md"
  task_dir_pattern: "opencode_schedule[/\\\\]\\d{8}[/\\\\][^/\\\\]+[/\\\\]"
audit_files:
  - "研发流程状态.md"
notify:
  url_patterns:
    - "oapi\\s*[.\\[\\]]\\s*dingtalk\\s*[.\\[\\]]\\s*com"
    - "oapi\\s*[.\\[\\]'\"+-]*\\s*dingtalk\\s*[.\\[\\]'\"+-]*\\s*com"
    - "robot\\s*/\\s*send"
  func_patterns:
    - "util_dingtalk"
    - "send_markdown|send_text"
    - "HARNESS_NOTIFY"
    - "harness\\.core\\.notify"
  allow_patterns:
    - "HARNESS_NOTIFY"
    - "harness\\.core\\.notify"
dangerous_commands:
  rm_recursive: "(?:\\brm|/bin/rm|\\\\rm)\\s+(?:-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*|-r\\s+-f|--recursive\\s+--force|-fr|-rf)\\b"
  shred: "\\bshred\\b"
  unlink: "\\bunlink\\b"
  rmdir_recursive: "\\brmdir\\s+-[a-zA-Z]*r"
  mv_trash: "\\bmv\\b.*(?:回收站|trash)"
  drop_table: "\\bDROP\\s+(TABLE|STABLE)\\b"
  delete_from: "\\bDELETE\\s+FROM\\b"
  truncate: "\\bTRUNCATE\\b"
  drop_collection: "\\bdrop_collection\\b"
backup:
  pattern: "backup|备份"
  semantic: enforce
secret_patterns:
  - "sk-[a-zA-Z0-9]{16,}"
  - "Bearer\\s+[a-zA-Z0-9._~+/=-]+"
  - "(?:password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|access_token)\\s*[=:]\\s*['\"]?[^\\s'\"]{8,}"
YAML_EOF
  echo "[dsh-harness] 已生成默认门禁规则: $RULES_FILE"
else
  echo "[dsh-harness] 门禁规则已存在（不覆盖，保留用户配置）: $RULES_FILE"
fi

# ---------- 3. 注册 DSH profile ----------
mkdir -p "$PROFILE_DIR"
cp "$HARNESS_DIR/harness/package.json" "$PROFILE_DIR/package.json"
cp "$HARNESS_DIR/harness/dsh.profile" "$PROFILE_DIR/dsh.profile"
# cordis.patch.yml：渲染 ${HARNESS_DIR} 占位后写入（不污染源文件）
sed "s|\${HARNESS_DIR}|$HARNESS_DIR|g" "$HARNESS_DIR/harness/cordis.patch.yml" > "$PROFILE_DIR/cordis.patch.yml"
# 软链 plugins（TS 插件）；core 为 Python 模块，运行期从 HARNESS_DIR 导入，不软链
ln -sfn "$HARNESS_DIR/harness/plugins" "$PROFILE_DIR/plugins"
echo "[dsh-harness] DSH profile 已注册: $PROFILE_DIR"
echo "[dsh-harness] 启动命令: dsh --profile $PROFILE_NAME \"<任务书路径 或 一句话需求>\""

# ---------- 4. 目标范围：同父目录全部 hetu-* 项目 + 可选参数 ----------
EXTRA="${1:-}"
if [ -n "$EXTRA" ]; then
  LIST_JSON="$("$PYTHON_BIN" "$TOPOLOGY_SCRIPT" --json list-targets --workspace "$WORKSPACE_DIR" --host "$HARNESS_DIR" --extra "$EXTRA")"
else
  LIST_JSON="$("$PYTHON_BIN" "$TOPOLOGY_SCRIPT" --json list-targets --workspace "$WORKSPACE_DIR" --host "$HARNESS_DIR")"
fi
mapfile -t TARGETS < <("$PYTHON_BIN" -c "import json,sys; [print(x) for x in json.loads(sys.stdin.read()).get('targets',[])]" <<< "$LIST_JSON")

if [ "${#TARGETS[@]}" -eq 0 ]; then
  echo "[dsh-harness] 未发现目标业务项目（同父目录下除宿主外无 hetu-* 项目）。"
  exit 0
fi

# ---------- 5. 逐项目安装（幂等） ----------
for proj in "${TARGETS[@]}"; do
  name="$(basename "$proj")"
  echo "[dsh-harness] ==== 安装到 $name ($proj) ===="
  mkdir -p "$proj/.opencode" "$proj/harness"

  # 5.1 .harness-env（复用拓扑脚本六字段契约，每次重写）
  "$PYTHON_BIN" "$TOPOLOGY_SCRIPT" --build-env --project "$proj" --workspace "$WORKSPACE_DIR" --host "$HARNESS_DIR" > "$proj/.opencode/.harness-env"

  # 5.2 软链 harness 组件（agents/skills/plugins/workflow.yaml → 项目 harness/）
  for item in "${LINK_ITEMS[@]}"; do
    ln -sfn "$HARNESS_DIR/harness/$item" "$proj/harness/$item"
  done

  # 5.3 .gitignore 补齐
  gitignore_file="$proj/.opencode/.gitignore"
  touch "$gitignore_file"
  if [ -s "$gitignore_file" ]; then
    tail -c 1 "$gitignore_file" | grep -q $'\n' || printf '\n' >> "$gitignore_file"
  fi
  grep -qxF ".harness-env" "$gitignore_file" || printf '.harness-env\n' >> "$gitignore_file"

  echo "[dsh-harness] 完成: $name（.harness-env + harness/{${LINK_ITEMS[*]}} 软链）"
done

# ---------- 6. 校验输出 ----------
echo ""
echo "[dsh-harness] ====== 安装对照表（项目 -> HARNESS_DIR / VENV_BIN）======"
for proj in "${TARGETS[@]}"; do
  name="$(basename "$proj")"
  env_file="$proj/.opencode/.harness-env"
  hd="$(grep '^HARNESS_DIR=' "$env_file" | head -1 | cut -d= -f2- | tr -d '"')"
  vb="$(grep '^VENV_BIN=' "$env_file" | head -1 | cut -d= -f2- | tr -d '"')"
  echo "[dsh-harness] $name -> HARNESS_DIR=${hd:-<回退查找>} | VENV_BIN=${vb:-<回退查找>}"
done
echo "[dsh-harness] =========================================================="
echo "[dsh-harness] 完成。DSH 启动命令: dsh --profile $PROFILE_NAME \"<任务书路径 或 一句话需求>\""
echo "[dsh-harness] 看板启动命令: bash $HARNESS_DIR/scripts/start_dashboard.sh"
