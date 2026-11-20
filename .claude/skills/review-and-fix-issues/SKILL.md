---
name: review-and-fix-issues
description: Code-review a phase, a component or the current branch, write a criticality-ranked recommendations doc in specification/implementation/, implement the fix-now items with regression tests, then record what was done in the SAME doc. Never releases.
---

# Skill: Review & Fix Issues

One loop over the codebase: **review → recommend → fix → record.**

1. Run a critical code review.
2. Write a single recommendations document that ranks findings by criticality and marks each **FIX NOW**
   or **DEFER →**.
3. Implement the fix-now items with regression tests.
4. **Update that same document in place**, marking what was fixed and adding a "Fixes applied" section.

The recommendations and the results live in **one document**.

This skill fixes only small, in-scope, high-value findings. It **never** bumps the version or cuts a
release (that stays with `/release-version`), and it never pulls deferred or larger work forward without
flagging it.

## Usage

```
/review-and-fix-issues [target]
```

- `/review-and-fix-issues v3.2`: review what the phase delivered (through its tag `v3.2.0` if released).
- `/review-and-fix-issues interp`: scope the review to one component (`core` / `interp` / `server` /
  `screen` / `cli` / `journal` / `agent` / `tests`).
- `/review-and-fix-issues`: review the **current branch**, i.e. everything built so far.

## Instructions

### Step 0: Scope and a green baseline

1. **Resolve the target:**
   - a phase (`vA.B`) / a version (`vA`) or its tag: the commits whose subjects carry that phase's `GOLEM-###`
     ids, plus the files they touched;
   - a component;
   - no argument: the whole working tree.
2. **Clean tree:** check `git status` is clean and note the branch.
3. **Green baseline:** run the automated gates (`uv run ruff check .`, `uv run pytest`). If the suite is
   **red or flaky**, say so. A flaky test in this project is itself a determinism finding. Fix a clear flake
   first (small, its own commit) or raise it and ask. **Never review or fix on top of a red suite.**

### Step 1: Critical code review

Read the in-scope code and take the highest-risk areas first. Be **adversarial**: hunt for *real*
defects, not restatements of what works.

- **One core (v1 onward):**
  - Is any rule duplicated outside `golem/core/`, in the screen's JavaScript, the interpreter, the validator
    or a replay?
  - Does `golem/core` import anything outside the standard library?
- **The rules (v1.2):**
  - Is a push refused into a wall and into another box?
  - Does a failed move count a step?
  - Does the corner rule fire only after a push, only off a goal, and in all four orientations?
  - Is a move applied after the level is solved or lost?
  - Does the parser accept an open map, two robots, or more boxes than goals?
- **Determinism (every phase):**
  - Does a Python set or dict ordering reach JSON, a trace or a report unsorted?
  - Does anything read the clock or unseeded randomness?
  - Inside Lua: is `pairs` still the fixed-order version, `next` absent, `table.sort` the merge sort, and
    `tostring` address-free? Is `math.random` seeded per run, and `math.randomseed` absent?
  - Is the lupa version pinned, and is `lupa.lua54` used explicitly?
  - Does a run-twice test exist for every fixture program, and are the traces compared byte for byte?
- **The sandbox (v2.3, v4.1):**
  - Is the program's environment a fresh table, never `_G`?
  - Is anything outside the allowlist reachable, directly or through a library table (`string.dump`,
    `debug` reached indirectly, `package.loaded`)?
  - Is the runtime created with `register_eval=False` and `register_builtins=False`? Is any Python object
    (a callable, a dict, the driver) passed into Lua, where its attributes could be reached?
  - Is loading text-only (mode `"t"`)?
  - Is `max_memory` set?
  - Can a metatable be set on `memory` or on a string?
- **The driver and the budgets (v2.3, v4.1):**
  - Does an infinite loop with no robot command end on the instruction budget?
  - Is the budget error a sentinel compared by identity, so that a program's own
    `error("instruction budget exhausted")` is not a loss?
  - Is the hook installed on the coroutine actually running, including after a swap?
  - Is `give_up`'s reason capped?
  - Does a program that returns count as `give_up("program ended")`?
  - Does a driver exception end the run as `failed`/`internal` without taking down the server?
  - Is `last_actions` capped at `LAST_ACTIONS_N`?
- **Stops and swaps (v2.4, v4.2):**
  - After a swap, is `memory` the same table, are the counters carried over, and is the old coroutine
    impossible to resume?
  - Are `continue` after `error`/`give_up` and `swap` after `deadlock` refused?
  - Does `half_budget` fire exactly once, and only when no box has reached a goal since the start?
  - Does the `repeat` key include the canonical `memory`?
  - Does the `memory` conversion survive cycles, functions, huge tables and number keys, and does it respect
    the cap?
  - Does the snapshot leak the robot's position or the map?
- **The API and the CLI (v5.1):**
  - Is there exactly one open run per session?
  - Does `run` refuse hidden ids?
  - Do errors use `{"error", "detail"}`, and are the exit codes 0/1/2?
  - Does the CLI send text, never paths, and does the `GOLEM_WORKSPACE` restriction survive symlinks and
    `..`?
  - Does the server bind `127.0.0.1`?
- **The journal and the validator (v5.2):**
  - Are versions deduplicated per session by SHA-256, and is a new version without a reason refused after
    the first?
  - Are writes transactional and traces atomic?
  - Does any route return a hidden level's text or a hidden trace? Run the hidden-leak test mentally against
    every new route.
  - Is the version limit enforced on the server (409), not only in the orchestrator?
  - Do the owner routes answer 401 without the token?
  - Are runs left open by a restart closed as `abandoned`?
