# Quickstart Guide

> Get your first "Charter Programming" task running in 5 minutes. Full documentation: [docs/harness/](docs/harness/README.md) (Chinese).

## 0. Prerequisites

| Dependency | Requirement |
|------------|-------------|
| opencode | ≥ 1.16 (currently the only adapted harness; more domestic harnesses will follow) |
| Model | Any configured provider (domestic LLMs such as DeepSeek / Qwen / GLM / Kimi recommended) |
| Python | `unittest` + project venv if running unit tests |
| Directory layout | `hetu-hammurabi` and business projects (`hetu-xxx`) must be **siblings under the same parent directory** |

## 1. Install the harness (30 seconds)

```bash
bash hetu-hammurabi/scripts/install_harness.sh
```

Verify:

```bash
opencode agent list        # you should see charter-orchestrator + 8 node subagents
opencode debug skill       # you should see charter-* skills
opencode debug config      # plugin list should include charter-gate.ts
```

## 2. Start your first task (pick one input mode)

### Mode A: one-line requirement (recommended for the first run)

Launch opencode in the business project, then:

```
/dev implement a generic utility: sort a list by date field, deduplicate, and write to a file
```

The system automatically runs: task book generation → analysis → coding → unit tests (hard gate) → code review → dev log → asset accumulation → DingTalk notification.

### Mode B: task book

1. Copy and fill in the template `hetu-hammurabi/templates/task_book.md`
2. Place it in the business project's task directory: `opencode_schedule/<YYYYMMDD>/<YYYYMMDD>任务N<名称>/`
3. Run:

```
/dev opencode_schedule/20260801/20260801任务1xxx/20260801任务1xxx.md
```

## 3. Where the artifacts live

Everything is archived in the task directory:

```
opencode_schedule/<YYYYMMDD>/<YYYYMMDD>任务N<名称>/
├── task book         # input (or auto-generated)
├── 实施计划.md        # analysis node
├── .gate.json         # hard-gate state (written after tests pass)
├── 评审报告.md        # review node
├── 任务N研发日志.md   # dev log
└── 研发流程状态.md    # per-node status of the whole flow
```

## 4. FAQ

| Issue | Fix |
|-------|-----|
| Config changes have no effect | **Quit and restart opencode** (config is loaded at startup) |
| "Test gate not passed" error | Expected behavior: the gate opens automatically once the tester node runs tests and writes `.gate.json`; writing dev logs or notifying before that is hard-blocked by design |
| `/dev` unavailable after switching machines | Re-run step 1 (symlinks use absolute paths) |
| "Path not found" | Make sure `hetu-hammurabi` and the business project are siblings under the same parent directory |
| Can I skip a node? | No — the pipeline is fixed by the charter; adjust task granularity instead of nodes |

## 5. Next steps

- **Full system docs** (Chinese): [docs/harness/](docs/harness/README.md) (overview / workflow / agents & skills / gates / assets / extending)
- **Charters**: `constitution/` (top-level 13 chapters + 7 sub-specs: coding / unit-test / logging / project / TDengine / Milvus / task splitting)
- **Core philosophy**: [Charter Programming Manifesto](宪章编程宣言.md) (Chinese)
- **Task granularity**: assess before writing a task book per `constitution/task_split/task_split.md`; split oversized tasks first

---

Open-sourced under the MIT License, no restrictions on commercial use. Questions or feedback: hetu_altas@163.com
