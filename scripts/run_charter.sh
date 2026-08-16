#!/usr/bin/env bash
# ============================================================
# run_charter.sh · DSH 下启动宪章编程流程（/cc 等价物，C1）
#
# 在业务项目目录执行，构造编排提示词（注入 workflow.yaml + 宪章 + 门禁约定），
# 调用 dsh headless 模式启动完整研发流程（节点 -1~7）。
#
# 用法（在业务项目目录，如 hetu-thoth）：
#   bash <HARNESS_DIR>/scripts/run_charter.sh <任务书路径>      # 任务书
#   bash <HARNESS_DIR>/scripts/run_charter.sh "一句话需求"      # 一句话需求（自动生成任务书）
#   bash <HARNESS_DIR>/scripts/run_charter.sh                   # 列出可用任务书
#   bash <HARNESS_DIR>/scripts/run_charter.sh <输入> --dry-run  # 只生成提示词不执行
#
# 前置：
#   - dsh 可用（headless profile 首次使用自动初始化）
#   - 当前目录为业务项目（含 .opencode/.harness-env 或 opencode_schedule/）
#   - 门禁密钥已生成（scripts/install_dsh.sh 或手动 conf/gate_secret）
# ============================================================
set -euo pipefail

HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKSPACE_DIR="$(cd "$HARNESS_DIR/.." && pwd)"
PROJECT_DIR="$(pwd)"
PROJECT_NAME="$(basename "$PROJECT_DIR")"
VENV_BIN="$WORKSPACE_DIR/venv-hetu/bin/python"
[ -x "$VENV_BIN" ] || VENV_BIN="python3"

# .harness-env 覆盖（业务项目已安装 harness 时）
ENV_FILE="$PROJECT_DIR/.opencode/.harness-env"
if [ -f "$ENV_FILE" ]; then
  while IFS= read -r line; do
    case "$line" in
      HARNESS_DIR=*) HARNESS_DIR="${line#HARNESS_DIR=}" ;;
      VENV_BIN=*) VENV_BIN="${line#VENV_BIN=}" ;;
    esac
  done < <(grep -E "^(HARNESS_DIR|VENV_BIN)=" "$ENV_FILE" | tr -d '"')
fi

DRY_RUN=0
INPUT=""
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    *) INPUT="$arg" ;;
  esac
done

echo "[charter] harness 宿主: $HARNESS_DIR"
echo "[charter] 业务项目:   $PROJECT_NAME ($PROJECT_DIR)"

# ---------- 前置校验 ----------
[ -f "$HARNESS_DIR/harness/workflow.yaml" ] || { echo "[charter] 错误: workflow.yaml 缺失" >&2; exit 1; }
[ -f "$HARNESS_DIR/constitution/constitution.md" ] || { echo "[charter] 错误: constitution.md 缺失" >&2; exit 1; }
[ -f "$HARNESS_DIR/conf/gate_secret" ] || { echo "[charter] 错误: 门禁密钥缺失（先运行 bash $HARNESS_DIR/scripts/install_dsh.sh 或手动生成 conf/gate_secret）" >&2; exit 1; }
if [ ! -d "$PROJECT_DIR/opencode_schedule" ] && [ ! -f "$ENV_FILE" ]; then
  echo "[charter] 警告: 当前目录不像业务项目（无 opencode_schedule/ 或 .harness-env）" >&2
fi

# ---------- 输入判别（与 /cc 一致：任务书 / 一句话需求 / 空=列出） ----------
INPUT_MODE="requirement"
TASK_BOOK=""
if [ -z "$INPUT" ]; then
  INPUT_MODE="list"
elif [ -f "$INPUT" ]; then
  INPUT_MODE="taskbook"
  TASK_BOOK="$(cd "$(dirname "$INPUT")" && pwd)/$(basename "$INPUT")"
elif [ -f "$PROJECT_DIR/$INPUT" ]; then
  INPUT_MODE="taskbook"
  TASK_BOOK="$PROJECT_DIR/$INPUT"
fi

if [ "$INPUT_MODE" = "list" ]; then
  echo ""
  echo "[charter] 可用任务书："
  if [ -d "$PROJECT_DIR/opencode_schedule" ]; then
    found=0
    while read -r f; do
      # 任务书特征：文件名与所在目录同名（YYYYMMDD任务N名称.md）
      dir="$(basename "$(dirname "$f")")"
      base="$(basename "$f" .md)"
      if [ "$dir" = "$base" ]; then
        echo "  $f"
        found=1
      fi
    done < <(find "$PROJECT_DIR/opencode_schedule" -name "*.md" -type f | sort)
    [ "$found" = "0" ] && echo "  （无任务书，可将任务书放入 opencode_schedule/<YYYYMMDD>/<任务目录>/）"
  else
    echo "  （当前目录无 opencode_schedule/）"
  fi
  echo ""
  echo "[charter] 用法: bash $0 <任务书路径 或 一句话需求>"
  exit 0
fi

# ---------- 构造编排提示词 ----------
WORKFLOW_TEXT="$(cat "$HARNESS_DIR/harness/workflow.yaml")"
if [ "$INPUT_MODE" = "taskbook" ]; then
  TASK_TEXT="$(cat "$TASK_BOOK")"
  INPUT_DESC="任务书（内容见下）"
