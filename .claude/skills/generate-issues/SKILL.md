---
name: generate-issues
description: Decompose one ROADMAP phase (vA.B) into a dependency-ordered issues file at specification/implementation/vA.B-issues.md, grounded in the real current code. The output feeds /upload-issues (GitHub flow) or /execute-issues-file (offline flow).
---

# Skill: Generate Phase Issues

Decompose one ROADMAP **phase** (`vA.B`) into a small, dependency-ordered **issues file** at
`specification/implementation/vA.B-issues.md`. The file is the input to `/upload-issues` → `/execute-issues`
(GitHub flow), or straight to `/execute-issues-file` (offline flow).

## Usage

```
/generate-issues <phase>
```

- `/generate-issues v1.1` or `/generate-issues 1.1`: ROADMAP phase **v1.1** (project skeleton and the level
  format) → `specification/implementation/v1.1-issues.md`

One file per phase. Issue ids (`GOLEM-###`) are **globally sequential** across phase files **and across
regeneration runs**. Never reset them.

## Instructions

### Step 0: Read inputs

1. Normalize the argument to `vA.B` and check it exists as a `### vA.B` heading in
   [specification/ROADMAP.md](../../../specification/ROADMAP.md). For anything else, name it and ask. A phase
   marked **outline** (v8.x) has no tasks yet: say so and ask the owner to fix its tasks in ROADMAP.md first.
2. Read ROADMAP.md §`vA.B`: the phase's **Goal**, description, **Tasks**, **DoD** (including which items are
   **Manual (owner)**) and **Tests**, plus the version heading (`## vA`) it sits under.
3. Read [specification/ARCHITECTURE.md](../../../specification/ARCHITECTURE.md) for the mechanisms and
   **Contracts** the phase touches, and [specification/VISION.md](../../../specification/VISION.md) for the
   principles and **non-goals**. The scope limit is the phase itself plus the non-goals: never pull a later
   phase's work in early, and never add what no phase asks for.
4. Read `CLAUDE.md` for the acceptance gates and the rules that are easy to break.
   (`specification/concept.uk.md` is frozen; never read it as a source of truth.)
5. **Find the next free `GOLEM-###` id. Never restart the numbering.** Check both sources and continue
   from the higher:

   ```bash
   # (a) GitHub: survives a wiped working tree (skip if the repo has no remote)
   gh issue list --state all --limit 1000 --json title \
     --jq '.[].title | capture("GOLEM-(?<n>[0-9]+)").n' 2>/dev/null | sort -n | tail -1

   # (b) local issues files: covers ids drafted but not uploaded
   grep -rhoE 'GOLEM-[0-9]+' --include='*-issues.md' specification/implementation/ 2>/dev/null \
     | grep -oE '[0-9]+' | sed 's/^0*//' | sort -n | tail -1
   ```

   Pass the directory with `--include`, not a `*-issues.md` glob. Under zsh an unmatched glob aborts the
   command before `2>/dev/null` applies, and `specification/implementation/` may not exist yet.

   The next id is `max(a, b) + 1`, zero-padded to three digits. Start at `GOLEM-001` only if both sources
   come back empty. Say in the report which sources were checked: with no remote, or with `gh`
   unauthenticated, (b) alone governs.
6. If `specification/implementation/vA.B-issues.md` already exists, ask whether to overwrite or append.

### Step 0.5: Reconcile with the real implementation

Ground the phase in what was actually built and fixed, not only in what the specification describes. Review
fixes and hardening in earlier phases may have moved the code away from the docs.

1. Read the **real current code** this phase builds on: `golem/` (`core/`, `interp/`, `server/`, `screen/`,
   `journal/`, `orchestrator/`, `cli.py`, `local.py`), `agents/scribe/`, `levels/` (training sets and
   `budgets.toml`, never `levels/hidden/`), `tests/`, `pyproject.toml` and `.env.example`. Note the actual
   module and function names, signatures, JSON fields, config keys and env var names.
