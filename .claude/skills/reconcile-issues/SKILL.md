---
name: reconcile-issues
description: Review one phase's already-generated specification/implementation/vA.B-issues.md against the REAL current implementation (and the local setup, read-only) and correct any issue that has drifted - stale file names, changed signatures, evolved contracts, or work already done. Edits the file in place with a visible "Reconciled" mark. Corrects issues only; never implements code or changes the version.
---

# Skill: Reconcile Issues

`/generate-issues` grounds new issues in the real implementation (its Step 0.5). This skill does the same
for a **pre-generated** issues file. It reads `specification/implementation/vA.B-issues.md`, compares each
issue's assumptions with the **actual current code**, and **corrects the issues that drifted, in the file,
with a visible change-mark**, so the record shows the original issue was modified.

It only **corrects the issues**: it never implements code, never touches the version and never uses GitHub.
Run it right before `/execute-issues-file`.

## Usage

```
/reconcile-issues <vA.B | path-to-issues-file>
```

- `/reconcile-issues v3.2` → reconciles `specification/implementation/v3.2-issues.md`

## Instructions

### Step 0: Read the issues and the real implementation

1. **The issues file:** resolve the target to `specification/implementation/vA.B-issues.md` and read all of it:
   the summary table, the dependency tree and every `### GOLEM-###` section.
2. **The code:** read the **real current code** the issues touch: `golem/`, `agents/scribe/`, `levels/`
   (never `levels/hidden/`), `tests/`, `pyproject.toml` and `.env.example`. Note the actual module and
   function names, signatures, JSON fields, config keys, env var names and dependencies.
3. **Earlier records:** read the earlier phases' `specification/implementation/*-execution-report.md` and
   `*code-review*.md`, especially **"Fixes applied"**, **"Architecture impact"** and **"Design notes"** (the
   v3.1 lupa spike, the v4.1 swap prototype).
4. **The spec:** read [specification/ROADMAP.md](../../../specification/ROADMAP.md) §vA.B (the DoD),
   [specification/ARCHITECTURE.md](../../../specification/ARCHITECTURE.md) (contracts) and `CLAUDE.md`.
5. **Owner-run work:** check the local state read-only where possible (e.g. start the server and
   `curl -s http://127.0.0.1:8700/api/levels`). If an owner step may already be done (levels played, hidden
   levels written, a live session run), ask the owner.

### Step 1: Find the drift

Compare each issue's **assumptions** with reality:

- **Paths:** wrong or renamed files and modules (e.g. an issue naming `golem/interp/runner.py` when the code
  has `golem/interp/driver.py`).
- **Names and signatures** that changed: core functions, the `World` fields, the driver's API, the snapshot
  and report fields, route paths, CLI options, config keys (e.g. a budget read from `.env` vs
  `levels/budgets.toml`).
- **Contracts** that a landed fix moved past the spec: the sandbox allowlist, the stop rules, the JSON
  shapes, the journal schema, the tool rules.
- **Design decisions** made after the issues were written: the v3.1 spike's answers (the lupa version, the
  determinism fixes that were needed), the v4.1 prototype's findings about `memory` and swaps.
- **Work already done:** the deliverable was already shipped by an earlier fix or phase, or an owner step
  was already performed.
- **The code is ground truth** where it disagrees with the issue text or a stale spec.

### Step 2: Correct the issues in place, with a visible mark

For each issue that drifted, edit its section in `vA.B-issues.md`:

1. **Fix the details** (Description, What needs to be done, Acceptance criteria) so they match the real
   implementation. Keep the **GOLEM id and the intent**; correct only what drifted.
2. **Add a change-mark** as a blockquote directly under the issue heading:
   > **⟳ Reconciled (<today>):** originally referenced `golem/interp/runner.py` and a `STEP_BUDGET` env var;
   > corrected to the shipped `golem/interp/driver.py` reading budgets from `levels/budgets.toml`. Reason:
   > matches the real implementation.
3. **Moot issues** (already delivered) stay in the file with a clear mark:
   > **⟳ Reconciled (<today>):** already satisfied by `<commit / release / owner step>`; execution is
   > verification-only (add or confirm the test, or re-run the DoD check; no new production code).
4. Use today's date. Never rewrite silently; every change is stamped.

### Step 3: If nothing drifted

Leave issues that match reality untouched. If **no** issue needed a correction, add one note under the
file's intro and stop:
`> **⟳ Reconciled (<today>): no drift found — issues match the current implementation.**`

### Step 4: Record

Commit the corrected file (`docs: reconcile vA.B issues against the implementation`, with the running model's
`Co-Authored-By` trailer) and push if a remote exists. Report which issues were corrected and why, which
were marked moot, and which were untouched.

## Important Rules

- **Correct issues only.** Never implement code, change the version or use GitHub. That is
  `/execute-issues-file` and `/release-version`.
- **The real code is ground truth** where it disagrees with the issue or a stale spec.
- **Every change is marked.** Keep the GOLEM id and intent, and add a dated `⟳ Reconciled` blockquote.
- **No churn.** Don't touch issues that already match reality.
- **Never read or quote `levels/hidden/`.**
- **Ask on genuine ambiguity.** If it's unclear whether the issue or the code is right, raise it with the
  user rather than guessing.