else
  TASK_TEXT="$INPUT"
  INPUT_DESC="一句话需求：$INPUT（节点 -1 需按 templates/task_book.md 模板生成任务书）"
fi

PROMPT_FILE="${TMPDIR:-/tmp}/charter-prompt-$(date +%s).md"
cat > "$PROMPT_FILE" <<EOF
你是河图体系「宪章编程」研发流程的主编排代理（charter-orchestrator）。

## 输入
- $INPUT_DESC
- 业务项目：$PROJECT_NAME（工作目录 $PROJECT_DIR）

## 宪章（必须遵守，先阅读再执行）
- 顶层宪法：$HARNESS_DIR/constitution/constitution.md
- 子规范：$HARNESS_DIR/constitution/ 下的 coding / unit_test / log / project / task_split 等
- 安全底线：禁止获取 root 权限、禁止输出明文密钥、数据增删改必须先备份

## 流程定义（严格按序执行，前序未完成不得进入下一节点；来自 harness/workflow.yaml）
$WORKFLOW_TEXT

## 节点执行要求
- 节点 -1（仅一句话需求时）：按 $HARNESS_DIR/templates/task_book.md 模板生成任务书
- 节点 0：校验任务书/宪章/输出目录，解析任务目录名（YYYYMMDD任务N名称）
- 节点 1（charter-analyst）：读 $HARNESS_DIR/docs/资源地图.md 匹配资源，产出 实施计划.md
- 节点 2（charter-coder）：按宪章实现全部文件（Python 文件首行编码声明、类型标注、Google docstring）
- 节点 3（charter-tester）：编写 unit_test/test_*.py（正常/反例/边界），用 $VENV_BIN 运行，
  结果写入 unit_test/test/test_*_result.txt；**只写结果，不自行落闸**
- 节点 4（charter-reviewer）：只读评审，产出 评审报告.md；结论 APPROVE 才放行，
  REVISE 回节点 2 修复（最多 2 轮）
- 节点 5（charter-logger）：撰写 任务N研发日志.md
- 节点 6（charter-assetter）：产出沉淀为 $HARNESS_DIR/docs/hetu-$PROJECT_NAME/ 下文档，
  区分新增（创建并登记 $HARNESS_DIR/docs/资源地图.md）与更新（仅追加/修订章节）
- 节点 7（charter-notifier）：通过唯一出口发送钉钉：
  HARNESS_NOTIFY=1 $VENV_BIN -m harness.core.notify --run-id <任务目录名> --project $PROJECT_NAME --title "..." --text "..."

## 门禁约定（.gate.json v2 信任模型，写/验分离）
- 节点 3 全部测试通过后，由你（编排器）核对 result 文件并落闸：
  $VENV_BIN -m harness.core.cli seal-gate \\
    --task-dir <任务目录> --run-id <任务目录名> \\
    --results <全部 result 文件> --total <总数> --passed <通过数> \\
    --secret-file $HARNESS_DIR/conf/gate_secret
- 落闸前禁止写研发日志、禁止发通知（hard gate）；研发流程状态.md 为审计记录可随时写
- 数据销毁命令必须显式带 backup/备份

## 输出目录（任务目录，所有中间产物放这里）
$PROJECT_DIR/opencode_schedule/<YYYYMMDD>/<YYYYMMDD任务N名称>/
  ├── <YYYYMMDD任务N名称>.md    任务书（输入或节点-1 生成）
  ├── 实施计划.md                节点1
  ├── .gate.json                 节点3 落闸（seal-gate 生成）
  ├── 评审报告.md                节点4
  ├── 任务N研发日志.md           节点5
  └── 研发流程状态.md            每完成一个节点追加：时间 | 节点 | 状态 | 说明

## 状态固化
每完成一个节点，向任务目录 研发流程状态.md 追加记录；流程结束输出总结
（改动文件数、测试通过数、评审结论、遗留事项）。全程使用中文。

## 任务书/需求内容
---
$TASK_TEXT
---
EOF

echo "[charter] 输入模式: $INPUT_MODE"
echo "[charter] 提示词已生成: $PROMPT_FILE"

if [ "$DRY_RUN" = "1" ]; then
  echo ""
  echo "[charter] ====== --dry-run 模式，提示词内容预览 ======"
  head -60 "$PROMPT_FILE"
  echo "...（共 $(wc -l < "$PROMPT_FILE") 行）"
  echo "[charter] dry-run 结束，未启动 dsh。"
  exit 0
fi

# ---------- 启动 dsh headless（业务项目目录即 workspace） ----------
echo ""
echo "[charter] 启动宪章研发流程（dsh headless）..."
echo "[charter] 提示: 完整流程可能较长，dsh headless 会一次跑完并打印最终总结"
if command -v dsh >/dev/null 2>&1; then
  dsh --profile headless "$(cat "$PROMPT_FILE")"
else
  echo "[charter] 错误: dsh 不在 PATH（npm exec @deepseek-ai/dsh 安装后可重试）" >&2
  exit 1
fi
