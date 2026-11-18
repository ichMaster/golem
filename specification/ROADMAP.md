# Roadmap — Golem

Eight self-contained versions, one for each phase of the concept, built in order: **v1** Game core (the level format, the rules, save and replay) → **v2** Game for a human (the server's WebSocket, the game screen) → **v3** Robot language and interpreter (the Lua sandbox, step-by-step execution and budgets) → **v4** Stops and program swap (the swap prototype first, then the stops and the snapshot) → **v5** Validator and journal (the HTTP API and the `golem` CLI, the validator and the journal, replay on the screen) → **v6** Agent (the orchestrator and the isolated workspace, then Scribe) → **v7** Experiments (tiers two and three and the hidden sets, then the metrics) → **v8** Several agents (several robots, messages between programs, the agents' channel, cooperative levels).

Phases inside a version are numbered `vA.B` (A = version, B = phase). Each phase lists a **Goal**, a short description, a **Tasks** list, a **Definition of Done (DoD)**, and the **Tests** that encode its DoD (see [ARCHITECTURE.md](ARCHITECTURE.md) §Testing and CI). Phases are built strictly in file order, and each one builds on the previous one's real code. Each version's DoD includes the concept's "done when" criterion for that phase.

**Versioning (`A.B.C`).** `A` = roadmap version (v1→1 … v8→8), `B` = phase within it, `C` = a post-release fix. A release covers the phases built since the previous release and takes the number of the last of them: v1.1–v1.3 shipped together are `1.3.0` (tag `v1.3.0`), and a release of one phase `vA.B` is `A.B.0`. A fix after a release bumps `C`. Never bump a version without explicit confirmation.

Many DoD items need a person or a live model: playing levels on the game screen, swapping a program by hand, watching a replay, and every live Scribe session, which spends the owner's Claude subscription. Those are **Manual (owner)** checks: the owner performs or confirms them, and only then do they count as passed. Everything automated runs with no network and no model: the server and the CLI are tested in-process, lupa runs for real (it is local and deterministic), and the agent is a fake script.

**The riskiest step is v4.** How a swap starts a new program from the current world state decides how `memory` and the interpreter are built. So v4.1 is a bare prototype of the swap, built right after v3, and nothing in v2 or v3 is polished beyond what its DoD asks before v4.1 has proven the design.

---

## Status

v1 and v2.1 are built and released. Latest release: v2.1.0 (v2.1).

| Phase | Title | Status | Release |
|---|---|---|---|
| v1.1 | Project skeleton and the level format | ✅ released | v1.3.0 |
| v1.2 | World state and the rules | ✅ released | v1.3.0 |
| v1.3 | Save, restore and replay | ✅ released | v1.3.0 |
| v2.1 | The server and the human game over WebSocket | ✅ released | v2.1.0 |
| v2.2 | The game screen | ⏳ planned | — |
| v3.1 | The Lua sandbox (with the lupa spike) | ⏳ planned | — |
| v3.2 | Step-by-step execution, budgets and the run report | ⏳ planned | — |
| v4.1 | The swap prototype: `memory` outside the program | ⏳ planned | — |
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

## v2 — Game for a human: the server's WebSocket and the game screen

A human plays the training levels with the arrow keys, through the same core the robot will use. This version introduces the server process that every later client reaches. Depends on: v1.

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

### v2.2 — The game screen

**Status:** ⏳ planned.

**Goal:** the owner plays the training levels with the arrow keys.

**Tasks:**
- `golem/screen/index.html`, `screen.js` and `screen.css`, served at `/`. A canvas draws walls, floor, goals, boxes, boxes on goals and the robot. The arrow keys send moves, `R` restarts the level, and a picker loads a level. The page shows the step count against the budget and a solved or lost banner with the reason, and it reconnects when the WebSocket drops.
- No frameworks, no build step, no CDN, and no rules in JavaScript: the page sends keys and draws the states it receives.
- Ten training levels across tiers 1 and 2, with recorded solutions in `tests/fixtures/solutions/`.

