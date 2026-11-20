---
name: ship-phase
description: Full GitHub-backed delivery pipeline over ROADMAP phases, on the checked-out branch. Takes one selector or a comma-separated LIST of phases/versions/ranges (e.g. v1.2, v3, v1-v3). The list names TARGETS - missing earlier phases are added automatically, the set is de-duplicated, sorted into roadmap order, and already-released phases are skipped. Per version - generate-issues (with reconcile), upload-issues and execute-issues for each of its phases; then a STOP for the owner to test the version, with fixes made together; then review-and-fix-issues and ONE release-version for the version. At the END of the run a HARDEN sweep runs BY DEFAULT (opt out with --no-harden). Never creates, switches or merges branches. Gated; stops on failure; pauses for the owner.
---

# Skill: Ship Phase — the full delivery pipeline

Drive the whole loop over the ROADMAP's phases, **one version at a time**. Each phase is executed before
the next one is generated, so the next phase's issues are reconciled against the real implementation. When
the version's phases are built, the run **stops so that the owner can test the version**; problems found are
fixed together with the owner. Only then does the version get its code review with fixes, and then **one
release**. The hardening sweep of deferred findings runs **by default once at the end of the run**; pass
`--no-harden` to skip it.

**Branches are the owner's.** The run works on the branch that is checked out when it starts. Every commit,
push and tag goes from that branch. The skill never creates, switches, merges, rebases or deletes a branch,
and never pushes to any other branch.

**The loop:**

```
PLAN = selectors → phases → de-duplicated → + missing earlier phases → sorted into roadmap order
       → minus already-released phases → grouped by version

for each VERSION vA in PLAN (in order), on the checked-out branch:
    for each PHASE vA.B of vA in PLAN (in order):
        0. RECONCILE  — ground vA.B in the real implementation + all prior fixes (inside generate-issues)
        1. generate-issues vA.B
        2. upload-issues @specification/implementation/vA.B-issues.md
        3. execute-issues vA.B::phase   (implement → gates → owner checks → commit → push → close)
    4. OWNER TEST     ⏸ STOP: the owner tests the version; fixes are made together, each with a test
    5. review-and-fix-issues vA        (after the owner says testing is finished)
    6. release-version A.L.0           ← ONE RELEASE PER VERSION; vA.L = its last phase built in this run
    → REPORT the version to chat
→ END OF RUN: HARDEN (harden-findings <plan scope> --release) — BY DEFAULT, skipped with --no-harden
→ overall summary to chat
```

This skill is a **thin orchestrator**. It sequences the sub-skills, adds the gating, the owner-test stop,
the per-version release and the end-of-run hardening; each sub-skill keeps its own discipline.

> **This pipeline releases.** Invoking `/ship-phase` is the explicit opt-in to the automated per-version
> releases (real tags and pushes) **and** to the HARDEN sweep. `/release-version`'s own rules still hold:
> it never downgrades and it confirms the changelog. To build without releasing, use the individual skills.

## Usage

```
/ship-phase <selector>[,<selector>…] [--no-harden]
```

A **selector** is a phase (`v1.2`, or a bare `1.2`), a version (`v3` = all its phases), or a range
(`v1-v3`, `v1.2-v3.1`). Pass one, or a comma-separated list of any mix; whitespace around commas is
ignored.

- `/ship-phase v1`: build v1.1, v1.2 and v1.3, stop for the owner's test of v1, review v1, release `1.3.0`,
  then HARDEN and a summary.
