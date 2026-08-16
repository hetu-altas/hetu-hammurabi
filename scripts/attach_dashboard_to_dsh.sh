#!/usr/bin/env bash
# ============================================================
# attach_dashboard_to_dsh.sh · 把宪章运行看板挂接到 DSH web GUI
#
# 效果：dsh web 启动后访问 http://127.0.0.1:<dsh端口>/dashboard 即见看板
#   （插件注册 /dashboard 前缀路由，代理到看板服务 8790）。
#
# 用法：
#   bash scripts/attach_dashboard_to_dsh.sh               # 挂接（默认 web profile）
#   bash scripts/attach_dashboard_to_dsh.sh --check       # 只检查不写入
#   bash scripts/attach_dashboard_to_dsh.sh --detach      # 卸载挂接
#
# 前提：看板服务需保持运行（bash scripts/start_dashboard.sh）。
# 注意：本脚本写入 $DSH_HOME（用户级配置），需在部署机执行；幂等可重复运行。
# ============================================================
set -euo pipefail

HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DSH_HOME="${DSH_HOME:-$HOME/.dsh}"
PROFILE_DIR="$DSH_HOME/profiles/web"
PLUGIN_SRC="$HARNESS_DIR/harness/dsh/plugins/dashboard-proxy.ts"
PLUGIN_NAME="hetu-dashboard-proxy"
PLUGIN_DEST="$PROFILE_DIR/plugins/$PLUGIN_NAME.ts"
PATCH_FILE="$PROFILE_DIR/cordis.patch.yml"
PYTHON_BIN="${PYTHON_BIN:-$HARNESS_DIR/../venv-hetu/bin/python}"
[ -x "$PYTHON_BIN" ] || PYTHON_BIN="python3"

MODE="attach"
for arg in "$@"; do
  case "$arg" in
    --check) MODE="check" ;;
    --detach) MODE="detach" ;;
  esac
done

echo "[attach] DSH home: $DSH_HOME"
echo "[attach] web profile: $PROFILE_DIR"

if [ ! -d "$PROFILE_DIR" ]; then
  echo "[attach] 错误: web profile 不存在（$PROFILE_DIR）。请先运行 dsh web 初始化。" >&2
  exit 1
fi
if [ ! -f "$PLUGIN_SRC" ]; then
  echo "[attach] 错误: 插件源文件不存在: $PLUGIN_SRC" >&2
  exit 1
fi

# ---------- 生成 patch 条目（YAML） ----------
# 用 Python 安全地读写 YAML（保留现有条目，幂等去重）
PATCH_ENTRY="$("$PYTHON_BIN" - "$PLUGIN_DEST" <<'PYEOF'
import sys
dest = sys.argv[1]
print(f"""- insert:
    - id: {dest.rsplit("/", 1)[-1].removesuffix(".ts")}
      name: "{dest}" """.rstrip())
PYEOF
)"

case "$MODE" in
  check)
    echo "[attach] --check 模式，仅打印将执行的变更："
    echo "  1. 复制插件: $PLUGIN_SRC -> $PLUGIN_DEST"
    echo "  2. 追加 patch 条目到 $PATCH_FILE:"
    echo "$PATCH_ENTRY" | sed 's/^/     /'
    echo "[attach] 检查完成（未写入）。"
    exit 0
    ;;
  detach)
    echo "[attach] 卸载挂接..."
    rm -f "$PLUGIN_DEST"
    "$PYTHON_BIN" - "$PATCH_FILE" <<'PYEOF'
import sys, yaml, pathlib
patch_file = pathlib.Path(sys.argv[1])
if not patch_file.is_file():
    print("[attach] patch 文件不存在，无需处理"); raise SystemExit(0)
data = yaml.safe_load(patch_file.read_text(encoding="utf-8")) or []
kept = []
removed = False
for row in data:
    if isinstance(row, dict) and "insert" in row:
        items = row["insert"]
        if isinstance(items, list):
            items = [it for it in items if not (isinstance(it, dict) and str(it.get("name", "")).endswith("dashboard-proxy.ts"))]
            removed = removed or len(items) != len(row["insert"])
            if items:
                row["insert"] = items
                kept.append(row)
            continue
    kept.append(row)
patch_file.write_text(yaml.safe_dump(kept, allow_unicode=True, sort_keys=False), encoding="utf-8")
print("[attach] patch 已清理" if removed else "[attach] patch 无该插件条目")
PYEOF
    echo "[attach] 卸载完成。重启 dsh web 生效。"
    exit 0
    ;;
esac

# ---------- 挂接 ----------
echo "[attach] 1/2 复制插件..."
mkdir -p "$(dirname "$PLUGIN_DEST")"
cp "$PLUGIN_SRC" "$PLUGIN_DEST"
echo "[attach]     $PLUGIN_DEST"

echo "[attach] 2/2 追加 patch 条目（幂等）..."
"$PYTHON_BIN" - "$PATCH_FILE" "$PLUGIN_DEST" <<'PYEOF'
import sys, yaml, pathlib
patch_file = pathlib.Path(sys.argv[1])
plugin_dest = sys.argv[2]
plugin_id = plugin_dest.rsplit("/", 1)[-1].removesuffix(".ts")
data = yaml.safe_load(patch_file.read_text(encoding="utf-8")) if patch_file.is_file() else []
if data is None:
    data = []
# 幂等：已存在则跳过
for row in data:
    if isinstance(row, dict) and "insert" in row:
        for it in row["insert"] or []:
            if isinstance(it, dict) and it.get("id") == plugin_id:
                print(f"[attach] patch 已含 {plugin_id}，跳过")
                raise SystemExit(0)
data.append({"insert": [{"id": plugin_id, "name": plugin_dest}]})
patch_file.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
print(f"[attach] patch 已追加条目 {plugin_id} -> {plugin_dest}")
PYEOF

echo ""
echo "[attach] ====== 挂接完成 ======"
echo "[attach] 1. 确保看板服务运行: bash $HARNESS_DIR/scripts/start_dashboard.sh"
echo "[attach] 2. 重启 dsh web（配置启动时加载）"
echo "[attach] 3. 浏览器访问: http://127.0.0.1:3080/dashboard （端口按你的 dsh web 实际端口）"
echo "[attach] 卸载: bash $0 --detach"