2. Read the earlier phases' `specification/implementation/*-execution-report.md` and `*code-review*.md`,
   especially their **"Fixes applied"** and **"Architecture impact"** notes. From v2.4 on, read the
   v2.3 lupa spike note; from v3.1 on, the v2.5 design note.
3. Where ARCHITECTURE.md or ROADMAP.md is stale relative to a landed fix, the **code is ground truth** for
   this phase's issues. Note the drift, and put the ARCHITECTURE.md correction into the issue that touches
   that contract.
4. For owner-run tasks (playing on the screen, writing hidden levels, live Scribe sessions), check what can be
   checked read-only (e.g. whether the server starts and `curl -s http://127.0.0.1:8700/api/levels` answers),
   and ask the owner about the rest. A task that is already done becomes a verification-only issue, not new
   work.

### Step 1: Decompose the phase

Turn the phase's tasks into a small set of issues, typically **2–5**. A small phase such as v2.5 may be one
or two issues. Don't pad. Each issue is a coherent, independently verifiable slice:

- **Size** by complexity:
  - **S:** one function or file.
  - **M:** a feature across a few files.
  - **L:** a new component or a contract change.
- **Area**, one of:
  - `core`: `golem/core/` (the rules; standard library only).
  - `interp`: `golem/interp/` (the sandbox, the driver, stops, swaps, snapshots).
  - `server`: `golem/server/` (the HTTP API and the WebSocket).
  - `screen`: `golem/screen/` (HTML, canvas, plain JavaScript).
  - `cli`: `golem/cli.py`, `golem/local.py` and the owner tools (`golem-levels`, `golem-metrics`).
  - `journal`: `golem/journal/` (the validator, the journal, the traces).
  - `agent`: `golem/orchestrator/` and `agents/scribe/`.
  - `levels`: `levels/` (training levels, budgets, `README.md`) and `tests/fixtures/solutions/`.
  - `config`: `pyproject.toml`, `uv.lock`, `.env.example`, `.gitignore`, `.github/workflows/`.
  - `tests`.
  - `docs`: the `specification/` files, README.md, CLAUDE.md.
  - `ops`: steps the owner performs: playing on the screen, writing hidden levels, live Scribe sessions.
- **Order by dependency.** The first issue is usually the gate that everything builds on. In v1.1 that is
  the project skeleton with the gates and CI; in v2.3 it is the lupa spike; in v5.2 it is the journal schema.
- **Tests in every code issue.** Keep decision logic pure so it can be unit-tested with plain data: the
  rules, the level parser, the stop decisions, the `memory` conversion, report assembly, version
  deduplication, metrics. No test touches the network or a model: the server and the CLI are tested
  in-process, lupa runs for real, and the agent is a fake script.
- **Determinism in every interpreter issue.** An issue that changes what a program can observe or how it is
  counted includes a run-twice test with byte-identical traces.
- **Manual DoD checks** from ROADMAP.md go into the acceptance criteria as **Manual (owner):** items. The
  executor cannot pass them on its own.
- **Contract changes:** a change to anything in ARCHITECTURE.md **§Contracts** carries the ARCHITECTURE.md
  update (and `concept.en.md` where it states the same thing) and the test that pins it, in the **same**
  issue.
- **Owner-run (`ops`) issues:**
  - List the exact steps from ROADMAP.md.
  - Mark which checks Claude can run itself (starting the server locally, `golem` or `curl` against
    `127.0.0.1`).
  - Name any repo artifact the issue produces (e.g. `levels/hidden/README.md`). Hidden levels themselves are
    never a repo artifact.
- **Stay within the phase.** No stops in v2.3, no designed screen in v2.2, no journal in v5.1, no live model before v6.2, nothing from
  VISION.md's non-goals.

### Step 2: Write the issues file

Write `specification/implementation/vA.B-issues.md` in English. Use **exactly** this format:

````markdown
# vA.B — Issues