- **Replay (v5.3):**
  - Are the frames rebuilt by the core, not by the page?
  - Does a hidden run answer 404?
  - Does the last frame equal the report?
- **The orchestrator and Scribe (v6):**
  - Is the workspace outside the repository, with a path inside it refused?
  - Is the agent's environment free of `GOLEM_OWNER_TOKEN` and every `ANTHROPIC_*` variable?
  - Does the tool-rules file allow only `golem` in Bash and only the workspace for files, and deny the web
    tools?
  - Is the whole process group killed at the time limit?
  - Is the end reason recorded?
  - Do Scribe's instructions contain a strategy, a program or a hint for a specific level?
  - Do they name every command exactly as the contracts do?
- **Secrets and leaks:**
  - Does a hidden level's text, the owner token or anything from `data/` appear in a log, an exception
    message, a test, a fixture or a commit?
  - Are fixture hidden levels the only hidden levels the tests use?
- **Robustness:**
  - Can a malformed WebSocket message or a huge program take down the server?
  - Is the WebSocket reconnect safe?
  - Does a malformed level reach a run?
- **Spec drift:** does the code diverge from the ARCHITECTURE.md contracts or the ROADMAP, or add what no
  phase asks for?

For each finding, capture:

- a **concrete failure scenario** (inputs → wrong result, leak, hang or crash);
- a `file:line` anchor;
- a **severity**: 🔴 HIGH / 🟠 MEDIUM / 🟡 LOW;
- a **proposed fix**.

A hidden-level leak, a sandbox escape, a hang of the server and a determinism break are 🔴 HIGH by default.

Cross-check against ROADMAP.md and ARCHITECTURE.md. If a gap is already scheduled for a later phase, note that
instead of treating it as new.

### Step 2: Write the recommendations document (the plan)

Write **one** doc at `specification/implementation/<scope>-code-review.md`, e.g. `v3.2-code-review.md`,
`interp-code-review.md`, or `branch-code-review.md` for the whole tree. Include:

- a header: date, reviewer, **scope**, method;
- a **criticality-ranked summary table**: `# | Severity | Finding | Recommendation | Status`.
  Recommendation is `FIX NOW` or `DEFER → <home>`; Status starts as `⏳ pending`;
- for each finding, its failure scenario and proposed fix;
- a short **"What's solid"** section, to keep the review balanced;
- **suggested next actions**.

Decide **FIX NOW vs DEFER** honestly:

- **FIX NOW** means real, small, self-contained, high-value and in scope now: a sandbox hole, a hidden-level
  leak, a nondeterministic trace, a hang, a crash that takes down the server.
- **DEFER →** means larger work, or work a later phase already owns. Give the home: a later phase (`v1.2` …
  `v8.x`), `backlog` (no phase owns it) or `cleanup (/simplify)`. Do **not** pull it forward.

Commit the doc as the plan (`docs: vA.B code review`) **and push it** if a remote exists. The review is worth
keeping even if the fix pass is interrupted.

### Step 3: Implement the FIX NOW items, with tests

For each **FIX NOW** finding, in criticality order:

1. Implement the fix following `CLAUDE.md` and ARCHITECTURE.md. Keep it minimal.
2. **Add a regression test that would have caught the bug.** A sandbox hole gets a test with the escape
   attempt; a leak gets a test with a fixture hidden level; a determinism break gets a run-twice test. No
   test calls the network or a model.
3. **Validate:** lint and tests green. Commit only passing code.
4. **Commit** one focused change per finding: `fix(<area>): … (code review #N)`, with the running model's
   `Co-Authored-By` trailer. **Then push.** Never leave a landed fix unpushed.
5. **A contract change** updates ARCHITECTURE.md and the pinning test in the **same** commit.

If a fix turns out bigger than "fix now" (it touches a contract broadly or needs a design decision),
**stop and re-classify it as DEFER** in the doc, with the reason, and move on. Don't half-land it.

### Step 4: Update the SAME document (the result)

Edit the doc **in place**:

- **Status column:** flip it to `✅ FIXED — <commit>` for each applied fix; keep `⏳ deferred` for the rest.
- **"Fixes applied" section:** for each fix, give the change, the regression test and the verification
  (final gate status).
- **"Architecture impact" note:** add one for any fix that **changed a documented contract or
  design-relevant behavior**, and make sure ARCHITECTURE.md reflects it. The next
  `/generate-issues` or `/reconcile-issues` reads these notes.
- **"Suggested next actions":** update them. Fixes on an already-released phase suggest a patch release
  (`/release-version A.B.1`); deferred items are carried into their phase.

Commit the update (`docs: vA.B code review — fixes applied`) **and push**.

### Step 5: Report

Summarize:

- findings by severity;
- which were **fixed** (with commits) and which **deferred** (with homes);
- the final gate status.

If fixes landed on an already-released phase, suggest `/release-version A.B.<next>`, but do **not** run
it. Offer a deeper pass with `/code-review high` for confirmation.

## Important Rules

- **One document, updated in place.** Recommendations and results share a single doc.
- **Fix only the FIX NOW items.** Never pull deferred work forward without re-classifying it in the doc.
- **Every fix ships a regression test**, with no network and no model.
- **Green before, green after.** Commit only code that passes the gates.
- **Record architecture deltas.** A contract change updates ARCHITECTURE.md and its test in the same commit,
  and gets an "Architecture impact" note.
- **Never release.** No version bump, no tag.
- **Never leave work unpushed** (when a remote exists). This skill can stop mid-way, so "the next step will
  push it" is not a safe assumption.
- **Never read or quote `levels/hidden/`**, not even to illustrate a finding.
- **Ask on genuine ambiguity**: an unclear scope, or a borderline fix-now-vs-defer call.
