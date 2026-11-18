# v1 — Code Review

**Date:** 2026-11-18
**Reviewer:** Claude Code (`/review-and-fix-issues v1`, run by `/ship-phase v1`)
**Scope:** everything v1 built on `v1-dev`. That is GOLEM-001…010 (commits 05390d4…a8c715e), with no fixes
from the owner's test (see [v1-owner-test.md](v1-owner-test.md)). The files: `golem/core/` (`level.py`,
`levels.py`, `world.py`, `replay.py`), `tests/`, `levels/`, `pyproject.toml`, `.github/workflows/ci.yml`,
and the ARCHITECTURE.md text these issues changed.
**Method:**
- read every file in scope against ARCHITECTURE §World and rules and §Contracts, ROADMAP §v1.1–§v1.3 and
  the CLAUDE.md invariants;
- reproduce each finding with a short script;
- baseline: lint clean, 261 tests green in four consecutive runs (no flake).

## Summary

| # | Severity | Finding | Recommendation | Status |
|---|----------|---------|----------------|--------|
| 1 | 🟠 MEDIUM | `from_json` accepts a robot or box outside the walls, and the robot can then walk off the map | FIX NOW | ⏳ pending |
| 2 | 🟡 LOW | The parser accepts boxes and goals the robot can never reach, so an unsolvable level loads | FIX NOW | ⏳ pending |
| 3 | 🟡 LOW | Documentation drift: the layout omits `levels.py`; ROADMAP §v1.3 shows the old `replay` signature | FIX NOW | ⏳ pending |
| 4 | 🟡 LOW | `levels_root()` resolves `levels` against the working directory; from elsewhere the listing is silently empty | DEFER → v2.1 | ⏳ pending |
| 5 | 🟡 LOW | `from_json` accepts states that contradict themselves (playing past the budget, solved with a box off a goal) | DEFER → backlog | ⏳ pending |
| 6 | 🟡 LOW | A level file with a UTF-8 BOM or CR-only line ends gives a confusing error | DEFER → v7.1 | ⏳ pending |
| 7 | 🟡 LOW | `load_level` with a non-string id raises `AttributeError`, not `UnknownLevel` | DEFER → v2.1 | ⏳ pending |
| 8 | 🟡 LOW | The direction offsets are defined twice (`level.DIRECTIONS`, `world.OFFSETS`) | DEFER → cleanup (/simplify) | ⏳ pending |

No 🔴 HIGH finding:
- nothing reaches JSON unsorted;
- nothing reads the clock or unseeded randomness;
- no rule exists outside `golem/core/`;
- nothing touches `levels/hidden/`.

## Findings

### 1. 🟠 `from_json` accepts a robot or box outside the walls — FIX NOW

**Where:** `golem/core/world.py:217` (`_saved_cell`).

**What:** `_saved_cell` checks only the level's bounding box and the walls. A level with ragged rows or
leading spaces has cells inside the bounding box that lie outside its walls. ARCHITECTURE.md says
`from_json` refuses "a robot or box … outside the map", but it accepts those cells.

**Failure scenario:**
- Level `"  ####\n###  #\n#@$. #\n######"`. A saved world with `"robot": [0, 0]` restores without error.
- Three `move(world, "W")` calls then move the robot to `(0, -3)`, each returning `True`.
- `look` there returns `"empty"` in every direction, and `render` no longer shows the robot.

The closed-map invariant, on which `move` and `look` rely, is broken. Today only `to_json` output reaches
`from_json`, so the impact is a contract violation rather than a live exploit.

**Fix:**
- The parser already flood-fills the robot's area. It keeps the result as `Level.inside`: every non-wall
  cell reachable from the robot's start without crossing a wall.
- `from_json` refuses a robot or box outside `inside`.
- ARCHITECTURE.md names the field.
- Regression test: the scenario above.

### 2. 🟡 The parser accepts boxes and goals the robot can never reach — FIX NOW

**Where:** `golem/core/level.py:101`.

**What:** The validity rules check the robot, the counts and the closed map. They do not check that the
boxes and goals lie in the robot's area. Walls never move, so such a box can never be pushed, or such a
goal never reached.

**Failure scenario:** a level with a goal written outside its walls (`"   .\n#####\n#@$ #\n#####"`) parses,
and every program fails it.
- Training levels are protected: every one needs a recorded solution.
- The owner's hidden levels (v5.2) have no recorded solution. Such a level would count as a failure for
  every program version until the solvability check in v7.1, and live Scribe sessions spend the owner's
  subscription on it.

