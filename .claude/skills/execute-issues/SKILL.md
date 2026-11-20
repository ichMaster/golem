---
name: execute-issues
description: Execute one phase's GitHub issues (label vA.B::phase) sequentially in dependency order - implement, run the acceptance gates, get owner confirmation for manual DoD checks, commit, push, close - then write vA.B-execution-report.md.
---

# Skill: Execute GitHub Issues

Execute one phase's GitHub issues sequentially. For each one: implement, validate, commit, push and close.
Then write an execution report.

## Usage

```
/execute-issues <label|phase> [--issue GOLEM-###] [--dry-run]
```

The label is the phase label exactly as it appears on GitHub (`v1.1::phase`). A bare `v1.1` also works.

- `/execute-issues v1.1::phase`: execute every open issue of phase v1.1.
- `/execute-issues v1.1::phase --issue GOLEM-003`: one issue (its dependencies must already be closed).
- `/execute-issues v1.1::phase --dry-run`: show the execution plan without changing anything.

## Instructions

### Step 0: Verify prerequisites

1. **Branch:** note the current branch.
2. **Clean tree:** run `git status`. If the only uncommitted files are this phase's issues file or GitHub
   report under `specification/implementation/`, commit them first (`docs: add vA.B issues`). Any other
   uncommitted change: stop and ask.
3. **GitHub:** `gh` is authenticated and the repo has a remote.
4. **Fetch the open issues:** `gh issue list --label "vA.B::phase" --state open --limit 100`.
5. **Read the phase files:** the issues file `specification/implementation/vA.B-issues.md`, and
   `vA.B-github-report.md` for the `GOLEM-###` → `#number` mapping.
6. **Read the spec:** [specification/ROADMAP.md](../../../specification/ROADMAP.md) §vA.B (Goal, Tasks,
   DoD, Tests), [specification/ARCHITECTURE.md](../../../specification/ARCHITECTURE.md) (mechanisms and
   contracts) and [specification/VISION.md](../../../specification/VISION.md) (non-goals), plus `CLAUDE.md`:
   the gates and the rules that are easy to break.
7. **Green baseline:** run the automated gates that apply (see `CLAUDE.md` **Acceptance gates**), so a
   later failure can be attributed. Never start on a red suite.

### Step 1: Build the execution queue

- **Order:** parse `GOLEM-###` ids from the issue titles (`GOLEM-###: {title}`) and order them by the issues
  file's Dependency Tree. Issues with no unmet dependency go first.
- **Resuming:** closed issues are already excluded (`--state open`), so a re-run resumes where the last one
  stopped.
- **`--issue`:** execute only that issue, after checking that its dependencies are closed.

Show the plan and ask for confirmation. With `--dry-run`, stop here.

### Step 2: Execute each issue (loop)

#### 2a. Announce

Print `--- Starting GOLEM-###: {title} ---`.

#### 2b. Read the issue

Read its detailed section in the issues file: what needs to be done and the acceptance criteria.

#### 2c. Implement

Follow `CLAUDE.md` and ARCHITECTURE.md. Route by component:

- **`golem/core/`** (v1): the only place the rules exist. Standard library only, an immutable `World`, pure
  functions over plain data, and every collection sorted before it reaches JSON. See ARCHITECTURE.md §World
  and rules.
- **`golem/interp/`** (v2.3–v2.5, v4): lupa is used here and nowhere else. The v2 prototype's code lives in
  these final modules, and v4 extends it.
  - The sandbox is an allowlist on a fresh environment table, created with `register_eval=False` and
    `register_builtins=False`. No Python object is passed into Lua, and programs are loaded as text only.
  - Until v4.1, the environment holds only names whose behaviour is already deterministic. From v4.1, the
    deterministic `pairs`, the merge-sort `table.sort`, the address-free `tostring` and `string.format`, and
    the seeded `math.random` stay in place.
  - The driver yields per robot command. The budget error is a sentinel compared by identity, and the hook
    is reinstalled after every swap.
  - `memory` belongs to the run.

  See ARCHITECTURE.md §Robot language, §Execution and §Stops.
