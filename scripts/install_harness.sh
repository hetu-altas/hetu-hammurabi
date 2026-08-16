#!/usr/bin/env bash
# ============================================================
# 将 harness 宿主（本脚本所在项目）的宪章编程 harness（.opencode）
# 安装/重装到同父目录下的全部 hetu-* 业务项目（可选参数追加指定项目）。
# 用法：
#   bash scripts/install_harness.sh               # 安装到全部平级 hetu-* 项目
#   bash scripts/install_harness.sh hetu-sybil    # 仅安装到指定项目（支持非 hetu-* 前缀项目）
# 说明：opencode 只发现"当前工作树"下的 .opencode/，业务项目需软链本 harness。
# 说明：宿主判定基于结构特征（.opencode/agents/ + constitution/constitution.md + docs/资源地图.md），
#       由 scripts/harness_topology.py 解析，不写死任何具体项目名。
# 说明：生成物 .opencode/.harness-env 含绝对路径，禁止入库（自动追加 .gitignore 忽略）。
# ============================================================
set -euo pipefail

HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKSPACE_DIR="$(cd "$HARNESS_DIR/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
TOPOLOGY_SCRIPT="$HARNESS_DIR/scripts/harness_topology.py"
LINK_ITEMS=(agents commands skills plugin package.json package-lock.json)

# 工具：执行拓扑脚本 --json 子命令并取指定字段
json_field() {
  local data="$1" field="$2"
  "$PYTHON_BIN" -c "import json,sys; print(json.loads(sys.stdin.read()).get('$field',''))" <<< "$data"
}

echo "[harness] harness 宿主: $HARNESS_DIR"
echo "[harness] 工作区(同父目录): $WORKSPACE_DIR"

# 1. 宿主校验：结构特征判定，防止脚本被拷贝到非宿主目录误用
DETECT_JSON="$("$PYTHON_BIN" "$TOPOLOGY_SCRIPT" --json detect-host --workspace "$WORKSPACE_DIR")" || {
  echo "[harness] 错误: 拓扑解析失败，当前目录不满足宿主三要件（.opencode/agents/ + constitution/constitution.md + docs/资源地图.md）" >&2
  echo "$DETECT_JSON" >&2
  exit 1
}
DETECTED_HOST="$(json_field "$DETECT_JSON" host_dir)"
if [ -z "$DETECTED_HOST" ] || [ "$DETECTED_HOST" != "$HARNESS_DIR" ]; then
  echo "[harness] 错误: 当前目录不是 harness 宿主（拓扑解析结果为: ${DETECTED_HOST:-空}）" >&2
  exit 1
fi

# 宿主自身 .opencode/.gitignore 同步追加 .harness-env 忽略（防宿主误提交）
host_gitignore="$HARNESS_DIR/.opencode/.gitignore"
touch "$host_gitignore"
if [ -s "$host_gitignore" ]; then
  tail -c 1 "$host_gitignore" | grep -q $'\n' || printf '\n' >> "$host_gitignore"
fi
grep -qxF ".harness-env" "$host_gitignore" || printf '.harness-env\n' >> "$host_gitignore"

# 2. 目标范围：同父目录下全部 hetu-* 项目（除宿主外）+ 可选追加参数
EXTRA="${1:-}"
if [ -n "$EXTRA" ]; then
  LIST_JSON="$("$PYTHON_BIN" "$TOPOLOGY_SCRIPT" --json list-targets --workspace "$WORKSPACE_DIR" --host "$HARNESS_DIR" --extra "$EXTRA")"
else
  LIST_JSON="$("$PYTHON_BIN" "$TOPOLOGY_SCRIPT" --json list-targets --workspace "$WORKSPACE_DIR" --host "$HARNESS_DIR")"
fi

mapfile -t TARGETS < <("$PYTHON_BIN" -c "import json,sys; [print(x) for x in json.loads(sys.stdin.read()).get('targets',[])]" <<< "$LIST_JSON")
mapfile -t SKIPPED < <("$PYTHON_BIN" -c "import json,sys; [print(x) for x in json.loads(sys.stdin.read()).get('skipped',[])]" <<< "$LIST_JSON")

for skip in ${SKIPPED[@]+"${SKIPPED[@]}"}; do
  echo "[harness] 提示: extra 指定项目不存在，已忽略: $skip"
done

if [ "${#TARGETS[@]}" -eq 0 ]; then
  echo "[harness] 未发现任何目标项目（同父目录下除宿主外无 hetu-* 项目）。"
  exit 0
fi

# 3. 逐项目安装（幂等：软链覆盖 + .harness-env 重写 + .gitignore 补齐）
for proj in "${TARGETS[@]}"; do
  name="$(basename "$proj")"
  echo "[harness] ==== 安装到 $name ($proj) ===="
  mkdir -p "$proj/.opencode"

  # 3.1 生成 .harness-env（每次重写；文件头注明勿手改）
  "$PYTHON_BIN" "$TOPOLOGY_SCRIPT" --build-env --project "$proj" --workspace "$WORKSPACE_DIR" --host "$HARNESS_DIR" > "$proj/.opencode/.harness-env"

  # 3.2 软链补全（agents/commands/skills/plugin/package.json/package-lock.json；node_modules 不软链，各项目自行 npm install）
  for item in "${LINK_ITEMS[@]}"; do
    ln -sfn "$HARNESS_DIR/.opencode/$item" "$proj/.opencode/$item"
  done

  # 3.3 .gitignore 补齐（.harness-env 含绝对路径，禁止入库）
  gitignore_file="$proj/.opencode/.gitignore"
  touch "$gitignore_file"
  # 确保文件末尾有换行，避免追加项拼接到最后一行行尾
  if [ -s "$gitignore_file" ]; then
    tail -c 1 "$gitignore_file" | grep -q $'\n' || printf '\n' >> "$gitignore_file"
  fi
  grep -qxF ".harness-env" "$gitignore_file" || printf '.harness-env\n' >> "$gitignore_file"

  echo "[harness] 完成: $name 的 ${LINK_ITEMS[*]} -> $HARNESS_DIR/.opencode/...（node_modules 未软链，首次运行 opencode 前需 npm install）"
done

# 4. 输出对照表
echo ""
echo "[harness] ====== 安装对照表（项目 -> HARNESS_DIR / AETHER_DIR / VENV_BIN）======"
for proj in "${TARGETS[@]}"; do
  name="$(basename "$proj")"
  env_file="$proj/.opencode/.harness-env"
  hd="$(grep '^HARNESS_DIR=' "$env_file" | head -1 | cut -d= -f2- | tr -d '"')"
  ad="$(grep '^AETHER_DIR=' "$env_file" | head -1 | cut -d= -f2- | tr -d '"')"
  vb="$(grep '^VENV_BIN=' "$env_file" | head -1 | cut -d= -f2- | tr -d '"')"
  echo "[harness] $name -> HARNESS_DIR=${hd:-<回退查找>} | AETHER_DIR=${ad:-<回退查找>} | VENV_BIN=${vb:-<回退查找>}"
done
echo "[harness] ============================================================="
echo ""
echo "[harness] 完成。在任一业务项目内输入 /cc <任务书路径> 即可启动宪章研发流程。"
echo "[harness] 提示: 若项目 .opencode/node_modules 不存在，首次启动 opencode 前请先在该项目执行 npm install。"
