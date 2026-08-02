# hetu-hammurabi

> *"When the River Chart emerged, the Sages took its pattern as law."*
>
> In ancient China, a dragon-horse bearing the **River Chart** (河图) rose from the Yellow River before the legendary sage Fuxi — the primal map of cosmic order, the ultimate abstraction of all patterns. It is not law itself, but the meta-order from which law is written.
>
> On the banks of the Euphrates, **Hammurabi** carved the scattered customs and judgments of his people into a basalt stele, issuing the first codified law in human history — the Code of Hammurabi. Law no longer lived in the memory of kings; it stood in stone, visible to all, binding to all. He legislated, and he enforced: within the law, order; beyond the law, no passage.
>
> When the Eastern map of order meets the Western lawgiver, there is **hetu-hammurabi** — the harness module of Charter Programming.
>
> It casts scattered charters into a codex, drawing boundaries for every action of the model; it engraves the R&D flow into a pipeline of nodes, giving each step its rule; it enforces with hard gates — no luck, no whim. It writes no business code, yet every line of business code moves within its statutes; it produces no data, yet every R&D effort settles into codified assets.
>
> No predictions, no price calls — only the most faithful lawgiver for the model.

---

**hetu-hammurabi** is the harness module of the hetu series "Charter Programming" (宪章编程) paradigm. Built on opencode's Commands / Agents / Skills / Plugins, it turns the R&D workflow into an executable pipeline: feed it a **task book path or a one-line requirement**, and it automatically runs task-book generation (optional) → analysis → coding → unit tests (hard gate) → code review → dev log → asset accumulation → DingTalk notification.

## Charter Programming · Core Tenets

> **Humans legislate; AI executes.**
> Our role is not "telling AI what to do" but "defining what AI cannot do." The legislator sets the boundaries; the executor acts within them.
>
> **The Constitution outranks the conversation.**
> The effect of a conversation dissolves when the context window closes; the effect of a constitution persists as long as the project lives. What is chatted is "a feeling"; what is written into the constitution is "a rule."
>
> **Constraints are assets, not burdens.**
> One amendment to the constitution triggers automatic compliance across every AI output. Constraints are not shackles on creativity — they are the mold that scales it.
>
> **Legislate first, code later.**
> Constrain with the charter, not with prompt patches — fix a class of bugs, not one bug; eliminate a class of violations, not one violation.

> — Excerpts from the [Charter Programming Manifesto](宪章编程宣言.md) (Chinese)

> The vibe programmer asks: "AI, what can you do?"
> The charter programmer says: "AI, within my rules, this is all you may do."

---

## Ecosystem Positioning

> **Open-source harness + domestic LLMs**: both the administrative arm and the executing officials are replaceable; only the constitution endures.