- `/ship-phase v1.2`: the same for phase v1.2 alone (plus any earlier phases that aren't released yet);
  the release is `1.2.0`.
- `/ship-phase v4,v3 --no-harden`: v3 (v3.1 → v3.2 → v3.3 → test → review → `3.3.0`), then v4 (v4.1 →
  v4.2 → test → review → `4.2.0`), reordered, with no HARDEN sweep.

> **The list is a target, not the whole plan.** The roadmap is cumulative: the full interpreter (v4) needs
> the prototype (v2), and the stops (v4.2) need the full sandbox (v4.1). So missing earlier phases are **added
> automatically**, and anything already released is skipped. On a repo released through `v4.2.0`,
> `/ship-phase v5.1` does exactly one phase's work.

## Instructions

### Step 0: Scope, baseline and the plan

1. **Parse the selector list.** Split on commas and trim. Each element is a phase (`vA.B`), a version
   (`vA`), or a range. Record whether `--no-harden` was passed.
2. **Resolve against the ROADMAP.** The phase universe is the `### vA.B` headings of
   [specification/ROADMAP.md](../../../specification/ROADMAP.md), grouped under their `## vA` version
   headings, **in file order**. A version selector expands to all its phases; a range to every phase it
   spans.
3. **Reject nothing silently.** If an element doesn't resolve to a real ROADMAP phase or version (a typo,
   `v9`, a reversed range `v3-v1`), name it and ask. Never drop it and ship the rest. A phase marked
   **outline** (v8.x) cannot be shipped until its tasks are fixed in ROADMAP.md: name it and ask.
4. **Expand, de-duplicate and fill.** Resolve the elements to a set of phases. Then add **every earlier
   roadmap phase** before the latest one that isn't already in the set. These are requirements, not scope
   creep: report them at confirmation but don't ask permission.
5. **Sort into roadmap order** and group the phases by version. The set is never a running order:
   `/ship-phase v4,v3` ships v3 first. If the order differs from what was typed, say so.
6. **Skip released phases.** One release can cover several phases, so a phase `vA.B` is released when a tag
   at or above `vA.B.0` exists, compared as `A.B.C` tuples: tag `v1.3.0` covers v1.1, v1.2 and v1.3. Work
   that is partly done resumes from its remaining steps, and the sub-skills are idempotent: generate asks
   before overwriting, upload skips existing issues, execute skips closed ones, release refuses a downgrade.
   A version whose planned phases are all executed but not released resumes at **OWNER TEST**. If
   `specification/implementation/vA-owner-test.md` records that the owner finished testing, it resumes at
   the review; otherwise ask the owner whether testing is finished.
7. **Preconditions:**
   - `gh` is authenticated and the repo has a GitHub remote. If either is missing, stop and offer
     `gh repo create` (run by the user) or the offline `/ship-solution`.
   - A branch is checked out (not a detached HEAD) and has an upstream on `origin`. If it has none, ask the
     owner before pushing it.
   - After `git fetch origin`, the branch is not behind its upstream. If it is only behind, fast-forward it
     with `git pull --ff-only`; if it has diverged, stop and ask.
   - The tree is clean.
   - The automated gates are green, or `n/a` before v1.1. Never start on a red suite.
8. **Flag the owner's work up front.** Every version stops for the owner's test (step 4). Several phases
   also have **Manual (owner)** checks:
   - v2.2: playing on the text page;
   - v3.2: playing ten levels;
   - v3.3: the motion, the frame rate and the small windows;
   - v4.2: a swap by hand;
   - v5.2: writing the hidden levels;
   - v5.3: a replay;
   - v6.1: the isolation check;
   - v6.2 and v7: live Scribe sessions, which spend the owner's subscription.

   Tell the user at confirmation where the run **will stop** for them.
9. **Confirm the plan once.** Show:
   - the checked-out branch that every commit, push and tag will go to;
   - the ordered phase list, grouped by version, with the release each version will get;
   - the filled-in phases, any reordering and the skips;
   - whether HARDEN runs;
   - the owner-test stops and the Manual (owner) checks.

   Then run. Don't re-confirm before each sub-step; pause only for the blockers in the rules below.

**Worked example:** `/ship-phase v4.1,v3` on the branch `dev`, in a repo where v1 and v2 are released
(tags `v1.3.0` and `v2.4.0`).

