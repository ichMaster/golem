---
name: ship-phase
description: Full GitHub-backed delivery pipeline over ROADMAP phases. Takes one selector or a comma-separated LIST of phases/versions/ranges (e.g. v1.2, v3, v1-v3). The list names TARGETS - missing earlier phases are added automatically, the set is de-duplicated, sorted into roadmap order, and already-released phases are skipped. Each version vA is built on its own branch version/vA, created from main. Per phase - generate-issues (with reconcile), upload-issues, execute-issues, review-and-fix-issues, release-version A.B.0, then main is fast-forwarded to the version branch and pushed. At the END of the run a HARDEN sweep runs BY DEFAULT (opt out with --no-harden). Gated; stops on failure; pauses for owner-run steps.
---

# Skill: Ship Phase — the full delivery pipeline

Drive the whole loop over the ROADMAP's phases. **Each phase is released before the next one is
generated**, so the next phase's issues are reconciled against the real, post-fix implementation. The
hardening sweep of deferred findings runs **by default once at the end of the run**; pass `--no-harden` to
skip it.

**Nothing is committed to `main` directly.** Each version `vA` is built on its own branch, `version/vA`. Every
commit of its phases lands there, and `main` moves only after a release, by a fast-forward to that branch.

**The loop:**

```
PLAN = selectors → phases → de-duplicated → + missing earlier phases → sorted into roadmap order
       → minus already-released (tag vA.B.0 exists)

for each VERSION vA in PLAN (in order):
    BRANCH — switch to version/vA (create it from origin/main, or fast-forward it to origin/main)
    for each PHASE vA.B of vA in PLAN (in order):
        0. RECONCILE  — ground vA.B in the real implementation + all prior fixes (inside generate-issues)
        1. generate-issues vA.B
        2. upload-issues @specification/implementation/vA.B-issues.md
        3. execute-issues vA.B::phase   (implement → gates → owner checks → commit → push → close)
        4. review-and-fix-issues vA.B   (review → ranked doc → fix-now fixes → same doc)
        5. release-version A.B.0        ← RELEASE PER PHASE (tag vA.B.0, pushed from version/vA)
        6. MERGE      — fast-forward main to version/vA and push main
        → REPORT the phase to chat
→ END OF RUN: HARDEN on the last version's branch (harden-findings <plan scope> --release), then MERGE
  — BY DEFAULT, skipped with --no-harden
→ overall summary to chat
```

This skill is a **thin orchestrator**. It sequences the sub-skills, adds the gating and the end-of-run
hardening, releases per phase, and owns the branches: one per version, merged into `main` at each release.
Each sub-skill keeps its own discipline and works on the current branch.

> **This pipeline releases.** Invoking `/ship-phase` is the explicit opt-in to the automated per-phase
> releases (real tags and pushes), to fast-forwarding and pushing `main` after each release, **and** to the
> HARDEN sweep. `/release-version`'s own rules still hold: it never downgrades and it confirms the
> changelog. To build without releasing, use the individual skills.

## Usage

```
/ship-phase <selector>[,<selector>…] [--no-harden]
```

A **selector** is a phase (`v1.2`, or a bare `1.2`), a version (`v3` = all its phases), or a range
(`v1-v3`, `v1.2-v3.1`). Pass one, or a comma-separated list of any mix; whitespace around commas is
ignored.

- `/ship-phase v1.2`: ship phase v1.2, plus any earlier phases that aren't released yet.
- `/ship-phase v3`: ship v3.1 and v3.2 (and any unreleased earlier phases), then HARDEN, then a summary.
- `/ship-phase v4,v3 --no-harden`: ships v3.1 → v3.2 → v4.1 → v4.2 (reordered), with no HARDEN sweep.

> **The list is a target, not the whole plan.** The roadmap is cumulative: the interpreter (v3) needs the
> core (v1), and the stops (v4.2) need the swap prototype (v4.1). So missing earlier phases are **added
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
5. **Sort into roadmap order.** The set is never a running order: `/ship-phase v4,v3` ships v3 first. If
   the order differs from what was typed, say so.
6. **Skip released phases** (tag `vA.B.0` exists). A phase that is partly done (issues file or GitHub
   issues exist, but no tag) resumes from its remaining steps. The sub-skills are idempotent: generate asks
   before overwriting, upload skips existing issues, execute skips closed ones, release refuses a downgrade.
7. **Preconditions:**
   - `gh` is authenticated and the repo has a GitHub remote. If either is missing, stop and offer
     `gh repo create` (run by the user) or the offline `/ship-solution`.
   - The tree is clean.
   - After `git fetch origin`, local `main` holds no commits that `origin/main` lacks. If it does, stop and
     ask: the run would leave them out of every version branch.
   - If the current branch is neither `main` nor a `version/vA` branch and holds commits that are not in
     `origin/main`, name them and ask. The run starts from `origin/main`, so those commits would be left
     out.
   - The automated gates are green, or `n/a` before v1.1. Never start on a red suite.
