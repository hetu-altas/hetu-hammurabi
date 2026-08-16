#!/usr/bin/env bash
# ============================================================
# attach_native_panel.sh · 宪章看板原生面板一键挂接（DSH client-plugin）
#
# 把 20260814 任务2 的全部挂接步骤固化为幂等脚本：
#   1. 同步包副本（仓库 harness/dsh/hetu-dashboard/ -> web profile packages/）
#   2. 校验包三要件（exports ./client + ./package.json、dsh.client、__ModuleLoader__ id=包名）
#   3. 注册 bundle（profile package.json 的 dsh.profile.bundles + 包内 cordis.patch.yml）
#   4. 校验配置树（dsh --profile web --dump-config）
#   5. 提示重启
#
# 用法：
#   bash scripts/attach_native_panel.sh            # 挂接（幂等）
#   bash scripts/attach_native_panel.sh --check    # 只校验不写入
#
# 前置：看板数据服务（8790）另行运行（bash scripts/start_dashboard.sh）。
# ============================================================
set -euo pipefail

HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DSH_HOME="${DSH_HOME:-$HOME/.dsh}"
PROFILE_DIR="$DSH_HOME/profiles/web"
PKG_SRC="$HARNESS_DIR/harness/dsh/hetu-dashboard"
PKG_NAME="@hetu/dsh-dashboard-panel"
PKG_DEST="$PROFILE_DIR/packages/hetu-dashboard"
PROFILE_PKG="$PROFILE_DIR/package.json"
PATCH_FILE="$PROFILE_DIR/cordis.patch.yml"
PYTHON_BIN="${PYTHON_BIN:-$HARNESS_DIR/../venv-hetu/bin/python}"
[ -x "$PYTHON_BIN" ] || PYTHON_BIN="python3"

MODE="attach"
for arg in "$@"; do
  case "$arg" in
    --check) MODE="check" ;;
  esac
done

echo "[panel] DSH home: $DSH_HOME"
if [ ! -d "$PROFILE_DIR" ]; then
  echo "[panel] 错误: web profile 不存在（先运行一次 dsh web 初始化）" >&2
  exit 1
fi

# ---------- 1. 校验包三要件（挂接失败的三个已知坑，全部固化为校验） ----------
check_pkg() {
  local src="$1" err=0
  "$PYTHON_BIN" - "$src" <<'PYEOF' || err=1
import json, pathlib, re, sys
src = pathlib.Path(sys.argv[1])
pkg = json.loads((src / "package.json").read_text(encoding="utf-8"))
errors = []
exports = pkg.get("exports") or {}
if exports.get("./client") is None: errors.append("exports 缺 ./client（browser 半区入口）")
if exports.get("./package.json") is None: errors.append("exports 缺 ./package.json（modules require.resolve 必需！）")
dsh = pkg.get("dsh") or {}
if dsh.get("bundle", {}).get("patch") is None: errors.append("dsh.bundle.patch 缺失（bundle 注册必需）")
client = dsh.get("client") or {}
if client.get("platform") != "web": errors.append("dsh.client.platform 必须为 web")
client_js = src / "client.js"
if not client_js.is_file(): errors.append("client.js 缺失（browser 半区产物）")
else:
    text = client_js.read_text(encoding="utf-8")
    m = re.search(r'__ModuleLoader__\.load\(\{\s*id:\s*"([^"]+)"', text)
    if not m: errors.append("client.js 未按 __ModuleLoader__.load({id, factory}) 包装")
    elif m.group(1) != pkg.get("name"): errors.append(f'client.js load id 必须等于包名 {pkg.get("name")!r}（当前 {m.group(1)!r}）')
for e in errors: print("[panel]   ✗ " + e)
if errors: sys.exit(1)
print("[panel]   ✓ 包三要件校验通过（exports ./client + ./package.json / dsh.client / load id=包名）")
PYEOF
  return $err
}

echo "[panel] 1/4 校验包要件..."
check_pkg "$PKG_SRC" || { echo "[panel] 错误: 仓库包不满足挂接要件，请先修复 harness/dsh/hetu-dashboard/" >&2; exit 1; }

# ---------- 2. 同步包副本 ----------
if [ "$MODE" = "check" ]; then
  echo "[panel] --check 模式，以下写入将被跳过（仅校验）"
  echo "[panel] 将同步: $PKG_SRC -> $PKG_DEST"
else
  echo "[panel] 2/4 同步包副本..."
  mkdir -p "$PKG_DEST/lib"
  cp "$PKG_SRC/package.json" "$PKG_DEST/package.json"
  cp "$PKG_SRC/client.js" "$PKG_DEST/lib/client.js"
  cp "$PKG_SRC/lib/index.js" "$PKG_DEST/lib/index.js" 2>/dev/null || true
  cat > "$PKG_DEST/cordis.patch.yml" <<EOF
- insert:
    - id: hetu-dashboard
      name: '$PKG_NAME'
EOF
  echo "[panel]   $PKG_DEST 已同步"

  # ---------- 3. 注册 bundle（幂等） ----------
  echo "[panel] 3/4 注册 bundle..."
  "$PYTHON_BIN" - "$PROFILE_PKG" "$PKG_NAME" <<'PYEOF'
import json, pathlib, sys
path, name = sys.argv[1], sys.argv[2]
data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
bundles = data.setdefault("dsh", {}).setdefault("profile", {}).setdefault("bundles", [])
if name not in bundles:
    bundles.append(name)
    pathlib.Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[panel]   bundles 已追加 {name}")
else:
    print(f"[panel]   bundles 已含 {name}，跳过")
PYEOF

  # ---------- 4. 校验配置树 ----------
  echo "[panel] 4/4 校验配置树..."
  if DSH_BIN="$(command -v dsh || true)" && [ -n "$DSH_BIN" ]; then
    dsh --profile web --dump-config 2>/dev/null | grep -q "hetu-dashboard" \
      && echo "[panel]   ✓ 配置树含 hetu-dashboard" \
      || echo "[panel]   ⚠ 配置树未见 hetu-dashboard（可忽略，重启后以实际为准）"
  else
    echo "[panel]   （dsh 不在 PATH，跳过配置树校验）"
  fi
fi

echo ""
echo "[panel] ====== 完成 ======"
echo "[panel] 1. 确保数据服务: bash $HARNESS_DIR/scripts/start_dashboard.sh"
echo "[panel] 2. 重启 dsh web（配置启动时加载）: 终端 Ctrl+C 后重新 npm exec @deepseek-ai/dsh web"
echo "[panel] 3. GUI 侧边栏底部出现「📊 宪章看板」按钮即挂接成功"
echo "[panel] 卸载: 从 $PROFILE_PKG 的 bundles 移除 $PKG_NAME 并删除 $PKG_DEST"