- **`golem/server/`** (v2.1–v2.2, v2.4, v3.1, v5.1): `create_app()`; routes stay thin over the core, the interpreter and the
  journal; it binds `127.0.0.1`; no response carries a hidden level's text, a hidden trace or the live
  world state; errors use `{"error", "detail"}`.
- **`golem/screen/`** (v2.2, v2.4, v3.2–v3.3, v5.3): plain HTML, canvas and JavaScript. It draws what the server
  sends and holds no rules, and it uses no framework, no build step and no CDN. v2.2 is a text page with no
  design. From v3.2, the look and the motion follow the design handoff in
  `specification/design/golem-clay/README.md`; its values are final.
- **`golem/cli.py`, `golem/local.py` and the owner tools:** one request per command, JSON out, exit codes
  0/1/2, program text sent (never paths), the `GOLEM_WORKSPACE` restriction applied.
- **`golem/journal/`** (v5.2): SQLite in transactions, atomic trace writes, versions deduplicated by
  SHA-256 with their reasons, hidden traces kept apart and never served.
- **`golem/orchestrator/` and `agents/scribe/`** (v6):
  - the workspace is outside the repository;
  - the environment never holds `GOLEM_OWNER_TOKEN` or any `ANTHROPIC_*` variable;
  - the tool rules are written to `.claude/settings.json`;
  - the agent runs in its own process group, which is killed at the time limit.

  The tests use the fake agent, never `claude`.
- **`levels/`:** the standard format. Every committed training level has a recorded solution in
  `tests/fixtures/solutions/`. Never read, create or commit anything under `levels/hidden/` except its
  `README.md`.
- **Contract changes** (ARCHITECTURE.md §Contracts) update ARCHITECTURE.md (and `concept.en.md` where it
  states the same thing) and the test that pins the contract, in the same commit.
- **Scope:** stay inside the phase; don't add what no phase asks for. Follow the existing style.

#### 2d. Validate

1. **Lint:** `uv run ruff check .` must be clean.
2. **Tests:** `uv run pytest` must exit 0. Every code issue adds or extends tests. No test touches the
   network or a model: the server and the CLI run in-process, lupa runs for real, and the agent is the fake
   script.
3. **Determinism:** for interpreter, driver, stop or journal changes, the run-twice tests must be green and
   the traces byte-identical.
4. **Manual (owner) criteria:**
   - **Your share:** you may start the server locally (`uv run golem-server`) and run `golem` or `curl`
     against `127.0.0.1` to check your own work.
   - **The owner's share:** playing on the screen, swapping a program by hand with `golem-local`, watching a
     replay, writing hidden levels. Print a numbered checklist and ask the owner to perform and confirm it.
   - **Live Scribe sessions** spend the owner's Claude subscription. They happen only when the owner asks.
   - **Recording:** record each item as `confirmed by owner` or `pending owner`, never as `pass` on your own.
5. **Acceptance criteria:** walk each criterion against the phase DoD in ROADMAP.md §vA.B.

Gates that don't apply yet (there is no `pyproject.toml` before v1.1) are recorded as `n/a`. Never commit on
a red gate.

#### 2e. Commit

```bash
git add {specific files created or modified}
git commit -m "$(cat <<'EOF'
GOLEM-###: {title}

{1-2 sentence summary of what was implemented}

Closes #{github-issue-number}

Co-Authored-By: <the running model's trailer> <noreply@anthropic.com>
EOF
)"
```

- **Manual checks still pending:** write `Refs #N` instead of `Closes #N`, so that pushing doesn't close an
  issue the owner hasn't verified.
- **`ops` issue with no repo artifact:** it has no commit; go straight to 2g once the owner confirms.

#### 2f. Push

`git push`.

#### 2g. Close or hold the issue

- **All criteria met:** close the issue with a summary.

  ```bash
  gh issue close {number} --comment "$(cat <<'EOF'
  ## Implementation Summary

  **Commit:** {hash or "none (owner steps only)"}
  **Files changed:** {count}

  ### What was done
  {bullets}

  ### Validation
  {lint / tests / determinism: pass, fail or n/a; manual: confirmed by owner}

  ### Acceptance criteria
  {checklist}
  EOF
  )"
  ```