8. **Flag the owner's work up front.** Several phases have **Manual (owner)** checks:
   - v2.2: playing ten levels;
   - v4.2: a swap by hand;
   - v5.2: writing the hidden levels;
   - v5.3: a replay;
   - v6.1: the isolation check;
   - v6.2 and v7: live Scribe sessions, which spend the owner's subscription.

   Tell the user at confirmation that the run **will pause** for them.
9. **Confirm the plan once.** Show:
   - the ordered phase list, grouped by version, with each version's branch (`version/vA`, and whether it
     will be created or already exists);
   - the filled-in phases, any reordering and the skips;
   - whether HARDEN runs;
   - the expected owner pauses.

   Then run. Don't re-confirm before each sub-step; pause only for the blockers in the rules below.

**Worked example:** `/ship-phase v4.1,v3` on a repo where v1 and v2 are fully released (`v1.1.0`–`v2.2.0`
tagged).

```
selectors : v4.1 · v3
expanded  : v4.1 | v3.1 v3.2
filled    : (nothing missing below v4.1 beyond the set)
skipped   : v1.1–v2.2                ← already released
ordered   : v3.1 → v3.2 → v4.1      (v4.1 was listed first; roadmap order is required)
branches  : version/v3 (v3.1, v3.2) · version/v4 (v4.1), both created from origin/main

PLAN: version/v3: v3.1 → merge, v3.2 → merge · version/v4: v4.1 → merge
      → HARDEN v3-v4 on version/v4 → merge → summary
Owner pauses: the v3.1 lupa spike if it fails (the Lua choice is the owner's); each phase's Manual (owner) DoD
```

### Step 1: A branch per version

Before the first planned phase of each version `vA`, switch to its branch:

```bash
git fetch origin
git switch version/vA \
  || git switch --no-track -c version/vA origin/main   # neither a local nor a remote branch exists yet
git merge --ff-only origin/version/vA                   # only if the remote branch exists: catch up with it
git merge --ff-only origin/main                         # a no-op when the branch already contains main
git push -u origin version/vA
```

`git switch version/vA` also picks up a branch that exists only on `origin`, so a run resumed on another
machine continues the same branch.

- **The branch is reused** for every phase of the version, for a resumed run and for a later
  `/ship-phase` that picks up the version's next phase. After each release it equals `main` again, so the
  fast-forward to `origin/main` is a no-op unless `main` moved.
- **If either `git merge --ff-only` fails,** the local branch, its remote copy or `main` have diverged. Stop
  and ask the owner. Never rebase a version branch: its release tags are already pushed, and a rebase would
  leave them on commits that are no longer in its history.
- **Every sub-skill in this version** commits and pushes on `version/vA`. None of them switches branches or
  touches `main`; only the MERGE step below does.
- **Merged branches are kept.** Deleting one is the owner's call.

### Step 2: For each phase, the six steps, gated

Run the phases **strictly in sequence**: phase N+1 starts only after phase N is **released and merged into
`main`**. Invoke each sub-skill through the **Skill tool** and follow its instructions fully.

0. **RECONCILE.** This happens inside `generate-issues` (its Step 0.5). It reads the real code, the
   earlier execution reports (including the design notes of v3.1 and v4.1) and the earlier code-review docs
   ("Fixes applied", "Architecture impact"). Where fixes moved the code away from ARCHITECTURE.md, the code
   is ground truth.
1. **`generate-issues vA.B`** writes `specification/implementation/vA.B-issues.md`.
2. **`upload-issues @specification/implementation/vA.B-issues.md`** creates the GitHub issues, labels and
   dependency comments, and `vA.B-github-report.md`, and commits them.
3. **`execute-issues vA.B::phase`** implements the issues one per commit, runs the gates, gets the owner's
   manual checks, pushes, closes the issues, and writes `vA.B-execution-report.md`.
4. **`review-and-fix-issues vA.B`** writes the ranked review doc, fixes only the FIX NOW items (with
   regression tests) and records them in that same doc.
5. **`release-version A.B.0`** bumps the version, tags `vA.B.0` and pushes `version/vA` and the tag.
6. **MERGE into `main`.** Fast-forward `main` to the released branch and push it:

   ```bash
   git switch main
   git pull --ff-only origin main      # local main catches up if the remote moved
   git merge --ff-only version/vA
   git push origin main
   git switch version/vA
   ```

   After the fast-forward, `main`, `version/vA` and the tag `vA.B.0` point to the same commit. If
   `git merge --ff-only` fails, `main` has commits that the branch lacks: switch back to `version/vA`, stop,
   and ask the owner. Never create a merge commit, never rebase and never force-push `main`.