**DoD** (the concept's phase 2):
- (Manual, owner) The owner passes ten training levels by hand on the screen.
- (Manual, owner) A push into a corner shows lost on deadlock, and running out of steps shows lost on steps.
- Every recorded solution replays to `solved` through the core.

**Tests:** the page and its assets are served; the static files reference no external URL; the recorded solutions of all ten levels replay to `solved`.

## v3 — Robot language and interpreter: the Lua sandbox, execution and budgets

A Lua program drives the robot one command at a time, inside a sandbox, within its budgets, and every run ends in a report. Depends on: v1. (v2 is not needed by the interpreter, but it comes first in the build order.)

### v3.1 — The Lua sandbox (with the lupa spike)

**Status:** ⏳ planned.

**Goal:** a Lua program runs in a sandbox that offers only the robot API, `memory` and safe Lua, and the same program always behaves the same way.

The concept leaves the choice of Lua open, so this phase starts with a spike. Everything after it depends on the spike's answers.

**Tasks:**
- **Spike first**, recorded in `specification/implementation/v3.1-lupa-spike.md`. It confirms that:
  - lupa installs from wheels on macOS arm64 and on CI's Linux;
  - `lupa.lua54` coroutines can be driven from Python;
  - count hooks work per coroutine;
  - `max_memory` works;
  - each determinism problem in ARCHITECTURE §Robot language and the sandbox can be reproduced and is removed by its fix.

  If any of these fails, stop and ask the owner to choose the alternative.
- Add the dependency `lupa`, pinned to an exact version.
- `golem/interp/sandbox.py`:
  - create the runtime with `register_eval=False`, `register_builtins=False` and `max_memory=LUA_MAX_MEMORY`;
  - build the environment allowlist;
  - add the deterministic `pairs`, the merge-sort `table.sort`, the address-free `tostring`, and `math.random` seeded with `RANDOM_SEED`;
  - load programs as text only (`load(src, "=program", "t", env)`);
  - create one `memory` table per runtime.
- The five robot commands as Lua wrappers that `coroutine.yield({cmd, arg})`.

**DoD:**
- Every global outside the allowlist is `nil` inside a program, and none of these escape attempts succeeds: `python`, `io.open`, `os.time`, `require`, `load`, `string.dump`, `debug`, `pcall`, `coroutine`, `next`, `setmetatable`, or loading a bytecode chunk.
- The same program run in two fresh runtimes gives identical results, including over `pairs` and `table.sort` on more than 100 elements.

**Tests:** an allowlist test that lists the environment; one test per escape attempt; the `pairs` order over mixed keys; `table.sort` stability and fixed instruction count; `tostring` of a table; seeded `math.random`; and the memory cap.

### v3.2 — Step-by-step execution, budgets and the run report

**Status:** ⏳ planned.

**Goal:** a program drives the robot through the core one command at a time, within its step and instruction budgets, and every run ends in a report.

**Tasks:**
- `golem/interp/driver.py`, the driver loop from ARCHITECTURE §Execution, budgets and the report:
  - resume the program, apply its command through the core, resume with the result;
  - the count hook with `HOOK_EVERY` and the sentinel budget error;
  - `give_up(reason)`, with a program that returns treated as `give_up("program ended")`;
  - Lua errors with their line;
  - a driver exception ending the run as `failed` with `reason: internal`.
- `golem/interp/report.py`: the run report (status, reason, steps, instructions, error, the last `LAST_ACTIONS_N` actions, the final map, versions).
- `golem/local.py`, run as `uv run golem-local run <level> <program.lua>`: runs in-process with every stop off and prints the report as JSON. It is the hand tool for this version, and its output matches the later `golem run`.
- Hand-written test programs in `tests/fixtures/programs/`: one solving a tier-one level, one infinite loop, one with a syntax error, one calling `give_up`, and one that calls `error("instruction budget exhausted")` itself.

**DoD** (the concept's phase 3):
- A hand-written program passes a tier-one level: `golem-local run training/tier1/t1-01 tests/fixtures/programs/t1_solver.lua` reports `solved`.
- An infinite loop ends as lost on instructions, and the server process (here, the runner) survives.
- A syntax error and a run-time error are reported with their line, and `give_up("x")` appears in the report.
- A program's own `error("instruction budget exhausted")` is reported as `failed` on `error`, not as a budget loss.
- Every fixture program run twice gives byte-identical reports.

**Tests:** driver tests over the fixture programs; the step budget through `move`; the instruction budget, including a loop with no robot command; the report shape (a contract test); and the determinism check.

## v4 — Stops and program swap: the prototype first, then the stops

The level never restarts: at a stop, the agent continues the program or swaps in a new one that starts from the current world with the same `memory` and the remaining budget. This version decides how `memory` and the interpreter are built, so its first phase is a prototype. Depends on: v3.

### v4.1 — The swap prototype: `memory` outside the program

**Status:** ⏳ planned.

**Goal:** a second program, started mid-level from the current world state, finishes the level with the `memory` that the first program built.

A deliberately small phase: prove the swap design before anything is built on it. If the prototype shows that the design in ARCHITECTURE must change, update ARCHITECTURE in this phase, before v4.2.

**Tasks:**
- `golem/interp/run.py`: a `Run` object holding the runtime, the shared `memory` table, the world, the counters and the list of versions.
- `swap(run, source)`: loads the new chunk with a new environment that shares `memory`, drops the old coroutine, installs the count hook on the new one, and carries the counters over.
- Two fixture programs: `explore.lua` maps a tier-one level into `memory` and calls `give_up("mapped")`; `finish.lua` reads the map from `memory` and solves the level without exploring.
- A short design note in the phase's execution report: what the prototype confirmed or changed.

**DoD:**
- Running `explore.lua` and then swapping in `finish.lua` solves the level. The step count continues from the swap point, and the old coroutine can no longer be resumed.
- ARCHITECTURE §Stops, snapshots and program swaps matches what the prototype built.

**Tests:** the explore-then-finish swap; counters carried over; the old coroutine dead; the instruction hook active after the swap; and determinism of the swapped run (run twice, identical traces).

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