- **Owner checks still pending:** leave the issue open. Comment with the pending checklist, mark it
  `awaiting owner` in the log, and continue with issues that don't depend on it.

#### 2h. Log progress

Add to the execution log: the issue id and title, commit, files, gate results, manual checks, and status
(`completed` / `awaiting owner` / `failed` / `skipped`).

### Step 3: Handle failures

If implementation or validation fails:

1. Do not commit broken code.
2. Revert: `git checkout -- .` for tracked files, and delete **by name** the new files this issue created.
   Never `git clean`.
3. Comment on the GitHub issue explaining what failed.
4. Log the failure.
5. Ask the user whether to continue with the next issue (if nothing depends on the failed one) or stop.

### Step 3b: No automatic version bump

Never change `VERSION`, `RELEASE.txt`, `pyproject.toml`'s version or tags here. That is `/release-version`,
on explicit confirmation. A phase with failed, skipped or `awaiting owner` issues is **not** releasable;
say so in the report.

### Step 4: Write the execution report

Write `specification/implementation/vA.B-execution-report.md`:

```markdown
# Phase vA.B — Execution Report

**Date:** {date}
**Branch:** {branch}
**Label:** vA.B::phase
**Target release:** {the release that will cover this phase, e.g. v1.3.0 for any phase of /ship-phase v1}
**Executed by:** Claude Code

## Summary

| Status | Count |
|--------|-------|
| Completed | {n} |
| Awaiting owner | {n} |
| Failed | {n} |
| Skipped | {n} |
| Remaining | {n} |

## Issues

| # | GOLEM ID | Title | Status | Commit | Files | Gates | Manual |
|---|----------|-------|--------|--------|-------|-------|--------|
| 1 | GOLEM-001 | ... | completed | a1b2c3d | 4 | lint ✓ tests ✓ determinism n/a | confirmed |

## Detailed Results

### GOLEM-001: ...
**Status:** completed · **Commit:** a1b2c3d · **GitHub:** #5
**Gates:** [x] lint · [x] tests · [ ] determinism (n/a)
**Manual (owner):** {each check: confirmed by owner / pending owner}

## Design notes
{only for phases that decide a design: the v2.3 spike's answers, the v2.5 prototype's findings}

## Next Steps
{remaining or awaiting-owner issues, their dependencies, and whether the phase is releasable}
```

Commit the report (`docs: vA.B execution report`, with the trailer) and push.

## Important Rules

- **One issue at a time**, in dependency order. Never start an issue whose dependencies aren't closed.
- **One issue = one commit.** Never mix work across ids.
- **No broken code.** Commit only when the gates that apply are green.
- **Tests ship with the feature.** No test or gate calls the network or a model. Live Scribe sessions are
  opt-in, by the owner.
- **Manual checks need the owner.** Never report a manual DoD check as passed without the owner's
  confirmation, and never `Closes #N` an issue with pending owner checks.
- **Contracts stay stable.** A contract change updates ARCHITECTURE.md and its pinning test in the same
  commit.
- **Invariants:**
  - One core: no rule outside `golem/core/`.
  - The agent's isolation: no hidden level text, hidden trace or live world state in any response; `run`
    refuses hidden ids; the CLI reads programs only inside `GOLEM_WORKSPACE`; the workspace is outside the
    repository.
  - The sandbox allowlist, text-only loading, and the sentinel budget error.
  - Determinism: the same program on the same level gives byte-identical traces.
  - The server binds `127.0.0.1` only.
- **Secrets stay out:**
  - Never read, print, copy or commit anything under `levels/hidden/`. Tests use `tests/fixtures/hidden/`.
  - Never print `.env` (`GOLEM_OWNER_TOKEN`) or anything under `data/`. To check that a value is set, test
    it without echoing it (`grep -q '^GOLEM_OWNER_TOKEN=.' .env`).
  - The owner token never goes into argv, logs, commits or issue comments, and never into the agent's
    environment.
- **Ask on ambiguity.** If an issue is unclear, ask rather than guess.
- **Progress updates.** Print a short status line after each issue.