**Fix:** with `Level.inside` from #1, a box or goal outside the robot's area is a `LevelError` at its cell.
ARCHITECTURE.md adds the rule to the validity list. Regression tests: a goal outside the walls, and a box in
a sealed pocket.

### 3. 🟡 Documentation drift — FIX NOW

**Where:** `specification/ARCHITECTURE.md:473` (Repository layout) and `specification/ROADMAP.md:92`.

**What:**
- The layout lists `golem/core/` as `level.py, world.py, replay.py`; `levels.py` (ids, listing, budgets)
  is missing.
- ROADMAP §v1.3 still says `replay(level, moves)`. GOLEM-009 settled on `replay(level, moves, budget)`,
  because a `World` needs a step budget.

**Failure scenario:** the next `/generate-issues` or a reader trusts the stale names.

**Fix:** correct both lines. Documentation only, so there is no test.

### 4. 🟡 `levels_root()` depends on the working directory — DEFER → v2.1

**Where:** `golem/core/levels.py:46`.

**What:** The default `levels` is relative, so it resolves against the current directory. Run from
another directory, `list_levels("training")` returns `[]` with no error, because a missing set directory is
an empty set by design.

**Failure scenario:** `uv run golem-server` started outside the repository serves no levels, and nothing
says why.

**Home:** v2.1, where the server first reads `.env`. Resolve `GOLEM_LEVELS_DIR` once at startup and refuse
to start when the directory or `budgets.toml` is missing. The tests already pass `root` explicitly.

### 5. 🟡 `from_json` accepts states that contradict themselves — DEFER → backlog

**Where:** `golem/core/world.py:198`.

**What:** It accepts:
- `status: "playing"` with `steps >= step_budget`;
- `"solved"` with a box off a goal;
- `"playing"` with every box on a goal.

**Failure scenario:** such a state restores, and the next move ends it in a way real play never would.

**Home:** backlog. `from_json` reads only what `to_json` wrote: traces store commands, and the human game's
state stays in the server. Revisit if a later phase reads saved worlds from outside.

### 6. 🟡 A BOM or CR-only line ends give a confusing error — DEFER → v7.1

**Where:** `golem/core/levels.py:68` (`read_text(encoding="utf-8")`) and `golem/core/level.py:49`.

**What:** A UTF-8 BOM shows up as `unknown character '﻿'` at line 1, column 1. CR-only line ends (old
Mac files) collapse the level into one line, which then fails as "not closed".

**Home:** v7.1, which imports published level sets.
- Read with `utf-8-sig`.
- Treat a lone `\r` as a line end.

### 7. 🟡 `load_level` with a non-string id — DEFER → v2.1

**Where:** `golem/core/levels.py:58`.

**What:** `load_level(5)` raises `AttributeError` from `.split`.

**Failure scenario:** a JSON message with a numeric level id reaches `load_level` and fails as an internal
error instead of "unknown level".

**Home:** v2.1, whose WebSocket `load` message is the first outside input. Validate the type there, or
make `load_level` refuse non-strings as `UnknownLevel`.

### 8. 🟡 The direction offsets are defined twice — DEFER → cleanup (/simplify)

**Where:** `golem/core/level.py:15` and `golem/core/world.py:17`.

**What:** The flood fill uses `DIRECTIONS`, and the rules use `OFFSETS`. Both are correct today and must
stay in step.

**Home:** cleanup. Build one from the other.

## What's solid

- **One core:** every rule is in `golem/core/world.py`, and `tests/test_core_imports.py` keeps the core on
  the standard library (an AST check, which a temporary `fastapi` import made fail).
- **Determinism:**
  - `to_json` writes a fixed key order with sorted boxes, and `render` walks rows and columns in order;
  - the listing is sorted;
  - the flood fill reports the same escape cell every run;
  - the only randomness in the tests is `random.Random(<int>)`.
- **Rules coverage:** every rule has its own test, including the corner rule in all four corners from both
  push directions, on and off a goal, and the solved > deadlock > steps precedence at the edge of the
  budget.
- **Ids are never paths:** `load_level` checks the id's shape and the listing before it opens anything, and
  `UnknownLevel` never echoes a path.
- **The phase-1 "done when":** every recorded solution replays to `solved` twice with identical JSON, and
  save, restore and continue matches an uninterrupted run over 60 seeded sequences that end in every
  status except solved (the solutions cover solved).

## Suggested next actions

1. Fix #1, #2 and #3, each in its own commit with its regression test (none for #3), and push.
2. Release v1 as `1.3.0` (`/release-version 1.3.0`, run by `/ship-phase`).
3. Carry #4 and #7 into v2.1's issues, #6 into v7.1's, #5 to the backlog, and #8 to a `/simplify` pass.
