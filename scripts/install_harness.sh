#!/usr/bin/env bash
# ============================================================
# 将 hetu-hammurabi 的宪章编程 harness（.opencode）软链到同级各 hetu-* 业务项目
# 用法：bash scripts/install_harness.sh
# 说明：openccode 只发现"当前工作树"下的 .opencode/，业务项目需软链本 harness。
# ============================================================
set -euo pipefail

HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PARENT_DIR="$(cd "$HARNESS_DIR/.." && pwd)"

echo "[harness] $HARNESS_DIR"
for sub in agents commands skills plugin; do
  for proj in "$PARENT_DIR"/hetu-*; do
    [ -d "$proj" ] || continue
    name="$(basename "$proj")"
    [ "$name" = "hetu-hammurabi" ] && continue
    mkdir -p "$proj/.opencode"
    ln -sfn "$HARNESS_DIR/.opencode/$sub" "$proj/.opencode/$sub"
    echo "[link] $name/.opencode/$sub -> $HARNESS_DIR/.opencode/$sub"
  done
done

echo "完成。在任一业务项目内输入 /dev <任务书路径> 即可启动宪章研发流程。"