```
selectors : v4.1 · v3
expanded  : v4.1 | v3.1 v3.2 v3.3
filled    : (nothing missing below v4.1 beyond the set)
skipped   : v1.1–v2.4                ← released (v1.3.0, v2.4.0)
ordered   : v3.1 → v3.2 → v3.3 → v4.1   (v4.1 was listed first; roadmap order is required)
branch    : dev                      ← every commit, push and tag; no other branch is touched

PLAN: v3: v3.1 → v3.2 → v3.3 → ⏸ owner test → review v3 → release 3.3.0
      v4: v4.1 → ⏸ owner test → review v4.1 → release 4.1.0
      → HARDEN v3-v4 → summary
Owner stops: the owner test of v3 and of v4; each phase's Manual (owner) DoD
```

### Step 1: BUILD — for each phase of the version, three steps, gated

Run the phases **strictly in sequence**: phase N+1 is generated only after phase N is **executed**. Invoke
each sub-skill through the **Skill tool** and follow its instructions fully.

0. **RECONCILE.** This happens inside `generate-issues` (its Step 0.5). It reads the real code, the
   earlier execution reports (including the design notes of v2.3 and v2.4), the earlier owner-test notes
   and the earlier code-review docs ("Fixes applied", "Architecture impact"). Where fixes moved the code
   away from ARCHITECTURE.md, the code is ground truth.
1. **`generate-issues vA.B`** writes `specification/implementation/vA.B-issues.md`.
2. **`upload-issues @specification/implementation/vA.B-issues.md`** creates the GitHub issues, labels and
   dependency comments, and `vA.B-github-report.md`, and commits them.
3. **`execute-issues vA.B::phase`** implements the issues one per commit, runs the gates, gets the owner's
   manual checks, pushes, closes the issues, and writes `vA.B-execution-report.md`.

**Design gates.** Two phases decide the design for everything after them:

- **v2.3** opens with the lupa spike. If the spike fails, stop the run and ask the owner to choose the
  alternative.
- **v2.4** is the swap prototype. If it changes the design, ARCHITECTURE.md is updated in that phase, and
  the run continues only after the update is committed.

### Step 2: OWNER TEST — stop and let the owner test the version

When the version's last planned phase is executed, its gates are green and everything is pushed:

1. **Stop and hand over.** Report to chat:
   - the phases and the `GOLEM-###` issues built, and the commit range;
   - the gate status;
   - **how to try it:** the exact commands that exercise what the version delivers, taken from the DoD of
     the phases built (for v1, a short `uv run python -c …` that loads a level, plays moves and prints the
     map; for v2, `uv run golem-server` with the page at `http://127.0.0.1:8700/`, and `uv run golem-local run …`).

   Then **end the turn and wait.** Don't start the review.
2. **Fix together.** For each problem the owner reports:
   - reproduce it;
   - fix it with a regression test (no network, no model);
   - run the gates;
   - commit `fix(<area>): … (owner test)` with the running model's `Co-Authored-By` trailer, and push.

   A request that is new scope, outside the version's phases, is named as such. It goes to the backlog or
   to a later phase unless the owner insists. A fix that changes a contract updates ARCHITECTURE.md and the
   pinning test in the same commit.
3. **Record it** in `specification/implementation/vA-owner-test.md`:
   - the date and the branch;
   - what the owner tested;
   - each problem, with its fix commit and its regression test;
   - anything moved to later work;
   - the owner's words that ended the testing.

   Commit it (`docs: vA owner test`) and push.
4. **Continue only when the owner says testing is finished.** Never assume it. Issues of the version's last
   phase left `awaiting owner` by execute-issues can be confirmed during this stop; close them then.

### Step 3: REVIEW, then ONE RELEASE for the version

1. **`review-and-fix-issues vA`** reviews what the version's phases built in this run (their `GOLEM-###`
   commits and the owner-test fixes). It writes the ranked review doc (`vA-code-review.md`, or
   `vA.B-code-review.md` when the run built one phase), fixes only the FIX NOW items with regression tests,
   and records them in that same doc.
2. **`release-version A.L.0`**, where `vA.L` is the version's last phase built in this run, bumps the
   version, tags `vA.L.0` and pushes the branch and the tag. One release covers every phase of the version
   built in this run: `/ship-phase v1` releases `1.3.0`, and `/ship-phase v1.2` releases `1.2.0`.