**Gate the hand-offs:**

- upload only after generate wrote the file;
- execute only after the issues exist;
- review only after execute finished with every issue closed (none failed or `awaiting owner`);
- release only after the review's fix-now items are committed, the gates are green, and the phase's manual
  DoD is confirmed by the owner;
- merge only after the release commit and the tag `vA.B.0` are pushed;
- start the next phase only after this one is merged into `main`.

**Design gates.** Two phases decide the design for everything after them:

- **v3.1** opens with the lupa spike. If the spike fails, stop the run and ask the owner to choose the
  alternative.
- **v4.1** is the swap prototype. If it changes the design, ARCHITECTURE.md is updated in that phase, and
  the run continues only after the update is committed.

**Every phase boundary ends pushed, clean and merged.** Before the next phase, check that `git status` is
clean, that neither `version/vA` nor `main` has unpushed commits (`git push` if they do), and that `main`
equals `version/vA`. This skill **stops on failure by design**, so a stop must never leave a phase's work on
one machine only. A stop before the release leaves the work pushed on `version/vA` and `main` untouched.

### Step 3: REPORT each phase to chat

After each release and merge, report:

- the `GOLEM-###` range → GitHub numbers;
- the execution commit range and the gate status;
- the manual checks the owner confirmed;
- the review findings (fixed now / deferred, with homes);
- any "Architecture impact" notes or design notes;
- the release tag, the branch, and the commit `main` now points to.

Then continue with the next phase.

### Step 4: END OF RUN — HARDEN (default; `--no-harden` skips it)

Once the last phase in the plan is released and merged, stay on the plan's last version branch
(`version/vZ`, which now equals `main`) and invoke **`harden-findings <first>-<last> --release`** through
the Skill tool, with the run's phase range. When it finishes, **MERGE** whatever it landed (its fixes, its
report updates and the patch release) into `main` exactly as in step 6, so that the run ends with `main`
equal to `version/vZ`.

- **What it does:** fixes every still-unfixed 🔴 HIGH / 🟠 MEDIUM finding from the run's review docs, each
  with a regression test, updates the docs in place, and ships a patch release on the latest phase (e.g.
  `v3.2.1`).
- **Held findings:** its escape hatch applies, so a fix that can't land cleanly is held with a reason, not
  forced.
- **With `--no-harden`:** skip it, and list the outstanding HIGH/MEDIUM findings and their homes in the
  summary.

Then give a short **overall summary**: phases shipped, phases skipped as already released, the branches
used and the commit `main` ends on, the HARDEN outcome, anything that stopped early and what remains, and
what's next.

## Important Rules

- **Release per phase (`A.B.0`)**, after it is built, reviewed, fix-now-fixed and owner-verified. Never
  batch phases into one release; never release mid-phase.
- **One branch per version, `version/vA`**, created from `origin/main` and reused for all its phases.
  Nothing is committed to `main` directly.
- **`main` moves only by a fast-forward to a released branch**: after each phase release, and after HARDEN.
  No merge commits, no rebases, no force-pushes. If a fast-forward is impossible, stop and ask.
- **Next phase only after the previous one is released and merged.** This strict order is what makes
  reconciliation meaningful.
- **HARDEN runs once at the end of the run, by default.** Invoking the skill is the consent; `--no-harden`
  is the opt-out.
- **Every phase boundary ends pushed, clean and merged.**
- **Stop on failure; don't paper over it.** A failed sub-skill or a red gate halts the run. Report what
  completed and what remains. Never release a phase whose gates aren't green.
- **Pause for the owner.** Owner-run steps and manual DoD checks are confirmed by the owner, never assumed.
  Never launch a live Scribe session, and never read or write hidden levels, unless the owner asks.
- **Pause for real decisions:** a failed lupa spike, a v4.1 design change, an id or tag collision, an
  overwrite-or-append prompt, a held HARDEN finding, a version branch that diverged from `main`, a failure.
  Routine confirmations run straight through.
- **Delegate, never duplicate.** This skill sequences `generate-issues`, `upload-issues`, `execute-issues`,
  `review-and-fix-issues`, `release-version` and `harden-findings`, and adds gating, the version branches and
  the merges into `main`; it has no other logic of its own.
- **The plan is roadmap-ordered and dependency-complete, always.** De-duplicate, fill the earlier phases,
  sort into ROADMAP file order, then drop the released ones. Report the fill, the reordering and the skips.