- **Harness**: built on an open-source agent harness, currently adapted to [opencode](https://opencode.ai) (≥ 1.16); **more domestic harnesses will be supported** — migrating the config layer (`.opencode/`) is all it takes
- **Models**: compatible with domestic LLMs (DeepSeek, Qwen, GLM, Kimi, ...) via the harness's provider configuration — no charter changes needed
- **Decoupling**: the charters (`constitution/`) are fully decoupled from the model and the harness — switching harness migrates only the orchestration layer; switching models only changes provider config; **the charter stays untouched**
- Echoing Tenet IV of the [Manifesto](宪章编程宣言.md): "Tools may change, models may change; the constitution never dies, and the system lives forever."

---

## Open-Source Adaptation (read before deploying)

All paths in this repository follow **relative-path conventions** — adjust them to your own layout when deploying:

| Item to adapt | Current convention | Notes |
|---------------|-------------------|-------|
| Shared venv | `../venv-hetu/bin/python` | Convention: the shared venv lives in the same parent dir as the projects; replace references in `.opencode/` and `constitution/` for other layouts |
| Log root | `../logs/hetu-altas/` | Convention: log root is a sibling of the projects (see `constitution/log/log.md`) |
| Shared-utils project | `../hetu-aether/` (example name) | Coding/testing/notification nodes reference the shared-utils project; update `.opencode/` references if renamed |
| Business project names | `hetu-mercury` / `hetu-thoth` (example names) | Replace with your own projects in the resource map (`docs/资源地图.md`) and charters |

> Note: `hetu-aether/mercury/thoth` are the example naming of the hetu ecosystem — keep them or replace with your own naming.

## Directory Layout

```
.
├── .opencode/
│   ├── commands/
│   │   └── dev.md                     # /dev entry (task book path or one-line requirement)
│   ├── agents/
│   │   ├── charter-orchestrator.md    # Orchestrator (primary, nodes -1~7)
│   │   ├── charter-taskwriter.md      # Node -1: task book generation (one-line requirement)
│   │   ├── charter-analyst.md         # Node 1: analysis → implementation plan
│   │   ├── charter-coder.md           # Node 2: coding
│   │   ├── charter-tester.md          # Node 3: unit tests (hard gate)
│   │   ├── charter-reviewer.md        # Node 4: code review (APPROVE/REVISE)
│   │   ├── charter-logger.md          # Node 5: dev log
│   │   ├── charter-assetter.md        # Node 6: asset accumulation (docs new/update)
│   │   └── charter-notifier.md        # Node 7: DingTalk notification
│   ├── skills/
│   │   ├── charter-taskbook/SKILL.md  # Requirement → task book
│   │   ├── charter-analysis/SKILL.md  # Resource matching (API docs/DDL/reference code)
│   │   ├── charter-coding/SKILL.md    # Coding charter (references coding.md)
│   │   ├── charter-testing/SKILL.md   # Testing charter (references unit_test.md)
│   │   ├── charter-logging/SKILL.md   # Dev log spec
│   │   └── charter-assets/SKILL.md    # Asset accumulation (new vs update)
│   └── plugin/
│       └── charter-gate.ts            # Hard-constraint plugin (gate/data safety/secrets/assets)
├── constitution/                      # Universal charters (single source of truth)
│   ├── constitution.md                # Top-level constitution (13 chapters)
│   └── coding/ unit_test/ log/ project/ tdengine/ milvus/ task_split/   # Sub-specs
├── docs/hetu-aether|mercury|thoth/    # Aggregated project docs
├── scripts/
│   └── install_harness.sh             # Symlink the harness into sibling hetu-* projects
├── templates/
│   └── task_book.md                   # Task book template
├── 宪章编程宣言.md                    # Charter Programming Manifesto (Chinese)
└── 快速上手指南.md                    # Quickstart (Chinese) — see quick_start.md
```

## Quick Start

Full documentation: [docs/harness/](docs/harness/README.md) (overview / workflow / agents & skills / gates / assets / extending). New to the project? Read the [Quickstart Guide](quick_start.md) first.

1. Install the harness into sibling business projects:

```bash
bash scripts/install_harness.sh
```

2. Prepare input (pick one):
   - Write a task book from `templates/task_book.md`, place it under `opencode_schedule/YYYYMMDD/<YYYYMMDD>任务N<名称>/` in the business project (e.g. `hetu-thoth`)
   - Or use a one-line requirement — the system generates the task book (node -1)

3. Before writing a large task book, assess granularity per `constitution/task_split/task_split.md`: tasks exceeding the limits must be split into sequenced task books.

4. Launch opencode in the business project and run:

```
/dev <task book path 或 one-line requirement>
```

The orchestrator executes the nodes and records each node's status in the task directory's `研发流程状态.md`.

## Pipeline Nodes

| Node | Agent | Output | Gate |
|------|-------|--------|------|
| -1 Task book generation | charter-taskwriter | `任务N<名称>.md` | Only for one-line requirements |
| 0 Validation | charter-orchestrator | task book/charter/output dir check | - |
| 1 Analysis | charter-analyst | `实施计划.md` | - |
| 2 Coding | charter-coder | source/scripts/deps | - |
| 3 Unit tests | charter-tester | `unit_test/test_*_result.txt` + `.gate.json` | Hard gate: all pass + `.gate.json`, back to node 2, max 3 rounds |
| 4 Code review | charter-reviewer | `评审报告.md` | APPROVE required; REVISE back to node 2, max 2 rounds |
| 5 Dev log | charter-logger | `任务N研发日志.md` | Only after nodes 3 & 4 (hard-blocked by charter-gate) |
| 6 Asset accumulation | charter-assetter | `docs/hetu-<project>/**` new/update | Only after nodes 3 & 4 |
| 7 Notification | charter-notifier | DingTalk notification | Only after nodes 3 & 4 (hard-blocked by charter-gate) |

## Output Layout (Task Directory)

Each task's artifacts live in its own directory, so multiple tasks per day never mix:

```
opencode_schedule/<YYYYMMDD>/
└── <YYYYMMDD>任务N<名称>/          # task dir (task book name without .md)
    ├── <YYYYMMDD>任务N<名称>.md    # task book (input, or generated at node -1)
    ├── 实施计划.md                  # node 1
    ├── .gate.json                   # node 3 (hard-gate state)
    ├── 评审报告.md                  # node 4
    ├── 任务N研发日志.md             # node 5
    └── 研发流程状态.md              # whole flow (maintained by orchestrator)
```

## Hard Constraints (charter-gate plugin)

`.opencode/plugin/charter-gate.ts` enforces 4 hard constraints:

1. **Test gate**: while `.gate.json` is missing or `test_passed=false`, writes to dev-log/status files (via `write`/`edit`/`apply_patch` or bash redirection) and DingTalk notification commands are blocked; **reads are never blocked**
2. **Data safety**: `rm -rf` / `DROP` / `DELETE FROM` / `TRUNCATE` / `drop_collection` require an explicit `backup`/`备份` marker
3. **Secret redaction**: plaintext credentials in messages (sk-, Bearer, token/password, ...) are auto-redacted with a warning
4. **Asset registration**: writes under `docs/hetu-*/` not registered in `docs/资源地图.md` trigger a warning

## Maintenance

- Charter changes: edit only `constitution/` sources — Skills reference them by path, no Skill changes needed.
- Adding a pipeline node: create an agent under `.opencode/agents/` and update the flow definition in `charter-orchestrator.md`.
- Changing hard constraints: edit `.opencode/plugin/charter-gate.ts` (a `throw` in a hook hard-blocks the tool call).
- Config changes (agents/skills/commands/plugin) require **quitting and restarting opencode** to take effect.

## License

This project is open-sourced under the **MIT License** ([LICENSE](LICENSE)), with **no restrictions on commercial use**:

- Use, copy, modify, merge, publish, distribute, sublicense, and sell — freely
- Commercial and closed-source use allowed; no payment or attribution beyond retaining the copyright notice
- The only obligation: keep the copyright and permission notice (distribute the LICENSE file)
- The software is provided "as is", without warranty of any kind (see LICENSE)

Copyright (c) 2026 hetu-altas

Contact: **hetu_altas@163.com**