### Step 4: REPORT each version to chat

After each release, report:

- the `GOLEM-###` range → GitHub numbers, per phase;
- the execution commit range and the gate status;
- the owner test: problems found and fixed (with commits), and anything moved to later work;
- the manual checks the owner confirmed;
- the review findings (fixed now / deferred, with homes);
- any "Architecture impact" notes or design notes;
- the release tag and the branch it was pushed from.

Then continue with the next version.

### Step 5: END OF RUN — HARDEN (default; `--no-harden` skips it)

Once the last version in the plan is released, invoke **`harden-findings <first>-<last> --release`** through
the Skill tool, with the run's phase range, on the same branch.

- **What it does:** fixes every still-unfixed 🔴 HIGH / 🟠 MEDIUM finding from the run's review docs, each
  with a regression test, updates the docs in place, and ships a patch release on the latest release (e.g.
  `v3.2.1`).
- **Held findings:** its escape hatch applies, so a fix that can't land cleanly is held with a reason, not
  forced.
- **With `--no-harden`:** skip it, and list the outstanding HIGH/MEDIUM findings and their homes in the
  summary.

Then give a short **overall summary**: versions shipped with their releases, phases skipped as already
released, the branch, the HARDEN outcome, anything that stopped early and what remains, and what's next.

## Gates

- upload only after generate wrote the file;
- execute only after the issues exist;
- generate the next phase only after this phase is executed with every issue closed. None may be failed;
  only the version's last phase may leave issues `awaiting owner`, to be confirmed at OWNER TEST;
- OWNER TEST only after the version's last planned phase is executed, green and pushed;
- review only after the owner says testing is finished, and every owner-test fix is committed, pushed and
  recorded;
- release only after the review's fix-now items are committed, the gates are green, and every manual DoD
  check of the version is confirmed by the owner;
- the next version only after this one is released.

**Every phase boundary ends pushed and clean.** Before the next step, check that `git status` is clean and
there are no unpushed commits, and `git push` if there are. This skill **stops on failure by design**, so a
stop must never leave work on one machine only.

## Important Rules

- **Branches are the owner's.** Work on the checked-out branch. Never create, switch, merge, rebase or
  delete a branch, and never push to another branch.
- **The owner tests every version before its review.** Stop, hand over with the commands to try, fix
  together, record it, and wait for the owner's word that testing is finished.
- **One release per version** (`A.L.0`, numbered after the version's last phase built in the run), after
  it is built, owner-tested, reviewed and fix-now-fixed. Never release before the owner's test, and never
  release part of the phases a run builds for a version.
- **Next phase only after the previous one is executed; next version only after the previous one is
  released.** This strict order is what makes reconciliation meaningful.
- **HARDEN runs once at the end of the run, by default.** Invoking the skill is the consent; `--no-harden`
  is the opt-out.
- **Every phase boundary ends pushed and clean.**
- **Stop on failure; don't paper over it.** A failed sub-skill or a red gate halts the run. Report what
  completed and what remains. Never release a version whose gates aren't green.
- **Pause for the owner.** The owner test, owner-run steps and manual DoD checks are confirmed by the owner,
  never assumed. Never launch a live Scribe session, and never read or write hidden levels, unless the
  owner asks.
- **Pause for real decisions:** a failed lupa spike, a v2.4 design change, an id or tag collision, an
  overwrite-or-append prompt, a held HARDEN finding, a branch that diverged from its upstream, a failure.
  Routine confirmations run straight through.
- **Delegate, never duplicate.** This skill sequences `generate-issues`, `upload-issues`, `execute-issues`,
  `review-and-fix-issues`, `release-version` and `harden-findings`, and adds the gating, the owner-test stop
  and the per-version release; it has no other logic of its own.
- **The plan is roadmap-ordered and dependency-complete, always.** De-duplicate, fill the earlier phases,
  sort into ROADMAP file order, then drop the released ones. Report the fill, the reordering and the skips.
