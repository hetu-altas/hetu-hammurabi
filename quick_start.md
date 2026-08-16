# Quickstart Guide

> Get your first "Charter Programming" task running in 5 minutes. Full docs:
> [docs/harness/](docs/harness/README.md) (Chinese) and
> [docs/hetu-hammurabi/dsh-client-plugin.md](docs/hetu-hammurabi/dsh-client-plugin.md) (Chinese).

## 0. Prerequisites

| Dependency | Requirement |
|------------|-------------|
| DSH | `npx @deepseek-ai/dsh web` (DeepSeek Harness — the primary execution carrier) |
| opencode | ≥ 1.16 (compatibility path; the legacy flow still works) |
| Model | Any configured provider (domestic LLMs such as DeepSeek / Qwen / GLM / Kimi recommended) |
| Python | Dashboard data service needs `venv-hetu` (fastapi/uvicorn) |
| Directory layout | `hetu-hammurabi` and business projects (`hetu-xxx`) must be **siblings under the same parent directory** |

## 1. Install (two steps)

```bash
# ① Python data service + constitution + core (repo is the service; git clone is enough)

# ② DSH all-in-one plugin (/cc command + hard gate + dashboard panel + status dock + dashboard auto-launch)
cd hetu-hammurabi
npx @deepseek-ai/dsh plugin --profile web add ./plugins/constitution-coding
```

> opencode compatibility path (optional): `bash scripts/install_harness.sh` installs the legacy
> harness; `/cc` works inside business projects (renamed; constitution coding).

## 2. Start DSH (the dashboard follows automatically)

```bash
# Launch from a business project or the workspace root
npx @deepseek-ai/dsh web --port 3090
```

- ~2s after DSH starts, the dashboard data service (8790) is **auto-launched** by the plugin hook
  (no manual start needed)
- If port 3080 is taken by a Windows app (e.g. attu), change the port with `--port`
  (see the port-conflict section in dsh-client-plugin.md)

## 3. Start your first task (pick one input mode)

### Mode A: /cc command in the GUI (recommended)

Type directly in the DSH web GUI input box:

```
/cc implement a generic utility: sort a list by date field, deduplicate, and write to a file
```

Or point to a task book:

```
/cc opencode_schedule/20260801/20260801任务1xxx/20260801任务1xxx.md
```

The system automatically runs: task book generation (on demand) → analysis → coding →
unit tests (hard gate) → code review → dev log → asset accumulation → DingTalk notification.
During execution the **right-side status dock** shows node -1..7 progress in real time, and the
hard gate (destructive commands / notify bypass / log writes before gate) is enforced by the machine.

### Mode B: task book

1. Copy and fill in `templates/task_book.md`
2. Put it into the business project task dir: `opencode_schedule/<YYYYMMDD>/<YYYYMMDD>任务N<名称>/`
3. Run `/cc <task book path>` as in Mode A

### Mode C: CLI (headless)

```bash
bash <HARNESS_DIR>/scripts/run_charter.sh "<task book path or one-line requirement>"   # --dry-run previews the prompt
```

## 4. View the artifacts

All intermediate artifacts are archived in the task directory:

```
opencode_schedule/<YYYYMMDD>/<YYYYMMDD>任务N<名称>/
├── task book        # input (or auto-generated)
├── 实施计划.md      # analysis node
├── .gate.json       # hard gate state (v2 signed, after tests pass)
├── 评审报告.md      # review node
├── 任务N研发日志.md # dev log node
└── 研发流程状态.md  # full pipeline node status
```

Dashboard ("📊 宪章看板" in the GUI sidebar, or standalone at `http://127.0.0.1:8790/`):
overview (tasks / node completions / success rate / gate block rate), **engine benchmark
(DSH vs opencode)**, per-node stats, gate block records, task list & detail — statistics cover
all hetu-* projects.

<<<<<<< Updated upstream
| Issue | Fix |
|-------|-----|
| Config changes have no effect | **Quit and restart opencode** (config is loaded at startup) |
| "Test gate not passed" error | Expected behavior: the gate opens automatically once the tester node runs tests and writes `.gate.json`; writing dev logs or notifying before that is hard-blocked by design |
| `/cc` unavailable after switching machines | Re-run step 1 (symlinks use absolute paths) |
| "Path not found" | Make sure `hetu-hammurabi` and the business project are siblings under the same parent directory |
| Paths don't match my environment | The repo uses relative-path conventions (`../venv-hetu/`, `../logs/`, `../hetu-aether/`); adapt them to your layout — see the "Open-Source Adaptation" section in the README |
| Can I skip a node? | No — the pipeline is fixed by the charter; adjust task granularity instead of nodes |
=======
## 5. FAQ
>>>>>>> Stashed changes

| Problem | Solution |
|---------|----------|
| `/cc` command missing | Confirm `npx @deepseek-ai/dsh plugin add` was run and dsh web was restarted (config loads at startup) |
| Command must be lowercase | `/CC` (uppercase) breaks dsh web startup (DSH command-name spec) |
| Dashboard not auto-started | Check `logs/hetu-altas/dashboard.log`; fallback: `bash scripts/start_dashboard.sh` |
| Port conflict (attu etc.) | `npx @deepseek-ai/dsh web --port <new-port>` |
| Task attributed to wrong project | /cc attributes by task content; be careful when launching from the workspace root |
| Skip a node | Not supported — the pipeline is constitution-fixed; adjust task granularity instead |

<<<<<<< Updated upstream
- **Full system docs** (Chinese): [docs/harness/](docs/harness/README.md) (overview / workflow / agents & skills / gates / assets / extending)
- **Charters**: `constitution/` (top-level 13 chapters + 7 sub-specs: coding / unit-test / logging / project / TDengine / Milvus / task splitting)
- **Core philosophy**: [Constitution Coding Manifest](manifesto.md)
- **Task granularity**: assess before writing a task book per `constitution/task_split/task_split.md`; split oversized tasks first
=======
## 6. Next steps

- **DSH plugin development guide**: [docs/hetu-hammurabi/dsh-client-plugin.md](docs/hetu-hammurabi/dsh-client-plugin.md)
- **DSH official docs offline mirror**: [docs/dsh-docs/](docs/dsh-docs/README.md)
- **Constitution**: `constitution/` (13 top-level chapters + 7 sub-specs)
- **Engine benchmark**: [docs/hetu-hammurabi/engine-benchmark.md](docs/hetu-hammurabi/engine-benchmark.md)
- **Manifesto**: [宪章编程宣言.md](宪章编程宣言.md)
>>>>>>> Stashed changes

---

MIT licensed, free for commercial use. Contact: hetu_altas@163.com
