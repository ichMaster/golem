# Roadmap — Golem

Eight self-contained versions, one for each phase of the concept, built in order: **v1** Game core (the level format, the rules, save and replay) → **v2** Prototype (a text game screen over the server's WebSocket, Lua programs run step by step, programs run from the page, the program swap) → **v3** Game screen (the "Clay and stone" design: the screen's data, the scene and the panels, the motion) → **v4** Interpreter (the full sandbox and the run report, then the stops and the snapshot) → **v5** Validator and journal (the HTTP API and the `golem` CLI, the validator and the journal, replay on the screen) → **v6** Agent (the orchestrator and the isolated workspace, then Scribe) → **v7** Experiments (tiers two and three and the hidden sets, then the metrics) → **v8** Several agents (several robots, messages between programs, the agents' channel, cooperative levels).

Phases inside a version are numbered `vA.B` (A = version, B = phase). Each phase lists a **Goal**, a short description, a **Tasks** list, a **Definition of Done (DoD)**, and the **Tests** that encode its DoD (see [ARCHITECTURE.md](ARCHITECTURE.md) §Testing and CI). Phases are built strictly in file order, and each one builds on the previous one's real code. Each version's DoD includes the concept's "done when" criterion for that phase.

**Versioning (`A.B.C`).** `A` = roadmap version (v1→1 … v8→8), `B` = phase within it, `C` = a post-release fix. A release covers the phases built since the previous release and takes the number of the last of them: v1.1–v1.3 shipped together are `1.3.0` (tag `v1.3.0`), and a release of one phase `vA.B` is `A.B.0`. A fix after a release bumps `C`. Never bump a version without explicit confirmation.

Many DoD items need a person or a live model: playing levels on the game screen, swapping a program by hand, watching a replay, and every live Scribe session, which spends the owner's Claude subscription. Those are **Manual (owner)** checks: the owner performs or confirms them, and only then do they count as passed. Everything automated runs with no network and no model: the server and the CLI are tested in-process, lupa runs for real (it is local and deterministic), and the agent is a fake script.

**The riskiest steps come first.** Whether lupa can run a program one robot command at a time (v2.3), and how a swap starts a new program from the current world state (v2.5), decide how `memory` and the interpreter are built. So v2 is a prototype of the whole loop, from a person's arrow keys to a program swapped in mid-level, with the cheapest client: a text page.
- Nothing in v2 is polished beyond what its DoD asks.
- The designed screen (v3) and the full interpreter (v4) are built only after v2.5 has proven the swap design.
- The prototype's code is real code in its final modules. v4 extends it and does not rewrite it.

---

## Status

v1 and v2.1–v2.3 are built and released. Latest release: v2.3.0 (v2.3).

| Phase | Title | Status | Release |
|---|---|---|---|
| v1.1 | Project skeleton and the level format | ✅ released | v1.3.0 |
| v1.2 | World state and the rules | ✅ released | v1.3.0 |
| v1.3 | Save, restore and replay | ✅ released | v1.3.0 |
| v2.1 | The server and the human game over WebSocket | ✅ released | v2.1.0 |
| v2.2 | The text game screen | ✅ released | v2.2.0 |
| v2.3 | Lua runs: the lupa spike, a minimal sandbox and the driver | ✅ released | v2.3.0 |
| v2.4 | Programs on the text screen | ✅ released | v2.4.0 |
| v2.5 | The swap prototype: `memory` outside the program | ⏳ planned | — |
| v3.1 | The screen's data from the server, and ten levels | ⏳ planned | — |
| v3.2 | The game screen: the scene and the panels | ⏳ planned | — |
| v3.3 | The game screen: motion, the atlas and small windows | ⏳ planned | — |
| v4.1 | The full sandbox and the run report | ⏳ planned | — |
| v4.2 | Stops and the snapshot | ⏳ planned | — |
| v5.1 | The HTTP API and the `golem` CLI | ⏳ planned | — |
| v5.2 | The validator and the journal | ⏳ planned | — |
| v5.3 | Replay on the game screen | ⏳ planned | — |
| v6.1 | The orchestrator and the isolated workspace | ⏳ planned | — |
| v6.2 | Scribe: plan, program, run, diagnosis | ⏳ planned | — |
| v7.1 | Tiers two and three, and the hidden sets | ⏳ planned | — |
| v7.2 | Metrics per version | ⏳ planned | — |
| v8.x | Several agents (outline; phases fixed after v7) | ⏳ planned | — |

## v1 — Game core: the level format, the rules, save and replay

The world and the Sokoban rules as pure Python with no dependencies and no graphics. Everything later (the human game, the interpreter, the validator, replays) calls this core and never re-implements a rule. Depends on: nothing; this is the foundation.

### v1.1 — Project skeleton and the level format

**Status:** ✅ released in v1.3.0.

**Goal:** a uv project with green gates locally and in CI, and levels read from the standard Sokoban text format.

The first code: the package, the gates, CI, and the level parser with its validation. The level layout and the budgets file are fixed here, because every later phase loads levels by id.

**Tasks:**
- `pyproject.toml` (uv, Python 3.12+, package `golem`, no runtime dependencies; dev dependencies `ruff`, `pytest`), `uv.lock`, `.env.example` (`GOLEM_LEVELS_DIR`), and `.gitignore` additions: `.env`, `data/`, `levels/hidden/*` except `levels/hidden/README.md`, `reports/`.
- `.github/workflows/ci.yml`: on every push and pull request, `uv sync --frozen`, `uv run ruff check .`, `uv run pytest`. No secrets.
- `golem/core/level.py`: `parse_level(text, level_id) -> Level`, using the character table, comments and ragged rows from ARCHITECTURE §World and rules. Validation: exactly one robot, at least one box, as many goals as boxes, a closed map (a flood fill from the robot never leaves the map). Every error names the line and the column.
- `golem/core/levels.py`: list a set's level ids (`training/tier1/t1-01` …) and load a level by id. An id is checked against the directory listing and never used as a raw path.
- `levels/budgets.toml` (step and instruction budget per tier), `levels/README.md` (the format, the tiers, and the source and licence of each level), `levels/hidden/README.md` (what belongs there and why it is not committed), and three tier-one training levels.

**DoD:**
- `uv run ruff check .` and `uv run pytest` are green locally and in CI.
- Every committed level parses, and a malformed level gives an error with its line and column.
- `golem.core` imports nothing outside the standard library.

**Tests:** unit tests cover the parser over every cell character, comments, ragged rows and each validation error; listing and loading by id, including the refusal of an unknown id or one that contains `..`; loading every committed level; and a test that `golem/core` imports only the standard library.

### v1.2 — World state and the rules

**Status:** ✅ released in v1.3.0.

**Goal:** moves and pushes follow classic Sokoban, every step is counted, and the corner rule loses the level.

**Tasks:**
- `golem/core/world.py`: a frozen `World` holding the level, the robot cell, the box cells, the step count, the status and the loss reason. Functions: `new_world(level, budget)`, `move(world, dir) -> (World, bool)`, `look(world, dir)`, `here(world)`, `boxes_left(world)`, `render(world)`.
- Pushes: one box, only into floor or a goal with no box; never a pull.
- Steps: every `move` counts one, moved or not. The step budget comes from the level's tier, and exhausting it ends the level as lost on steps.
- The corner rule, checked after every push: a box on a non-goal cell with walls on two orthogonal sides ends the level as lost on deadlock.
- Solved when every box is on a goal. No move is applied after the level is solved or lost.

**DoD:**
- The rules in ARCHITECTURE §World and rules hold in unit tests, case by case.
- `look` returns exactly `wall`, `box`, `goal`, `box_on_goal` or `empty`, and `here` returns `goal` or `empty`.

**Tests:** unit tests cover a move onto floor, a goal and a wall; a push onto floor and onto a goal; a refused push into a wall or into another box; a step counted on a failed move; the step budget; the corner rule in all four orientations, on a goal (no loss) and off a goal (loss); the win; no move after the end; and `render` round-tripping a level's text.

### v1.3 — Save, restore and replay

**Status:** ✅ released in v1.3.0.

**Goal:** a world state can be saved and restored exactly, and a recorded sequence of moves always produces the same final state.

**Tasks:**
- `to_json(world)` and `from_json(data, level)`, with sorted box cells so that the JSON is identical for identical states.
- `golem/core/replay.py`: `replay(level, moves, budget)` for a move string such as `"NNESW"`, returning the final world and the per-step states.
- `state_key(world)` for repeat detection (used in v4.2).
- Recorded solutions for the committed training levels in `tests/fixtures/solutions/<level>.txt`.

**DoD** (the concept's phase 1):
- A recorded sequence of moves always produces the same final state: each recorded solution replays to `solved`, twice, with identical JSON.
- Saving, restoring and continuing gives the same final state as playing the same moves without interruption.

**Tests:** unit tests cover the JSON round trip; replay of every recorded solution to `solved`; save, restore and continue against an uninterrupted run over seeded random move sequences; and `state_key` equality and inequality.

## v2 — Prototype: a text game screen, Lua runs, programs on the screen and the program swap

The whole loop at its smallest, each part only as large as it must be to prove that it works:
- a person plays the training levels with the arrow keys on a text page, over the server's WebSocket;
- a hand-written Lua program drives the robot through the same core;
- the owner runs programs from a folder on the text page and watches the robot's moves;
- a second program, swapped in mid-level, finishes the level with the `memory` that the first one built.

This version introduces the server process that every later client reaches. The designed screen comes in v3 and the full interpreter in v4. Depends on: v1.

### v2.1 — The server and the human game over WebSocket

**Status:** ✅ released in v2.1.0.

**Goal:** one server process holds a human game and applies arrow-key moves through the core.

**Tasks:**
- Add the dependencies `fastapi`, `uvicorn` and `python-dotenv`.
- `golem/server/app.py`: `create_app()`, run as `uv run golem-server` on `GOLEM_HOST:GOLEM_PORT` (`127.0.0.1:8700`).
- `GET /api/levels`: training level ids with their tier, size and budgets. The same route serves `golem levels` in v5.1.
- WebSocket `/ws` with the messages from ARCHITECTURE §HTTP API and the `golem` CLI: `load`, `move`, `restart` → `state`. A bad message gets an `error` reply and the connection stays open. Hidden ids are refused.
- The server log in `data/logs/server.log` (rotating), plus `.env.example` additions.

**DoD:**
- A scripted WebSocket client (in tests) loads a level, moves, and receives states whose steps, status and map match the core.
- A hidden id, an unknown id and a malformed message each get an `error` reply.
- (Manual, owner) `uv run golem-server` starts, and `curl -s http://127.0.0.1:8700/api/levels` lists the training levels. Claude may run this check itself.

**Tests:** `TestClient` WebSocket tests for `load`, `move`, `restart` and every error path; `/api/levels` against the level files; a check that the default bind is `127.0.0.1`.

### v2.2 — The text game screen

**Status:** ✅ released in v2.2.0.

**Goal:** the owner plays the training levels with the arrow keys on a plain text page that the server serves.

A deliberately plain page: no design, no canvas and no animation. It proves the serving, the socket and the reconnect, which the designed screen (v3.2) keeps.

**Tasks:**
- **Serving.** `GET /` answers `golem/screen/index.html`, and `/screen/…` serves the files under `golem/screen/` with their content types and nothing outside that directory. The files are found through the package, not the working directory.
- **The page.** `golem/screen/index.html` and `screen.js`: plain HTML and JavaScript, with no framework, no build step, no CDN and no rules in JavaScript. It shows:
  - the map as text in a `<pre>`, exactly as the state's `map`;
  - the level id, `steps / budget`, and the status with its reason: solved, lost on steps, or lost on deadlock;
  - the training levels from `GET /api/levels`, one button each, which sends `load`;
  - the key hints, and a line for an `error` reply.
- **Keys.** The arrow keys send `move` and `R` sends `restart`.
- **The socket.** The page connects to `/ws` when it opens and draws every `state` it receives. On a drop it shows "Reconnecting…" and ignores keys without queuing them. It retries at 0.5, 1, 2 and 4 s, then every 5 s, and the server sends the current state on reconnect.
- **The game survives a restart.** The server saves the human game to `data/human-game.json` after every `load`, `move` and `restart`, written atomically, and restores it at start, so a page that reconnects after a server restart finds the game where it was. Only a training level restores; a save that does not restore is logged without its contents, and the server starts with no game.

**DoD** (the concept's phase 2, first part):
- (Manual, owner) The owner passes t1-01 … t1-03 by hand on the page.
- (Manual, owner) A push into a corner shows lost on deadlock, and running out of steps shows lost on steps.
- (Manual, owner) When the server restarts, the page shows that it is reconnecting, then continues the game where it was.

**Tests:**
- `GET /` and every file the page references are served with their content types;
- a path outside `golem/screen/` gets 404, encoded traversal included;
- no file under `golem/screen/` references an external URL;
- a game saved by one server is restored by a new server on the same file, ended games included; a save that is not JSON, not a saved game, a hidden or unknown level, or a world that does not fit its level starts with no game and logs no level text; the saved file is byte-identical for the same messages.

### v2.3 — Lua runs: the lupa spike, a minimal sandbox and the driver

**Status:** ✅ released in v2.3.0.

**Goal:** a hand-written Lua program drives the robot through the core one command at a time, within its step and instruction budgets, and every run ends in a short report.

The concept leaves the choice of Lua open, so this phase starts with a spike. Everything after it depends on the spike's answers. The sandbox is minimal but safe from the first line; v4.1 completes it.

**Tasks:**
- **Spike first**, recorded in `specification/implementation/v2.3-lupa-spike.md`. It confirms that:
  - lupa installs from wheels on macOS arm64 and on CI's Linux;
  - `lupa.lua54` coroutines can be driven from Python;
  - count hooks work per coroutine;
  - `max_memory` works;
  - each determinism problem in ARCHITECTURE §Robot language and the sandbox can be reproduced and is removed by its fix. The fixes themselves are built in v4.1.

  If any of these fails, stop and ask the owner to choose the alternative.
- Add the dependency `lupa`, pinned to an exact version, and use `lupa.lua54`.
- `golem/interp/sandbox.py`, the minimal sandbox:
  - create the runtime with `register_eval=False`, `register_builtins=False` and `max_memory=LUA_MAX_MEMORY`;
  - give each program a fresh environment table, never `_G`, holding the robot API, `memory` and only the allowlist names whose behaviour is already deterministic. `pairs`, `tostring`, `string.format`, `table.sort` and `math.random` wait for their deterministic versions in v4.1;
  - load programs as text only (`load(src, "=program", "t", env)`);
  - create one `memory` table per runtime.
- The five robot commands as Lua wrappers that `coroutine.yield({cmd, arg})`.
- `golem/interp/driver.py`, the driver loop from ARCHITECTURE §Execution, budgets and the report:
  - resume the program, apply its command through the core, and resume it with the result;
  - the step budget through the core, and the instruction budget through the count hook with `HOOK_EVERY` and the sentinel budget error;
  - `give_up(reason)`, with the reason cut to 200 characters; a program that returns counts as `give_up("program ended")`;
  - Lua errors, at load and at run time, with their line;
  - a driver exception ends the run as `failed` with `reason: internal`.
- `golem/interp/report.py`: the short report, which holds the run report's `level`, `status`, `reason`, `steps`, `instructions` and `error` (ARCHITECTURE §Execution, budgets and the report). v2.5 and v4.1 add the other fields.
- `golem/local.py`, run as `uv run golem-local run <level> <program.lua>`: runs in-process and prints the report as JSON. It is the hand tool for the interpreter until the `golem` CLI (v5.1).
- Hand-written test programs in `tests/fixtures/programs/`:
  - `t1_solver.lua`, which solves a tier-one level;
  - an infinite loop;
  - a syntax error;
  - a call to `give_up`;
  - a program that calls `error("instruction budget exhausted")` itself.

**DoD** (the concept's phase 2, second part):
- A hand-written program passes a tier-one level: `golem-local run training/tier1/t1-01 tests/fixtures/programs/t1_solver.lua` reports `solved`.
- An infinite loop with no robot command ends as lost on instructions, and the runner survives.
- A syntax error and a run-time error are reported with their line, and `give_up("x")` appears in the report.
- A program's own `error("instruction budget exhausted")` is reported as `failed` on `error`, not as a budget loss.
- Inside a program, `python`, `io`, `os`, `require`, `load`, `debug`, `pcall`, `coroutine`, `next` and `setmetatable` are `nil`, and a bytecode chunk is refused.
- Every fixture program run twice gives byte-identical reports.

**Tests:** driver tests over the fixture programs, with real lupa; the step budget through `move`; the instruction budget, including a loop with no robot command; the names that must be absent and the bytecode refusal; and the run-twice check.

### v2.4 — Programs on the text screen

**Status:** ✅ released in v2.4.0.

**Goal:** the owner picks a Lua program from the `programs/` folder on the text page, reads its code, runs it on a training level, and watches the robot's moves played back step by step, ending with the run report.

The server reads the programs and runs them; the page shows the code and plays back what the server computed. The page still holds no rules: every map it shows comes from the core.

**Tasks:**
- **The folder.** `programs/` at the repository root, committed, holds hand-written example programs, and `GOLEM_PROGRAMS_DIR` (default `programs`) can point elsewhere. A program is a `*.lua` file directly in the folder, named with lowercase letters, digits, `-` and `_`; its first comment line is its description. The examples:
  - `t1_solver.lua`, which solves every tier-one level;
  - an explorer that maps the room and gives up with what it saw;
  - one demonstration of each ending: lost on steps, lost on deadlock, lost on instructions, `give_up`, and a Lua error.
- **The driver records the moves.** A run can return, with its report, the world after each `move`. The maps are the core's `render`.
- **The routes** (a contract):
  - `GET /api/programs`: the programs, sorted by name, each with its name, description and size;
  - `GET /api/programs/{name}`: the program's name and source;
  - `POST /api/programs/{name}/run` with `{"level": "<training id>"}`: the run report and the frames, the starting map first and then one frame per `move`, each with the step, the direction, whether the robot moved, and the map.
  - A name that is not a program in the folder gets `404 not_found`, and nothing outside the folder is read. A hidden or unknown level id gets the same `unknown level` error. A run happens off the event loop, so the human game stays responsive.
- **The page.** A programs panel on the text page:
  - the list of programs; choosing one shows its code with line numbers;
  - a level picker (the training levels) and a Run button;
  - the playback: the run's own map in a `<pre>`, one frame every 150 ms, with the step and the move, and a button that skips to the end;
  - the run report at the end, with the status and its reason worded as on the human game, and the error text with its line;
  - the human game and its keys are unaffected.

**DoD:**
- (Manual, owner) The owner sees the programs in `programs/` on the page and reads the code of each.
- (Manual, owner) `t1_solver.lua` solves t1-01, t1-02 and t1-03, and the owner watches each run step by step.
- (Manual, owner) The demonstration programs show each ending in the report: lost on steps, on deadlock and on instructions, `give_up`, and a Lua error with its line.
- (Manual, owner) A program edited or added in `programs/` shows up after a page reload, without restarting the server.

**Tests:**
- the routes: the list, the source, the run; an unknown name, a name with a path, an encoded path and a name that is not `.lua` get 404; a symlink out of the folder is not read;
- a hidden level id gets the same error as an unknown one, and no line of the fixture hidden level appears in any response;
- the frames: the first is the starting map, each next one follows one `move`, and the last one equals the core's replay of the moves;
- every program in `programs/` runs on every tier-one level and ends in a report, the solver solves them all, and a run twice gives byte-identical JSON;
- the page loads only `/screen/` files and references no external URL.

### v2.5 — The swap prototype: `memory` outside the program

**Status:** ⏳ planned.

**Goal:** a second program, started mid-level from the current world state, finishes the level with the `memory` that the first program built.

A deliberately small phase: prove the swap design before anything is built on it. If the prototype shows that the design in ARCHITECTURE must change, update ARCHITECTURE in this phase, before v3 and v4 build on it.

**Tasks:**
- `golem/interp/run.py`: a `Run` object holding the runtime, the shared `memory` table, the world, the counters and the list of versions.
- `swap(run, source)`:
  - loads the new chunk with a new environment that shares `memory`;
  - drops the old coroutine;
  - installs the count hook on the new coroutine;
  - carries the counters over.
- Two fixture programs: `explore.lua` maps a tier-one level into `memory` and calls `give_up("mapped")`; `finish.lua` reads the map from `memory` and solves the level without exploring.
- The report gains `versions`, the program versions that drove the run.
- `golem-local run <level> <first.lua> --swap <second.lua>`: when the first program gives up or returns, the second one takes over. This lets the owner try the swap before the stops of v4.2.
- A short design note in the phase's execution report: what the prototype confirmed or changed.
- **The swap on the text page** (added at the owner's request on 2026-11-21, during the owner test):
  - the programs panel names an optional second program, "Swap in";
  - `POST /api/programs/{name}/run` takes `{"level", "swap": "<program name>"}`, and swaps the second program in when the first one gives up or returns, as `golem-local --swap` does;
  - the frames mark the swap point, the playback shows it, and the report shows the versions;
  - `explore.lua` and `finish.lua` are also in `programs/`.

**DoD** (the concept's phase 2, third part):
- Running `explore.lua` and then swapping in `finish.lua` solves the level. The step count continues from the swap point, and the old coroutine can no longer be resumed.
- `golem-local run training/tier1/t1-01 tests/fixtures/programs/explore.lua --swap tests/fixtures/programs/finish.lua` reports `solved` with `versions` `[1, 2]`.
- ARCHITECTURE §Stops, snapshots and program swaps matches what the prototype built.
- **Manual (owner):** on the text page, `explore.lua` with `finish.lua` swapped in solves t1-01; the playback marks the swap point and the report shows versions 1 and 2.

**Tests:**
- the explore-then-finish swap;
- the counters carried over;
- the old coroutine dead;
- the instruction hook active after the swap: an infinite loop swapped in ends on the instruction budget;
- `golem-local --swap`;
- the swapped run run twice, with byte-identical reports;
- the program route with a swap: the solve, the swap frame, an unknown or invalid swap program refused, and byte-identical JSON twice.

## v3 — Game screen: the "Clay and stone" design

The text page of v2.2 becomes the designed game screen, on which the owner plays the training levels. Depends on: v2 (the server, the page's serving, its socket and its reconnect).

The screen follows the "Clay and stone" design:
- the brief: [design/game-screen-brief.md](design/game-screen-brief.md);
- the designer's handoff: [design/golem-clay/README.md](design/golem-clay/README.md), whose layout, tokens and motion values are final.

It takes three phases: what the screen needs from the server (v3.1), a playable screen with every panel (v3.2), and its motion and smaller layouts (v3.3).

### v3.1 — The screen's data from the server, and ten levels

**Status:** ⏳ planned.

**Goal:** the server sends the screen everything it draws, and ten training levels exist.

**Tasks:**
- The WebSocket `state` gains `inside`: one string per row of `map`, as long as that row, with `1` for a cell inside the walls and `0` for a cell outside them. It comes from the core's `Level.inside`, so the page draws the floor only there and never computes it.
- A new WebSocket message for the level picker. The client sends `{"type": "levels"}`, and the server answers `{"type": "levels", "levels": [...]}`: one entry per training level, sorted by id, with the fields of `GET /api/levels` plus the start `map` and its `inside`. Hidden levels are never listed.
- `GET /api/levels` keeps its contract and still carries no map. The same route serves `golem levels` (v5.1), and the agent doesn't get a level's map before it runs the level. The screen's channel is the WebSocket, which the agent never uses.
- Ten training levels: the committed t1-01 … t1-03, plus t1-04, t1-05 and t2-01 … t2-05. The sample maps in the design handoff (`GolemClayScreen.dc.html`) are candidates. Each level must parse, have a recorded solution in `tests/fixtures/solutions/`, and fit its tier's budget in `budgets.toml`.
- ARCHITECTURE §HTTP API (the WebSocket contract) records `inside` and `levels`.

**DoD:**
- A scripted WebSocket client receives `inside` with every state and the level list on request, both matching the core and the level files.
- Neither message carries a hidden id or any line of a hidden map, and `GET /api/levels` still carries no map.
- Every recorded solution of the ten levels replays to `solved` through the core.

**Tests:**
- `inside` against `Level.inside` for every training level, at the start and after moves;
- the `levels` reply against the level files, and against a root that holds the fixture hidden level;
- `/api/levels` unchanged;
- the ten solutions replay to `solved`.

### v3.2 — The game screen: the scene and the panels

**Status:** ⏳ planned.

**Goal:** the owner plays the ten training levels on the "Clay and stone" screen. Every state is drawn at once; motion comes in v3.3.

**Tasks:**
- **The files.** `golem/screen/index.html` and `screen.js` replace the text page of v2.2, and `screen.css` joins them. `art/golem-art.js` is the handoff's renderer, trimmed to the clay direction. They are served as v2.2 serves the page. No frameworks, no build step, no CDN, and no rules in JavaScript.
- **The look.** The handoff's tokens become CSS custom properties in `screen.css`. Nocturne's `.btn` and `.seg` classes are copied in without its Google Fonts `@import`. Inter Regular, Medium and SemiBold ship as WOFF2 under `golem/screen/fonts/` with their OFL licence.
- **The scene.** One canvas at the device pixel ratio, drawn in the handoff's order: the room, the tray, the floor where `inside` is set, the runes, the shadows, the walls and blocks, Golem facing the last move, and the light.
  - The static layer is cached per state.
  - The cell size, the board insets and the three levels of detail follow the handoff, in the wide layout (≥ 1200 px).
- **The socket.** The page keeps v2.2's socket and reconnect. On every open it also asks for `levels`.
- **Keys and focus,** as in the handoff's table:
  - the arrows act only while the board has focus, and `event.repeat` is ignored;
  - `R` restarts;
  - the `Tab` order is fixed, and focus rings appear on `:focus-visible` only.
- **The panels:**
  - the picker: tiers and cards with miniatures, with solved marks kept in `localStorage`;
  - the level plate and the step gauge (normal, warning, lost, solved);
  - the key hints;
  - the result panel for solved, lost on steps and lost on deadlock, with the next level;
  - the error notice;
  - the reconnecting overlay;
  - the title screen.
- **What changed.** The page compares the previous state with the new one only to name what happened: a move, a push, a bump, a block onto or off a rune, the stuck block of a deadlock. It never decides whether a move is legal. In this phase the stuck block is marked without animation.

**DoD** (the concept's phase 3):
- (Manual, owner) The owner passes the ten training levels by hand on the screen.
- (Manual, owner) A push into a corner shows lost on deadlock with the stuck block marked, and running out of steps shows lost on steps.
- (Manual, owner) When the server restarts, the screen shows that it is reconnecting, then continues the game where it was.

**Tests:**
- `GET /` and every file the page references are served with their content types;
- no file under `golem/screen/` references an external URL;
- the fonts' licence ships with them.

### v3.3 — The game screen: motion, the atlas and small windows

**Status:** ⏳ planned.

**Goal:** every action on the screen moves as the design specifies, and the screen fits smaller windows.

**Tasks:**
- `art/golem-fx.js`, from the handoff's poses and effects, and a tween scheduler in `screen.js`. Input never waits: a new state snaps the running tween to its end and starts the next one.
- The handoff's motion table:
  - idle and move;
  - push, with the sliding block drawn outside the static layer;
  - bump, with the "+1" chip and the keycap flash;
  - a block onto and off a rune;
  - solved, lost on steps, and lost on deadlock (spotlight, crack, lock);
  - the steps warning, reconnecting and the error notice.
- `prefers-reduced-motion`: only the short fades from the handoff's last column remain.
- The atlas "All levels": a dialog with every tier. `Tab` and the arrows move between cards, `Enter` plays and `Esc` closes.
- The compact layout under 1200 px, where the picker folds into a rail, and the narrow one under 900 px.
- A fixture levels root under `tests/fixtures/` with a 20 × 20 training level (the handoff's large map), for the performance check with `GOLEM_LEVELS_DIR`.

**DoD:**
- (Manual, owner) Every moment of the motion table looks as the handoff specifies, and fast key presses never wait for an animation.
- (Manual, owner) The 20 × 20 board holds 60 fps on the MacBook, and the screen works at 1024 × 700 and at 800 px wide.
- (Manual, owner) With "Reduce motion" on in macOS, only fades remain.

**Tests:** the fixture root's large level parses and loads over the WebSocket; the served files still reference no external URL.

## v4 — Interpreter: the full sandbox, the run report, the stops and the snapshot

The prototype interpreter of v2.3–v2.5 becomes the full one:
- the complete sandbox, with every determinism fix;
- the full run report;
- the stops. At a stop, the agent continues the program or swaps in a new one that starts from the current world with the same `memory` and the remaining budget. The level never restarts.

Depends on: v2 (the prototype it extends).

### v4.1 — The full sandbox and the run report

**Status:** ⏳ planned.

**Goal:** a program sees exactly the allowlist in ARCHITECTURE, the same program always behaves the same way, and the run report is complete.

**Tasks:**
- `golem/interp/sandbox.py` completes the environment allowlist from ARCHITECTURE §Robot language and the sandbox:
  - the deterministic `pairs`;
  - the merge-sort `table.sort`;
  - the address-free `tostring` and the `string.format` wrapper;
  - `math.random` seeded with `RANDOM_SEED`, with no `math.randomseed`;
  - the `string` library without `string.dump`, which is also the strings' `__index`.
- The memory cap: a program that allocates past `LUA_MAX_MEMORY` ends with a report entry, never with the runner.
- `golem/interp/report.py` completes the run report with `last_actions` (the last `LAST_ACTIONS_N`) and `final_map`, pinned by a contract test.
- Fixture programs for the escape attempts and for determinism.

**DoD:**
- Every global outside the allowlist is `nil` inside a program, and none of these escape attempts succeeds: `python`, `io.open`, `os.time`, `require`, `load`, `string.dump` (also as `("").dump`), `debug`, `pcall`, `coroutine`, `next`, `setmetatable`, or loading a bytecode chunk.
- The same program run in two fresh runtimes gives identical results, including over `pairs`, `table.sort` on more than 100 elements, `tostring` and `string.format` of a table, and `math.random`.
- A program past the memory cap ends with a report entry, and the runner survives.
- Every fixture program run twice gives byte-identical reports.

**Tests:**
- an allowlist test that lists the environment;
- one test per escape attempt;
- the `pairs` order over mixed keys;
- `table.sort` stability and fixed instruction count;
- `tostring` and `string.format` of a table;
- seeded `math.random`;
- the memory cap;
- the report shape (a contract test);
- the run-twice check.

### v4.2 — Stops and the snapshot

**Status:** ⏳ planned.

**Goal:** the interpreter pauses on the events the agent switched on, hands over a snapshot, and continues or swaps on request.

**Tasks:**
- `golem/interp/stops.py`: the five stops (`error`, `deadlock`, `give_up`, `half_budget`, `repeat`), each with its `continue` and `swap` rules and its behaviour when switched off, as in the ARCHITECTURE table. `half_budget` fires once per run; `repeat` keys on `state_key` plus the canonical `memory`.
- `golem/interp/snapshot.py`: the snapshot JSON and the `memory` conversion (arrays and objects, number keys, functions, cycles, the `SNAPSHOT_MEMORY_MAX_BYTES` cap).
- `continue` and `swap` on a stopped run. An illegal request (continuing after `error`, swapping after `deadlock`) is refused with a clear error.
- `golem-local` gains `--stop-on` and becomes interactive at stops: it prints the snapshot and reads `continue`, `swap <file>` or `quit` from standard input.

**DoD** (the concept's phase 4):
- (Manual, owner) With `golem-local`, a program that maps a level and gives up is swapped by hand for one that finishes the level using the old map.
- Each stop fires exactly when specified, and never when switched off.

**Tests:** one test per stop, both firing and switched off; `continue` and `swap` legality for every stop; the snapshot shape (a contract test); the `memory` conversion edge cases; and an automated version of the manual DoD that drives the same stop and swap through the `Run` object.

## v5 — Validator and journal: the HTTP API and the CLI, the validator, replay

The game becomes reachable from the shell. Every program version and every run is kept, one command validates a program over all levels, and any run can be replayed. Depends on: v4.

### v5.1 — The HTTP API and the `golem` CLI

**Status:** ⏳ planned.

**Goal:** the commands `levels`, `run`, `state`, `continue` and `swap` work from the shell, and every response is JSON.

**Tasks:**
- `golem/server/api.py`: the routes from ARCHITECTURE §HTTP API and the `golem` CLI for these five commands. Runs live in the server, with one open run per session; the session comes from `X-Golem-Session` (or is `manual`). Errors use `{"error", "detail"}` with 4xx statuses, and `run` refuses hidden ids.
- Add the dependencies `typer` and `httpx`.
- `golem/cli.py`, run as `uv run golem`: each command is one request to `GOLEM_URL`. The CLI reads program files and sends their text, applies the `GOLEM_WORKSPACE` path restriction when it is set, prints JSON, and uses exit codes 0, 1 and 2.
- `.env.example` additions.

**DoD:**
- From a shell against a running server: `golem levels`; `golem run training/tier1/t1-01 explore.lua --stop-on give_up` → a snapshot; `golem state` → the same snapshot; `golem swap finish.lua` → a report with `solved`.
- A stopped server gives exit code 2 and a JSON error, not a traceback.
- With `GOLEM_WORKSPACE` set, a program path outside it (including through a symlink or `..`) is refused.

**Tests:** API tests with `TestClient`; CLI tests through an httpx ASGI transport (no port) for each command, the exit codes and the path restriction; the error shapes (a contract test).

### v5.2 — The validator and the journal

**Status:** ⏳ planned.

**Goal:** one command gives a report for all levels, every program version is kept with its reason, and the hidden levels are seen only as passed or failed.

**Tasks:**
- `golem/journal/db.py`: the SQLite schema from ARCHITECTURE §Validator and journal; transactions; and closing runs that are still open as `abandoned` at startup.
- Program versions per session: SHA-256 deduplication, the `--reason` stored, and a new version without a reason refused after the first one.
- `golem/journal/traces.py`: traces written atomically when a run closes; hidden traces go to `data/traces/hidden/`.
- `golem/journal/validator.py` and `golem validate <program> [--reason]`: every training and hidden level with every stop off; full training reports; hidden levels as passed or failed only; summaries per set and tier.
- `golem versions` and `golem show <n>`.
- The owner routes `POST /api/sessions` and `POST /api/sessions/{id}/close` behind `GOLEM_OWNER_TOKEN`, with the version limit (`409 version_limit`) enforced for sessions that have one.
- Hidden levels: `GOLEM_HIDDEN_DIR`, and three tier-one hidden levels written by the owner (gitignored); fixture hidden levels in `tests/fixtures/hidden/` for the tests.

**DoD** (the concept's phase 5, first half):
- One command gives a report for all levels: `golem validate t1_solver.lua --reason "first"` returns full reports for the training levels and only passed or failed for the hidden ones.
- `golem versions` lists the versions with their reasons, and `golem show 1` returns the first version's source.
- No API response contains any part of a hidden level's text.
- (Manual, owner) The owner writes the three hidden tier-one levels and confirms that `golem validate` reports them as passed or failed only.

**Tests:**
- the journal schema (a contract test);
- version deduplication and the missing-reason refusal;
- atomic trace writing;
- validation against fixture training and hidden sets;
- **the hidden-leak test**: every route is run against a fixture hidden level, and no part of its text may appear in any response;
- the owner routes, which answer 401 without the token;
- the version limit, which answers 409;
- abandoned runs closed at startup.

### v5.3 — Replay on the game screen

**Status:** ⏳ planned.

**Goal:** any training run can be replayed on the game screen.

**Tasks:**
- `GET /api/runs` (training runs, newest first) and `GET /api/runs/{id}/frames`: the server rebuilds every world state from the trace through the core. A hidden run answers 404.
- A replay mode in the screen: a run picker, play, pause, single steps, speed, a timeline with stops and swaps marked, the list of actions, and the robot's view (cells seen so far; the rest greyed out).
- The replay follows the replay sketch in the design handoff ([design/golem-clay/README.md](design/golem-clay/README.md)), whose layout v3.2 already leaves room for. The frames come with the level's `inside`, as the WebSocket state does.

**DoD** (the concept's phase 5, second half):
- Any run can be replayed: the frames rebuilt from a trace end in the state that the run's report records.
- (Manual, owner) The owner replays a run that had a stop and a swap, and sees both marked on the timeline.

**Tests:** frames rebuilt for traces with and without swaps; the final frame equals the report's final map and counters; a hidden run gives 404; the static files still reference no external URL.

## v6 — Agent: the orchestrator, the isolated workspace, Scribe

The agent appears, as a separate process that reaches the game only through `golem`. The orchestrator and the isolation are proven with a fake agent first, so that the first live session already runs with its isolation verified. Depends on: v5.

### v6.1 — The orchestrator and the isolated workspace

**Status:** ⏳ planned.

**Goal:** an agent process runs in its own workspace, sees the game only through `golem`, and stops at its limits. This is proven first with a fake agent and no model.

**Tasks:**
- `golem/orchestrator/`, run as `uv run golem-orchestrate --set <set> [--max-versions N] [--max-minutes M] [--agent-cmd …]`. It follows the steps in ARCHITECTURE §The agent and its isolation:
  - open the session through the owner route;
  - create the workspace in `GOLEM_WORKSPACES`, outside the repository (refuse a path inside it);
  - write the workspace files and `.claude/settings.json` with the tool rules;
  - build a clean environment (no `GOLEM_OWNER_TOKEN`, no `ANTHROPIC_*`) with `golem` on `PATH`;
  - launch the agent command in its own process group;
  - write the stream log, kill the process group at the time limit, and close the session with its end reason.
- A fake agent for the tests, `tests/fixtures/fake_agent.py`, which runs scripted `golem` commands.
- `.env.example` additions.

**DoD:**
- With the fake agent, the workspace layout, the environment and the tool-rules file are as specified; the version limit reaches the agent as `409 version_limit`; the time limit kills the agent's process group; and the session closes with the right reason.
- (Manual, owner) A live Claude Code session in a fresh workspace is asked to read `levels/hidden/`, to read the repository's `CLAUDE.md`, to run `curl` and to fetch a web page. Every attempt is refused, and `golem levels` works.

**Tests:** orchestrator tests with the fake agent (layout, environment, limits, kill, end reasons); the generated `.claude/settings.json` (a contract test); the refusal of a workspace path inside the repository.

### v6.2 — Scribe: plan, program, run, diagnosis

**Status:** ⏳ planned.

**Goal:** Scribe passes the tier-one training levels without hints.

**Tasks:**
- `agents/scribe/CLAUDE.md`, Scribe's instructions, as listed in ARCHITECTURE §The agent and its isolation. They contain the rules and the API but no strategy for any level and no program.
- `agents/scribe/task.md`: the task prompt that the orchestrator passes, naming the level set and the limits.
- `SCRIBE_MODEL` passed as `--model` when set.
- A session summary in the journal when the session closes: versions used, the best validation, the time spent, the end reason.

**DoD** (the concept's phase 6):
- (Manual, owner) The agent passes the tier-one training levels without hints: a live session on `training/tier1` ends with every level passing in `golem validate`, and the journal shows the versions with their reasons.
- The workspace contains only what the orchestrator put there and what Scribe wrote. There is no hand-written program and no hint.

**Tests:** a cross-check that `agents/scribe/CLAUDE.md` names every robot command and every CLI command exactly as the contracts do, so that the instructions cannot drift from the code; the orchestrator passes the task prompt and `--model`; the session summary is written from a fixture journal.

## v7 — Experiments: harder levels, hidden sets and metrics

Find where the agent stops coping, and show it in numbers. Depends on: v6.

### v7.1 — Tiers two and three, and the hidden sets

**Status:** ⏳ planned.

**Goal:** training and hidden level sets for all three tiers, every level proven solvable.

**Tasks:**
- Training levels for tiers 2 and 3, with recorded solutions in `tests/fixtures/solutions/`. The source and licence of every level go in `levels/README.md`.
- Hidden levels for tiers 1 to 3, written or chosen by the owner, with their solutions kept beside them (gitignored).
- `uv run golem-levels check [--hidden]`: an owner tool that replays each level's solution through the core and reports any level that is not solved, without printing the hidden levels' text.
- Budgets per tier reviewed in `levels/budgets.toml`.

**DoD:**
- Every tier has training and hidden levels (the counts are agreed with the owner when the phase starts).
- Every training level's recorded solution replays to `solved` in the tests.
- (Manual, owner) `golem-levels check --hidden` reports every hidden level as solvable.

**Tests:** recorded solutions of all training levels; `golem-levels check` over fixture levels, including an unsolvable one; a check that the tool never prints a hidden level's text.

### v7.2 — Metrics per version

**Status:** ⏳ planned.

**Goal:** a metrics table that shows where the agent stops coping.

**Tasks:**
- `golem/metrics.py`, run as `uv run golem-metrics [--session S …]`: an owner tool that reads the journal directly. For each session and version it reports:
  - training levels passed per tier;
  - the share of hidden levels passed;
  - the regressions (levels that passed in the previous version and fail now);
  - the average steps per passed level;
  - the versions needed to reach the best result;
  - the number of hidden validations.
- The table is written to `reports/metrics-<date>.md` and printed.
- Experiment sessions: the owner runs Scribe on tiers 1, 2 and 3 with agreed limits.

**DoD** (the concept's phase 7):
- (Manual, owner) A metrics table exists that shows where the agent stops coping: sessions on all three tiers, with the four numbers from the concept per version.
- The metrics are computed from the journal alone and are the same when run twice.

**Tests:** metrics over a fixture journal (passes, regressions, averages, hidden validations); a session with no validation; the markdown table's shape.

## v8 — Several agents: robots that cooperate

Several robots on one level, each with its own agent, program and `memory`. They talk at two levels: their programs exchange short messages during a run, and the agents negotiate at stops. Depends on: v7.

This version is an **outline**. Its phases are fixed, with full tasks and tests, after v7, when the metrics show what a single agent can do.

### v8.1 — Several robots in the core and on the screen

**Status:** ⏳ planned (outline).

**Goal:** a level with several robots, played by the core in a fixed turn order. A robot is a wall to the others. The format numbers the robots in reading order. The screen draws every robot.

### v8.2 — Messages between programs

**Status:** ⏳ planned (outline).

**Goal:** `send(msg)` and `receive()` in the robot language. Both are yields. Messages are plain, size-capped data, delivered on the receiver's next turn, and they are deterministic.

### v8.3 — The agents' channel and the orchestrator for several agents

**Status:** ⏳ planned (outline).

**Goal:** one session per agent, each with its own workspace, program and `memory`, plus a shared channel through which agents agree at stops who takes which box and who rewrites their program.

### v8.4 — Cooperative levels and the two-agent experiment

**Status:** ⏳ planned (outline).

**Goal** (the concept's phase 8): two agents pass a level that a single robot cannot, on levels where one robot has to clear the way for the other.
