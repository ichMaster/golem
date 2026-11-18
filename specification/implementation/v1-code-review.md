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
| 1 | 🟠 MEDIUM | `from_json` accepts a robot or box outside the walls, and the robot can then walk off the map | FIX NOW | ✅ FIXED — 7462ba0 |
| 2 | 🟡 LOW | The parser accepts boxes and goals the robot can never reach, so an unsolvable level loads | FIX NOW | ✅ FIXED — 3f143e1 |
| 3 | 🟡 LOW | Documentation drift: the layout omits `levels.py`; ROADMAP §v1.3 shows the old `replay` signature | FIX NOW | ✅ FIXED — 6b2e8d5 |
| 4 | 🟡 LOW | `levels_root()` resolves `levels` against the working directory; from elsewhere the listing is silently empty | DEFER → v2.1 | ⏳ deferred |
| 5 | 🟡 LOW | `from_json` accepts states that contradict themselves (playing past the budget, solved with a box off a goal) | DEFER → backlog | ⏳ deferred |
| 6 | 🟡 LOW | A level file with a UTF-8 BOM or CR-only line ends gives a confusing error | DEFER → v7.1 | ⏳ deferred |
| 7 | 🟡 LOW | `load_level` with a non-string id raises `AttributeError`, not `UnknownLevel` | DEFER → v2.1 | ⏳ deferred |
| 8 | 🟡 LOW | The direction offsets are defined twice (`level.DIRECTIONS`, `world.OFFSETS`) | DEFER → cleanup (/simplify) | ⏳ deferred |

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

## Fixes applied

All three fixes are on `v1-dev`. After the last one: lint clean, 272 tests green, and CI green on 7462ba0,
3f143e1 and 6b2e8d5.

### #1 — `from_json` keeps the robot and the boxes inside the walls (7462ba0)

- **Change:**
  - the parser's flood fill now returns the robot's area, kept as `Level.inside`;
  - `_saved_cell` refuses a cell that is a wall ("is a wall") or that is not in `inside` ("is outside the
    map"), instead of checking only the bounding box.
- **Regression tests:**
  - `tests/test_world_json.py::test_from_json_refuses_a_cell_outside_the_walls`: the robot and the boxes,
    on two cells beyond the ragged level's walls and two beyond its bounds;
  - `tests/test_level.py::test_inside_holds_the_robots_area_and_nothing_outside_the_walls`.
- **Verification:** against the old code, the new test fails on the four cells beyond the walls (the
  out-of-bounds ones were already refused). With the fix, 270 tests passed.

### #2 — unreachable boxes and goals are a `LevelError` (3f143e1)

- **Change:** after the flood fill, the first box, then the first goal, outside `inside` (in row and
  column order) raises a `LevelError` at its own cell.
- **Regression tests:**
  - `tests/test_level.py::test_a_goal_outside_the_walls_is_an_error` (line 1, column 4);
  - `tests/test_level.py::test_a_box_in_a_sealed_pocket_is_an_error` (line 2, column 6).

  Both fail against the old parser. The three committed training levels still parse.
- **Verification:** 272 tests passed.

### #3 — documentation drift (6b2e8d5)

- **Change:**
  - ARCHITECTURE §Repository layout lists `levels.py` under `golem/core/`;
  - ROADMAP §v1.3 shows `replay(level, moves, budget)`.
- **Regression test:** none; the change is documentation only.

## Architecture impact

- **`Level.inside`** is a new field of the level (ARCHITECTURE §World and rules, the `parse_level` line). It
  holds every non-wall cell the robot's start reaches without crossing a wall; a robot or a box can only
  ever stand in it. v2.1's screen and v3.2's interpreter can rely on it.
- **Level validity** (a contract) gained one rule: every box and goal lies in the robot's area. A box or
  goal outside it is a `LevelError` at its own cell. This matters for the owner's hidden levels (v5.2),
  which have no recorded solution.
- **`from_json`** refuses robot and box cells outside `inside`, as ARCHITECTURE.md already promised for
  "outside the map".

## Suggested next actions

1. Release v1 as `1.3.0` with `/release-version 1.3.0`, run by `/ship-phase v1`.
2. Carry the deferred findings into their homes:
   - #4 (resolve `GOLEM_LEVELS_DIR` once at server start, and fail loudly) and #7 (a non-string level id)
     go into v2.1's issues;
   - #6 (BOM and CR-only line ends) goes into v7.1's;
   - #5 (self-contradicting saved states) goes to the backlog;
   - #8 (one definition of the direction offsets) goes to a `/simplify` pass.
