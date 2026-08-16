#!/usr/bin/env bash
# 启动宪章体系运行看板服务（DSH 重构版）
# 用法: bash scripts/start_dashboard.sh [端口]   （默认 8790）
set -euo pipefail

HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${1:-8790}"
VENV_BIN="${HARNESS_DIR}/../venv-hetu/bin"
PYTHON="${VENV_BIN}/python"

if [ ! -x "${PYTHON}" ]; then
  echo "[dashboard] 未找到共享 venv: ${PYTHON}（请检查 ../venv-hetu 布局）" >&2
  exit 1
fi

cd "${HARNESS_DIR}"
echo "[dashboard] 启动看板: http://127.0.0.1:${PORT}"
echo "[dashboard] 数据源: runlog/events（实时）+ opencode_schedule（历史解析）"
exec "${PYTHON}" -m uvicorn harness.core.api:app \
  --host 127.0.0.1 --port "${PORT}" --log-level warning