Issues for phase **vA.B — {title}** (version **vA — {version title}**), derived from the Tasks and DoD in
[ROADMAP.md](../ROADMAP.md) §vA.B and the contracts in [ARCHITECTURE.md](../ARCHITECTURE.md). This file
covers one phase; ids continue from the previous phase (GOLEM-{prev} → **GOLEM-{first}…{last}**).

{1–3 sentences: what the phase delivers, what it builds on, what it leaves for later phases.}

## Issues Summary Table

| # | ID | Title | Size | Area | Phase | Dependencies |
|---|----|-------|------|------|-------|--------------|
| 1 | GOLEM-{first} | {title} | M | core | vA.B | -- |
| 2 | GOLEM-{…} | {title} | S | tests | vA.B | GOLEM-{first} |

**Size legend:** S = one function or file · M = a feature across a few files · L = a new component or a contract change

---

## Dependency Tree

```
GOLEM-{first} ({gate})
  |
  +-- GOLEM-{…} (…)
  |
  +-- GOLEM-{…} (…)  => {phase DoD}
```

**Parallelization hints:** {what must go first; what is independent}.

---

## vA.B — {title}

### GOLEM-{id} — {Title}

**Description:**
{1–3 sentences; name the files it touches.}

**What needs to be done:**
- {bullet}

**Dependencies:** {GOLEM ids, or None}

**Expected result:**
{one sentence}

**Acceptance criteria:**
- [ ] {functional criterion}
- [ ] **Tests:** {the tests added: unit with plain data, real lupa, in-process server/CLI, fake agent}
- [ ] **Determinism:** {the run-twice check} — *(only for interpreter, driver, stop or journal changes)*
- [ ] **Contract:** {contract + the test that pins it + the ARCHITECTURE.md update} — *(only if a contract changes)*
- [ ] **Gates:** {lint / tests}
- [ ] **Manual (owner):** {DoD check from ROADMAP.md §vA.B} — *(only where the DoD needs a person or a live model)*

---

{repeat the `### GOLEM-{id} …` block per issue}

## vA.B scope notes

**Critical path:** GOLEM-{…} → … → GOLEM-{…}.
**Phase DoD (ROADMAP.md §vA.B):** {restate the DoD}.
**Contracts touched:** {contracts + their tests, or "none"}.
**Owner steps:** {what the owner must do: play, write hidden levels, run a live session — or "none"}.
**Not in this phase:** {nearby work that belongs to a later phase or to no phase}.
**Generated later:** `vA.B-github-report.md` (on upload), `vA.B-execution-report.md` (on execution).
````

### Step 3: Report

Show the user the file path, the issue count, the `GOLEM-###` range, the critical path, and which id
sources were checked. Suggest the next step:

```
/upload-issues @specification/implementation/vA.B-issues.md   # GitHub flow
/execute-issues-file vA.B                                     # offline flow
```

Do **not** create GitHub issues or commit here. This skill only writes the local file, so the user can
read and edit it first.

## Important Rules

- **One file per phase**, at `specification/implementation/vA.B-issues.md`.
- **Ids are globally sequential** (`GOLEM-###`) across phase files and regeneration runs. Resolve the next id
  as `max(GitHub, local issues files) + 1`.
- **Tests in every code issue**, with no network and no model. Manual DoD checks are labeled
  **Manual (owner):**.
- **Contract change = ARCHITECTURE.md + the pinning test**, all in the same issue.
- **Stay within the phase** and outside VISION.md's non-goals. Simplicity beats completeness.
- **Honor the DoD.** Together, the issues must satisfy the phase DoD in ROADMAP.md §vA.B, including the
  concept's "done when" criterion.
- **Never read or quote `levels/hidden/`.** Issues refer to hidden levels by role, and tests use
  `tests/fixtures/hidden/`.
- **Ask on ambiguity.** If a task is under-specified, ask before inventing scope.
- **Don't touch GitHub.** `/upload-issues` does that.
