# Architecture — Golem

## Overview

One server process and three kinds of client. **The Golem server** is the only process that knows the rules and the world. It holds the game core, the interpreter that runs robot programs, the validator and the journal. **The game screen** is a browser page that draws the world and sends arrow keys over a WebSocket. **The `golem` CLI** turns commands into HTTP requests, and it is the only way the agent reaches the game. **The orchestrator** launches the agent (Scribe, Claude Code in non-interactive mode) in its own workspace and enforces its limits. Everything runs on the owner's Mac. The only outbound connection is Claude Code's own, to Anthropic.

The parts arrive along the roadmap: the core (v1), then the server's WebSocket and the screen (v2), the interpreter (v3), stops and swaps (v4), the HTTP API, the CLI, the validator and the journal (v5), the orchestrator and Scribe (v6), level sets and metrics (v7), and several robots and agents (v8).

```
┌─ the owner's Mac ──────────────────────────────────────────────────────────────┐
│                                                                                │
│  ┌──────────────────────┐  WebSocket /ws  ┌──────────────────────────────────┐ │
│  │ browser: game screen ├────────────────►│ Golem server · 127.0.0.1:8700    │ │
│  │ arrows · replay      │                 │ FastAPI + uvicorn                │ │
│  └──────────────────────┘                 │                                  │ │
│                                           │ /ws ──────────────────┐          │ │
│  ┌──────────────────────┐  HTTP /api      │ /api ─► interpreter ──┤          │ │
│  │ golem CLI            ├────────────────►│   │     (lupa) ▲      ▼          │ │
│  │ Typer + httpx        │  JSON           │   └─► validator┘  game core      │ │
│  └──────────▲───────────┘                 │          │                       │ │
│             │ Bash: golem …               │          ▼                       │ │
│  ┌──────────┴───────────┐                 │ journal  data/journal.sqlite     │ │
│  │ Scribe: claude -p    │                 │          data/traces/*.json      │ │
│  │ cwd = its workspace  │                 │ levels   training/ · hidden/     │ │
│  └──────────▲───────────┘                 └──────────────────────────────────┘ │
│             │ launches · limits                                                │
│  ┌──────────┴───────────┐                                                      │
│  │ orchestrator         │                                                      │
│  └──────────────────────┘                                                      │
└─────────────┬──────────────────────────────────────────────────────────────────┘
              │ HTTPS :443 outbound (Claude Code only)
      ┌───────▼────────────────┐
      │ Anthropic              │
      │ (owner's subscription) │
      └────────────────────────┘
```

Human moves arrive over `/ws` and go straight to the core. Program commands arrive over `/api`, go through the interpreter, and reach the same core. The validator runs the interpreter over level sets and writes the results to the journal.

## Network, ports and protocols

| From | To | Protocol / port | Purpose |
|---|---|---|---|
| Browser (game screen) | server | HTTP + WebSocket, `127.0.0.1:8700` | the page, the world state, arrow keys, replays |
| `golem` CLI | server | HTTP, `127.0.0.1:8700`, JSON | the agent's commands (and the owner's, by hand) |
| Orchestrator | server | HTTP, `127.0.0.1:8700`, Bearer `GOLEM_OWNER_TOKEN` | opens and closes sessions |
| Orchestrator | Claude Code | local subprocess | launches Scribe and reads its output stream |
| Claude Code (Scribe) | Anthropic | HTTPS :443, outbound | the model, on the owner's subscription |
| Developer (Mac) | GitHub | HTTPS :443 / SSH, outbound | `git push` triggers CI |
| **Inbound from the network** | — | **nothing** | the server binds `127.0.0.1` only |

There are no other listeners and no other outbound connections. The game itself never calls the internet.

## Tech stack

| Technology | Used by | Purpose |
|---|---|---|
| Python 3.12+ with uv | everything except the screen | one language; dependencies pinned in `pyproject.toml` and `uv.lock` |
| Python standard library only | game core | rules with no dependencies, testable on their own |
| FastAPI + uvicorn | server | the HTTP API and the WebSocket in one process |
| lupa, Lua 5.4 runtime (`lupa.lua54`) | interpreter | the sandbox, coroutines and `debug.sethook`. Lua is the concept's choice, confirmed or replaced in the v3.1 spike |
| Typer + httpx | `golem` CLI | a thin wrapper that turns commands into HTTP requests and prints JSON |
| `sqlite3` (standard library) | journal | sessions, versions, runs and validations, with no database server |
| JSON files | traces | one file per run |
| HTML + canvas + plain JavaScript | game screen | no frameworks, no build step, no CDN |
| Claude Code (`claude -p`) | Scribe | can already write files and call shell commands |
| `subprocess` (standard library) | orchestrator | launches Claude Code and enforces the limits |
| ruff + pytest | gates | lint and tests, with no network and no model |
| GitHub Actions | CI | the gates on every push and pull request |

## Components

- **Game core** (`golem/core/`, v1). Pure Python with no dependencies and no I/O beyond reading level text. It parses levels, holds an immutable world state, applies moves and pushes, counts steps, detects the corner deadlock and the win, saves and restores the state, and replays move sequences. Human moves, program commands, the validator and replays all go through it. The rules exist nowhere else.
- **Server** (`golem/server/`, v2.1 and v5.1). A FastAPI app built by `create_app()` and run by uvicorn on `GOLEM_HOST:GOLEM_PORT` (`127.0.0.1:8700`). It serves the game screen's files, the WebSocket `/ws` for the human game and replays, and the HTTP API under `/api` for the CLI. The routes are thin: they parse input, call the core, the interpreter or the journal, and shape the JSON output.
- **Game screen** (`golem/screen/`, v2.2 and v5.3). One HTML page, one script and one stylesheet, served by the server at `/`. A canvas draws the grid. The arrow keys send moves over `/ws`. A level picker, a step counter and a solved/lost banner complete the human game, and a replay mode plays back recorded runs. The page draws what the server sends and contains no game rules.
- **Interpreter** (`golem/interp/`, v3 and v4). One Lua runtime per run, holding the sandbox environment, the `memory` table and the step and instruction counters. A Python driver resumes the program's coroutine, applies each robot command through the core, checks the stop conditions, and builds snapshots and run reports. Swapping a program loads a new chunk into the same runtime.
- **Validator and journal** (`golem/journal/`, v5.2). The validator runs one program over the training and hidden sets with every stop off. The journal stores sessions, program versions (with the reason for each change), runs and validations in SQLite, and every run's trace as a JSON file.
- **`golem` CLI** (`golem/cli.py`, v5.1). Typer + httpx. Each command is one HTTP request, and every response is printed as JSON. It reads program files from disk and sends their text, never their paths.
- **Local runner** (`golem/local.py`, v3.2 and v4.2). `uv run golem-local` drives the interpreter in-process, with no server. It is the developer's and the owner's hand tool for v3 and v4, and it prints the same report and snapshot JSON that `golem` prints later.
- **Orchestrator** (`golem/orchestrator/`, v6.1). Opens a session on the server, prepares the agent's workspace outside the repository, launches the agent with a clean environment and tool rules, kills it at the time limit, keeps its output stream, and closes the session.
- **Scribe** (`agents/scribe/`, v6.2). The agent's instructions (`CLAUDE.md`) and task prompt. The orchestrator copies them into each workspace. Scribe itself is Claude Code; the repository holds only its instructions.
- **Levels** (`levels/`). Text files in the standard Sokoban format: training levels committed, hidden levels gitignored, budgets per tier in `levels/budgets.toml`.
- **Storage** (`data/`, gitignored). The journal, the traces, the orchestrator's session logs and the server log.

## World and rules

The rules are classic Sokoban. Every rule below is implemented once, in `golem/core/`.

**Level format.** One level per `.txt` file, in the standard Sokoban text format:

| Character | Cell |
|---|---|
| `#` | wall |
| space, `-` or `_` | floor |
| `$` | box |
| `.` | goal |
| `*` | box on a goal |
| `@` | robot |
| `+` | robot on a goal |

Lines that start with `;` are comments, and blank lines before and after the map are ignored. Rows may differ in length; a cell past the end of a row is outside the map. A level is valid when it has exactly one robot, at least one box, as many goals as boxes, walls that close it, so that the robot cannot walk off the map (a flood fill from the robot over every non-wall cell never leaves the map), and every box and goal inside the area that fill covers, since walls never move and anything outside it can never be reached. A parse error (`LevelError`) names the level id, the line and the column, both counted from 1 in the file's own lines, comment lines included. An error about the whole level, such as a missing robot or unequal counts, names the first map line, column 1; a second robot is named at its own cell, an open map at the last cell inside it, and a box or goal the robot cannot reach at its own cell.

**Rules.**

1. The robot moves one cell north, east, south or west (`N`, `E`, `S`, `W`). A move into a wall changes nothing and returns `false`. A move onto floor or a goal moves the robot and returns `true`.
2. A move into a box pushes it when the cell behind the box, in the same direction, is floor or a goal with no box on it. The box moves there and the robot moves into the box's old cell. Otherwise nothing moves and the move returns `false`. The robot pushes one box at a time and never pulls one.
3. Every move counts one **step**, whether or not anything moved. A human arrow press counts the same.
4. The level is **solved** when every box stands on a goal.
5. The level is **lost** when the step budget is exhausted, when the instruction budget is exhausted (programs only), or when a push leaves a box on a cell that is not a goal and has walls on two orthogonal sides (north and east, east and south, south and west, or west and north). This **corner rule** is the only deadlock the game detects. Every other dead position is the program's problem.
6. After the level is solved or lost, no move is applied.

**Level ids.** A level's id is `<set>/<tier>/<name>`, for the file `<levels root>/<set>/<tier>/<name>.txt`, where the levels root is `GOLEM_LEVELS_DIR` (`levels`). Each part matches `[a-z0-9][a-z0-9-]*`, and the tier is `tier<N>`. A set's listing holds every such file, sorted by id; other files and directories are ignored. A level is loaded only by an id that appears in its set's listing, never by a path built from the id, and any other id is refused as unknown (`UnknownLevel`).

**Budgets.** Each level has a step budget and an instruction budget, set per tier in `levels/budgets.toml`. The human game uses the step budget only. The file holds one table per tier, named `tier<N>`, with exactly two keys, both positive integers:

```toml
[tier1]
steps = 200
instructions = 1_000_000
```

A missing key, an unknown key, or a value that is not a positive integer is an error (`BudgetsError`) that names the tier and the key.

**The core's interface** works on plain data. A cell is a `(row, column)` pair counted from 0, where row 0 is the first map line after comments.

- `parse_level(text, level_id) -> Level`: an immutable level with its size, walls, goals, starting boxes and robot cell, and `inside`: every non-wall cell the robot's start reaches without crossing a wall (boxes do not block it), the only cells a robot or a box can ever occupy.
- `World`: a frozen dataclass with the level, the robot cell, the box cells (a frozenset), the step count, the step budget, the status (`playing`, `solved` or `lost`) and the loss reason (`None`, `steps` or `deadlock`; the interpreter sets `instructions`). `new_world(level, budget)` starts a level with the step budget of its tier, which `budget_for(level_id, budgets)` looks up; a level whose boxes all start on goals is solved at once.
- `move(world, dir) -> (World, bool)`, `look(world, dir) -> str`, `here(world) -> str`, `boxes_left(world) -> int`. A direction other than `N`, `E`, `S` or `W` is a `ValueError`. After a move on a playing world, the world is solved if every box is on a goal, otherwise lost on `deadlock` if the push triggered the corner rule, otherwise lost on `steps` if the step count has reached the budget. A move on a solved or lost world changes nothing, returns `false` and counts no step.
- `render(world) -> list[str]`: the current map as Sokoban text lines, which is the report's final map.
- `to_json(world)` and `from_json(data, level)` save and restore a state.
- `replay(level, moves, budget)` applies a move string such as `"NNESW"` from the level's start, and `play(world, moves)` from any world. Both return the final world and the list of states: the starting world first, then the world after each move. A character other than `N`, `E`, `S` or `W` is a `ValueError` naming its position, counted from 1, raised before any move is applied.
- `state_key(world)`: the robot cell and the sorted box cells, used for repeat detection. It ignores the step count.

**The saved world** (a contract) is plain JSON data with its keys in this order and its boxes sorted, so that equal states give byte-identical JSON:

```json
{"level": "training/tier1/t1-01", "robot": [2, 3], "boxes": [[2, 4]], "steps": 1,
 "step_budget": 200, "status": "playing", "loss_reason": null}
```

`from_json` restores it onto the level it names and refuses, with a `ValueError` naming the field, anything inconsistent: another level, a missing or unknown key, a wrong type, a robot or box on a wall or outside the map (not in the level's `inside`), two boxes in one cell, the robot on a box, a box count other than the level's, a negative step count, a non-positive step budget, an unknown status, or a `loss_reason` that doesn't fit the status.

Every collection that reaches JSON is serialized in sorted order, so that the output never depends on Python's set or dict ordering.

## Robot language and the sandbox

A program is Lua 5.4 text and runs in a sandbox that offers only the robot API, `memory` and a fixed allowlist of Lua functions.

**The robot API** (a contract; the strings are exact):

| Command | What it does | Returns |
|---|---|---|
| `move(dir)` | one step in `"N"`, `"E"`, `"S"` or `"W"`; pushes a box if the cell behind it is free | `true` or `false` |
| `look(dir)` | looks at the neighbouring cell in that direction | `"wall"`, `"box"`, `"goal"`, `"box_on_goal"` or `"empty"` |
| `here()` | looks at the robot's own cell | `"goal"` or `"empty"` |
| `boxes_left()` | counts the boxes not yet on goals | an integer |
| `give_up(reason)` | ends the program; the reason (a string, cut to 200 characters) goes into the report | does not return |

An invalid direction is a Lua error. The robot never learns its absolute position: a program that wants coordinates keeps its own, relative to where it started. Only `move` costs a step. All five commands cost instructions, like any other Lua code.

**The runtime.** One `LuaRuntime` per run, created with `register_eval=False` and `register_builtins=False`, so that Lua has no `python` module, and with `max_memory=LUA_MAX_MEMORY`. No Python object is ever passed into Lua; the driver exchanges only strings, numbers, booleans and Lua tables with the program. Programs are loaded with `load(source, "=program", "t", env)`. The mode `"t"` accepts text only and refuses precompiled bytecode.

**The environment.** A program's globals are a fresh table, never `_G`. It contains:

- the robot API and `memory`;
- `assert`, `error`, `ipairs`, `pairs`, `select`, `tonumber`, `tostring`, `type` and `unpack` (an alias of `table.unpack`);
- the `string`, `table` and `math` libraries, without `string.dump` and `math.randomseed`.

Nothing else is reachable. In particular there is no `io`, `os`, `require`, `package`, `debug`, `load`, `loadstring`, `dofile`, `loadfile`, `pcall`, `xpcall`, `coroutine`, `next`, `rawget`, `rawset`, `rawequal`, `rawlen`, `setmetatable`, `getmetatable`, `collectgarbage` or `print`. The reasons for the less obvious entries:

- No `pcall` or `xpcall`. The budget error must end the program; a program that could catch it would run forever.
- No `coroutine`. Robot commands yield to the driver; a program with its own coroutines could intercept those yields.
- No `next` and no metatables. Raw iteration order is not deterministic (see below), and a metatable on `memory` would make it more than plain data.
- No `print`. A program reports through `memory`, which the snapshot shows, and through `give_up(reason)`.

**Determinism inside Lua.** Lua 5.4 has four sources of run-to-run variation, and the sandbox removes each one:

| Source | Fix in the sandbox |
|---|---|
| The order of `pairs` depends on a per-runtime string-hash seed | `pairs` iterates in a fixed order: numbers ascending, then strings in byte order, then `false`, `true`. A table used as a key is a Lua error. `next` is not exposed |
| `table.sort` picks a random pivot on arrays longer than 100 | `table.sort` is a stable merge sort written in Lua, so its result and its instruction count are fixed |
| `tostring` of a table or function prints a memory address | `tostring` returns `"table"` or `"function"` for those types |
| `math.random` is seeded randomly when the runtime starts | the driver seeds it with `RANDOM_SEED` when the run starts; `math.randomseed` is not exposed |

Instruction counts depend on the Lua version's bytecode, so the lupa version and the `lupa.lua54` runtime are pinned. Changing either is a contract change.

## Execution, budgets and the report

**The driver.** Every robot command is a Lua wrapper that calls `coroutine.yield({cmd, arg})`. The Python driver resumes the program's coroutine, receives the command, applies it through the core, records the action, checks for the end of the level and for the stops, and resumes the coroutine with the result. A Python function called from Lua cannot yield, which is why the commands are Lua wrappers and the work happens in the driver.

```
load the program → coroutine
loop:
    resume(coroutine, last result) → a command, or the program ended, or a Lua error
    apply the command through the core → result; record the action
    solved or lost?  → close the run and build the report
    a stop that is switched on?  → pause and build the snapshot
```

**The instruction budget.** The driver sets a count hook on the program's coroutine with `debug.sethook(co, hook, "", HOOK_EVERY)`; the `debug` library exists in the runtime but not in the program's environment. Every `HOOK_EVERY` instructions (1000), the hook adds to the run's counter. When the counter reaches the budget, the hook raises an error whose value is a unique sentinel table that only the driver holds. Because the program has no `pcall`, the error ends the coroutine, and the driver recognizes the sentinel and ends the level as lost on instructions. A program that calls `error("instruction budget exhausted")` itself produces an ordinary Lua error, not a loss. Counts are accurate to `HOOK_EVERY`. The hook is installed again on every new coroutine after a swap, and the counter is carried over.

**The end of a program.** A program that returns without solving the level is treated as `give_up("program ended")`. A Lua error, including a syntax error at load time, carries its message and line number.

**The run report** (a contract) is built when a level ends:

```json
{
  "level": "training/tier1/t1-03",
  "status": "lost",
  "reason": "deadlock",
  "steps": 140,
  "instructions": 52000,
  "error": null,
  "last_actions": [{"n": 140, "cmd": "move", "arg": "E", "result": true}],
  "final_map": ["#######", "#  @$ #", "#######"],
  "versions": [5, 7]
}
```

- `status` is `solved`, `lost` (with `reason` = `steps`, `instructions` or `deadlock`), `failed` (the program ended with its stop switched off: `reason` = `error` or `give_up`, with the text in `error`) or `abandoned` (the agent left the run at a stop).
- `last_actions` holds the last `LAST_ACTIONS_N` (20) robot commands with their results.
- `versions` lists the program versions that drove the run.

For a hidden level the report is only `{"level": "hidden/tier2/h-07", "passed": false}`.

## Stops, snapshots and program swaps

**Stops.** The agent chooses which events pause a run (`--stop-on`, by default all five):

| Stop | Fires when | `continue` | `swap` | With the stop switched off |
|---|---|---|---|---|
| `error` | a Lua error, at load or at run time | no: the program is dead | yes | the run ends `failed` |
| `deadlock` | a push breaks the corner rule | no | no: the level is lost | the run ends `lost` with no snapshot |
| `give_up` | the program calls `give_up(reason)`, or returns | no | yes | the run ends `failed` |
| `half_budget` | half the step budget is spent while `boxes_left()` still equals its value at the start of the level; fires once per run | yes | yes | no pause |
| `repeat` | after a step, the robot cell, the box cells and the canonical `memory` all equal those after an earlier step of the run | yes | yes | no pause |

A `deadlock` stop is terminal. It exists so that the agent gets the snapshot (`memory` and the latest actions) together with the report. Including `memory` in the `repeat` key is deliberate: a robot that returns to the same cell while still adding to its map is exploring, not looping. A program that counts steps in `memory` never triggers `repeat`, and the step budget and `half_budget` catch it instead.

**The snapshot** (a contract) is what the agent gets at a stop, and what `golem state` returns:

```json
{
  "run": "r-000123",
  "level": "training/tier1/t1-03",
  "status": "stopped",
  "stop": {"event": "give_up", "detail": "no path to the box"},
  "version": 7,
  "remaining": {"steps": 412, "instructions": 1830000},
  "boxes_left": 1,
  "memory": {"map": {"0,0": "empty", "0,1": "wall"}, "x": 3, "y": -1},
  "last_actions": [{"n": 88, "cmd": "look", "arg": "N", "result": "wall"}],
  "can": ["swap"]
}
```

The snapshot has no map and no robot position: the agent sees the world only as the program saw it. `memory` is converted to JSON as follows:

- A table whose keys are exactly 1..n becomes an array; any other table becomes an object, with number keys written as strings.
- A function, or any other value that is not data, becomes the string `"<function>"` (or the type's name in angle brackets).
- A table seen twice becomes `"<cycle>"`.
- The result is cut at `SNAPSHOT_MEMORY_MAX_BYTES`, with `"memory_truncated": true` added.

The conversion is only for display. The Lua table itself is never rebuilt from JSON.

**Swap.** `swap(source)` loads the new program into the same runtime with a new environment that shares the same `memory` table. The old coroutine is dropped and can never be resumed. The world, the step and instruction counters and the stop that fired once (`half_budget`) all carry over. The level never restarts. Each program that drives a run is recorded with its version number, and the trace marks every swap.

**Lifetime of a run.** One session has at most one open run. A run closes when it is solved or lost, when a program fails with its stop switched off, or as `abandoned` when the agent starts a new run while this one is stopped. The Lua state cannot be saved, so a run that is open when the server stops is lost: at the next start, the journal closes it as `abandoned`.

## Validator and journal

**`validate(program)`** runs the program on every training level and every hidden level, each from its start, with every stop switched off, one level after another. A training level gets its full report and a hidden level only `passed` or `failed`, plus a summary of passed out of total for each set and tier. Because the run is deterministic, validating the same version twice gives the same result.

**Program versions.** Every distinct program text that a session sends through `run`, `swap` or `validate` becomes a version. Versions are numbered from 1 per session and deduplicated by their SHA-256, so sending the same text again reuses its number. The CLI's `--reason` text is stored with a new version. After a session's first version, a new version without a reason is refused, because the reason is what makes a rollback meaningful. `golem versions` lists the versions with their reasons and their latest validation, and `golem show <n>` prints one version's source. A rollback is simply running an older version's text again.

**The journal schema** (a contract), in `data/journal.sqlite`:

| Table | Columns |
|---|---|
| `sessions` | `id`, `agent`, `started_at`, `ended_at`, `max_versions`, `max_minutes`, `status`, `end_reason` |
| `versions` | `session_id`, `n`, `sha256`, `source`, `reason`, `created_at` |
| `runs` | `id`, `session_id`, `kind` (`run` or `validate`), `level`, `level_set` (`training` or `hidden`), `status`, `reason`, `steps`, `instructions`, `versions` (JSON), `started_at`, `ended_at`, `trace` |
| `validations` | `id`, `session_id`, `version_n`, `per_tier` (JSON: passed and total for each set and tier), `created_at` |

Every write is a transaction. Commands that do not come from an orchestrator session belong to the session `manual`, which has no limits.

**Traces.** `data/traces/<run>.json` holds the level id and text, the stops that were switched on, and, in order, every robot command with its result and the counters after it, every stop, and every swap with its version. A trace is written atomically (to a temporary file, then renamed) when the run closes. Hidden runs write their traces to `data/traces/hidden/`, and no API route serves them.

## HTTP API and the `golem` CLI

Every response is JSON. An error is `{"error": "<code>", "detail": "<text>"}` with a 4xx status. The CLI prints the body and exits with 0 on success, 1 on a 4xx error, and 2 when the server cannot be reached.

| Command | Route | Returns | Phase |
|---|---|---|---|
| `golem levels` | `GET /api/levels` | training level ids with their tier, size and budgets | v5.1 (the route since v2.1) |
| `golem run <level> <program> [--stop-on …] [--reason …]` | `POST /api/runs` | a snapshot (stopped) or a run report (ended) | v5.1 |
| `golem state` | `GET /api/runs/current` | the current snapshot, or the last report | v5.1 |
| `golem continue` | `POST /api/runs/current/continue` | a snapshot or a run report | v5.1 |
| `golem swap <program> [--reason …]` | `POST /api/runs/current/swap` | a snapshot or a run report | v5.1 |
| `golem validate <program> [--reason …]` | `POST /api/validate` | training reports, hidden passed/failed, summaries | v5.2 |
| `golem versions` | `GET /api/versions` | the session's versions with reasons and latest validation | v5.2 |
| `golem show <n>` | `GET /api/versions/{n}` | one version's source and reason | v5.2 |

`run` accepts training level ids only, so a hidden level is reachable only through `validate`. The session comes from the `X-Golem-Session` header, which the CLI fills from `GOLEM_SESSION`, or is `manual` when the header is absent. When `GOLEM_WORKSPACE` is set, the CLI reads a program file only if its resolved path, after symlinks, lies inside that directory.

**Routes outside the CLI:**

- `POST /api/sessions` and `POST /api/sessions/{id}/close` are **owner routes**: they need Bearer `GOLEM_OWNER_TOKEN` and are used only by the orchestrator.
- `GET /api/runs` and `GET /api/runs/{id}/frames` serve the screen's replay (v5.3). They list and rebuild training runs only, and answer `404` for a hidden run. A training trace holds nothing that the run report does not already give the agent.

**WebSocket `/ws`** (a contract). The client sends:

- `{"type": "load", "level": "<id>"}`, for training ids only;
- `{"type": "move", "dir": "N"}`;
- `{"type": "restart"}`.

The server answers each message with `{"type": "state", "level": …, "map": […], "steps": n, "budget": n, "status": "playing" | "solved" | "lost", "reason": …}`, or with `{"type": "error", "detail": …}`, and the connection stays open. The server holds one human game at a time.

## The agent and its isolation

**The orchestrator** (`uv run golem-orchestrate --set training/tier1 [--max-versions N] [--max-minutes M]`):

1. Opens a session on the server through the owner route, with the limits.
2. Creates the workspace `GOLEM_WORKSPACES/<session>/` (by default `~/golem-workspaces/`) **outside the repository**. Claude Code reads every `CLAUDE.md` from its working directory up to the file-system root, so a workspace inside the checkout would give the agent the project's own instructions. The workspace receives `agents/scribe/CLAUDE.md`, a `.claude/settings.json` with the tool rules, and an empty `programs/` directory, and nothing else.
3. Launches the agent with the working directory set to the workspace, using `claude -p "<task prompt>" --output-format stream-json` (the command is configurable, so that tests can use a fake agent). The environment carries `GOLEM_URL`, `GOLEM_SESSION`, `GOLEM_WORKSPACE` and a `PATH` that contains `golem`. It never carries `GOLEM_OWNER_TOKEN`, `ANTHROPIC_API_KEY` or any other `ANTHROPIC_*` variable, so Claude Code runs on the owner's subscription and cannot open its own sessions.
4. Writes the agent's output stream to `data/sessions/<session>/agent.jsonl`. At `max_minutes` it kills the agent's whole process group.
5. Closes the session with its end reason (done, time limit, version limit, agent error). The workspace is kept.

**The version limit** is enforced by the server: past `max_versions`, a command that would create a new version gets `409 version_limit`, which the agent sees as an ordinary command result.

**The tool rules** in the workspace's `.claude/settings.json` (a contract, pinned by a test of the generated file):

- allow `Bash(golem:*)`, and `Read`, `Write`, `Edit`, `Glob` and `Grep` inside the workspace;
- deny `WebFetch` and `WebSearch`.

In non-interactive mode a tool call that needs a permission nobody can grant is refused, so anything outside the allowlist fails: another shell command, a file outside the workspace, the web.

**Scribe's instructions** (`agents/scribe/CLAUDE.md`, v6.2) contain:

- the world and the rules, the robot API and the sandbox's limits;
- the `golem` commands and the shapes of the snapshot and the report;
- the loop: plan, then program, then run, then diagnosis from the report;
- the table of reactions from the concept, which maps a problem in the report to the depth of the rewrite;
- the file discipline: `PLAN.md` for the strategy, `programs/vNNN.lua` for each version (never overwritten), `NOTES.md` for diagnoses, and a `--reason` on every new version;
- when to finish: every training level passes, the program has been validated, then stop.

**Layers of isolation.** Each layer holds on its own:

1. The API never returns a hidden map, a hidden trace or the live world state. Only the snapshot and the report leave the server.
2. `run` refuses hidden ids, and `validate` reports hidden levels only as passed or failed.
3. The CLI reads programs only inside the workspace and sends text, never paths.
4. The agent's tools reach only the workspace and only the `golem` command.
5. The hidden levels, the journal and the traces live in gitignored paths of the repository, outside the workspace, and are never committed.

## The game screen

The page draws the map that the server sends: walls, floor, goals, boxes, boxes on goals and the robot. It shows the step count against the budget and the status with its reason. Keys: the arrows move, `R` restarts the level, and a picker loads a training level. The page holds no rules. It never decides whether a move is legal; it sends the key and draws the state that comes back.

**Replay** (v5.3) asks the server for a training run's frames (`GET /api/runs/{id}/frames`). The server rebuilds every world state from the trace through the core, so the page still holds no rules. The page offers play, pause, single steps and speed, a timeline with the stops and swaps marked, the list of actions, and the robot's view: the cells the robot has seen so far, with the rest greyed out. Hidden runs cannot be replayed.

## Contracts

Changing any of these updates this document (and `concept.en.md` where it states the same thing) and the test that pins it, in the same commit:

- The level text format, the level id scheme `<set>/<tier>/<name>`, and the `levels/budgets.toml` schema.
- The rules: move and push semantics, the step definition, the corner rule, the win condition.
- The robot API: the five commands, their arguments and their exact return values.
- The sandbox: the environment allowlist, the fixed `pairs` order, the stable `table.sort`, `tostring`, the seeded `math.random`, text-only loading, and the pinned lupa version and Lua runtime.
- The stop events, their `continue` and `swap` rules, and the `--stop-on` names.
- The JSON shapes of the snapshot, the run report, the hidden result and the error body, plus the CLI's exit codes.
- The HTTP routes, the CLI commands with their arguments, and the WebSocket messages.
- The journal schema and the trace format.
- The variable names in `.env.example`.
- The workspace layout, the agent's environment, and the tool rules in `.claude/settings.json`.

## Data and state files

Nothing that a run produces is deleted. `data/`, `reports/`, `levels/hidden/` (except its `README.md`) and `.env` are gitignored.

| Path | Written | Content |
|---|---|---|
| `levels/training/tier{1,2,3}/*.txt` | by hand, committed | training levels |
| `levels/hidden/tier{1,2,3}/*.txt` | by the owner, gitignored | hidden levels with opaque names |
| `levels/budgets.toml` | by hand, committed | step and instruction budgets per tier |
| `levels/README.md` | by hand, committed | the format, the tiers, and the source and licence of every level |
| `data/logs/server.log` | the server (v2.1) | the server log, rotating (1 MB × 3) |
| `data/journal.sqlite` | the server (v5.2) | sessions, versions, runs, validations |
| `data/traces/<run>.json` | the server, when a run closes (v5.2) | the trace of a training run |
| `data/traces/hidden/<run>.json` | the server (v5.2) | the trace of a hidden run, never served by the API |
| `data/sessions/<session>/agent.jsonl` | the orchestrator (v6.1) | Claude Code's output stream for the session |
| `GOLEM_WORKSPACES/<session>/` | the orchestrator and the agent (v6.1) | `CLAUDE.md`, `.claude/settings.json`, `PLAN.md`, `programs/`, `NOTES.md` |
| `reports/metrics-<date>.md` | `golem-metrics` (v7.2) | the metrics table |

## Configuration and secrets

All settings live in `.env` (read with python-dotenv) or in `levels/budgets.toml`. Nothing is hard-coded.

| Variable | Phase | Meaning (default) |
|---|---|---|
| `GOLEM_LEVELS_DIR` | v1.1 | the levels root (`levels`) |
| `GOLEM_HOST`, `GOLEM_PORT` | v2.1 | where the server listens (`127.0.0.1` / `8700`) |
| `LUA_MAX_MEMORY` | v3.1 | the Lua memory cap per run, in bytes (64 MiB) |
| `RANDOM_SEED` | v3.1 | the seed of the sandbox's `math.random` (`0`) |
| `HOOK_EVERY` | v3.2 | instructions between two calls of the count hook (`1000`) |
| `LAST_ACTIONS_N` | v3.2 | actions in a report or a snapshot (`20`) |
| `SNAPSHOT_MEMORY_MAX_BYTES` | v4.2 | the cap on `memory` in a snapshot (`65536`) |
| `GOLEM_URL` | v5.1 | where the CLI sends requests (`http://127.0.0.1:8700`) |
| `GOLEM_DATA_DIR` | v5.2 | the journal, traces and logs (`data`) |
| `GOLEM_HIDDEN_DIR` | v5.2 | the hidden levels (`levels/hidden`) |
| `GOLEM_OWNER_TOKEN` | v5.2 | the Bearer token for the owner routes; never in the agent's environment |
| `GOLEM_SESSION` | v5.2 | the session the CLI acts in (set by the orchestrator; otherwise `manual`) |
| `GOLEM_WORKSPACE` | v6.1 | the only directory the CLI reads programs from (set by the orchestrator) |
| `GOLEM_WORKSPACES` | v6.1 | where workspaces are created (`~/golem-workspaces`) |
| `SCRIBE_MAX_VERSIONS`, `SCRIBE_MAX_MINUTES` | v6.1 | the session limits (`30` / `60`) |
| `SCRIBE_MODEL` | v6.2 | Claude Code's `--model` (unset: Claude Code's default) |

The project has no API keys. The things to keep private are `GOLEM_OWNER_TOKEN`, the hidden levels, the journal and the traces. Claude Code's login stays in Claude Code's own configuration, and the project never reads or copies it.

## Security and access

| Threat | Protection |
|---|---|
| The agent reads the hidden levels | gitignored, outside the workspace; tool rules limit file access to the workspace and shell access to `golem`; no web tools; no API route returns a hidden map or a hidden trace; hidden ids are opaque |
| The agent reads the live world state, the journal or the traces | only the snapshot and the report leave the server; `data/` is outside the workspace |
| The agent learns the project's internals | the workspace is outside the repository, so the repository's `CLAUDE.md` and code are never loaded |
| The agent opens its own session or raises its limits | the session routes need `GOLEM_OWNER_TOKEN`, which is never in the agent's environment; the server enforces the version limit |
| A program reaches files, processes, the clock or Python | the environment allowlist; `register_eval=False`, `register_builtins=False`; no Python object enters Lua; text-only `load` |
| A program hangs the server or exhausts its memory | the instruction budget through the count hook, no `pcall`, the runtime's `max_memory`; every failure becomes a report entry |
| A program's own `error(...)` passes for a budget loss | the budget error is a sentinel table, compared by identity |
| A run cannot be reproduced | the sandbox's determinism fixes, a pinned runtime, no clock, sorted serialization; a test runs every fixture program twice and compares the traces |
| The agent is billed to an API key | the orchestrator strips `ANTHROPIC_*` from the agent's environment |
| The agent runs forever or burns the subscription | the time limit kills the process group; the version limit ends new work |
| The agent fits its program to the hidden levels | hidden results are passed or failed only; the metrics count hidden validations per session |
| A hidden level is published | `levels/hidden/` is gitignored; tests use fixture hidden levels in `tests/fixtures/hidden/`; no hidden level text appears in logs, issues or commits |
| Someone on the network uses the server | it binds `127.0.0.1` only |

## Error handling and resilience

- A Lua error, an exhausted budget or the runtime's memory error ends the program and becomes a report entry. A program never takes the server down.
- An exception in the driver itself (a bug) ends the run as `failed` with `reason: internal`. The traceback goes to the server log, the server keeps serving, and a test reproduces the case.
- A server restart loses open runs. At startup, runs still open in the journal are closed as `abandoned`.
- Journal writes are transactions. Trace files are written atomically.
- The CLI prints a JSON error and exits with a non-zero code. It never prints a Python traceback for an expected failure.
- An unreadable or malformed level is refused by id with a parse error. It never reaches a run.
- The orchestrator records why a session ended (done, time limit, version limit, agent error). A crashed agent leaves its workspace and its stream log for diagnosis.
- When the screen's WebSocket drops, the page reconnects. The human game state stays in the server.

## Observability

- The server logs runs started and closed, stops, swaps, validation summaries, and sessions opened and closed to `data/logs/server.log` and the console. It never logs the text of a hidden level or the owner token.
- The journal is the source of all metrics. `golem-metrics` (v7.2) aggregates it per version: training passed per tier, the share of hidden levels passed, regressions, average steps per passed level, versions needed, and hidden validations.
- The orchestrator keeps each session's agent stream in `data/sessions/<session>/agent.jsonl`.
- Nothing is sent anywhere: no telemetry, no crash reporting.

## Repository layout

```
golem/
  CLAUDE.md                 # instructions for Claude Code (the developer, not Scribe)
  LICENSE
  README.md
  pyproject.toml            # v1.1: uv; no runtime deps in v1; fastapi + uvicorn + python-dotenv (v2.1),
                            # lupa (v3.1), typer + httpx (v5.1); dev: ruff, pytest
  .env.example              # v1.1: see §Configuration and secrets
  specification/
    VISION.md               # why and for whom, principles, non-goals, glossary
    ARCHITECTURE.md         # this file: components, mechanisms, contracts
    ROADMAP.md              # versions and phases with Goal/Tasks/DoD/Tests
    concept.en.md           # the original concept, the short overview
    concept.uk.md           # its Ukrainian translation, frozen
    implementation/         # issues files and reports (generated by the skills)
  golem/
    core/                   # v1: level.py, world.py, replay.py: the rules, stdlib only
    server/                 # v2.1: app.py (create_app), ws.py; api.py (v5.1)
    screen/                 # v2.2: index.html, screen.js, screen.css
    interp/                 # v3: sandbox.py, driver.py, report.py; run.py, stops.py, snapshot.py (v4)
    journal/                # v5.2: db.py, traces.py, validator.py
    cli.py                  # v5.1: the golem CLI
    local.py                # v3.2: golem-local, the in-process runner
    orchestrator/           # v6.1: golem-orchestrate
    levels_check.py         # v7.1: golem-levels, the owner's solvability check
    metrics.py              # v7.2: golem-metrics
  agents/
    scribe/                 # v6.2: CLAUDE.md (Scribe's instructions), task.md (the task prompt)
  levels/
    training/tier1/ …       # committed
    hidden/                 # gitignored; only README.md is committed
    budgets.toml
    README.md
  tests/
    fixtures/               # recorded solutions, test programs, fixture hidden levels
  .github/workflows/ci.yml  # v1.1: the gates on every push and pull request
  data/                     # gitignored: journal, traces, session streams, logs
  reports/                  # gitignored: metrics tables (v7.2)
```

## Testing and CI

Automated gates need no network and no model. The core is pure, the server and the CLI are tested in-process, lupa runs for real because it is local and deterministic, and the agent is replaced by a fake script.

| Gate | Command | When |
|---|---|---|
| Lint | `uv run ruff check .` | any Python change |
| Tests | `uv run pytest` (one test: `uv run pytest tests/test_x.py::test_name`) | any Python change |

Before v1.1 there is no `pyproject.toml`, so both gates are `n/a`, not passed.

- **Unit tests** cover the pure logic with plain data: the level parser and its errors, the rules (moves, pushes, failed moves counting a step, the corner rule on goal and non-goal cells, the win), save and restore, replay, the stop decisions, the `memory` conversion, report and snapshot assembly, version deduplication, and metrics aggregation.
- **Interpreter tests** run real lupa:
  - every name outside the allowlist is `nil` inside a program, and every escape attempt fails;
  - an infinite loop ends on the instruction budget;
  - a program's own `error("instruction budget exhausted")` is not a budget loss;
  - `pairs` order and `table.sort` are fixed;
  - **every fixture program runs twice in fresh runtimes, and the traces must be byte-identical.**
- **API and CLI tests** use FastAPI's `TestClient` and an httpx ASGI transport, with no open port. One test runs every route against a fixture hidden level and asserts that no part of its text appears in any response.
- **Orchestrator tests** use a fake agent, a small script standing in for `claude`, to check the workspace layout, the environment (no owner token, no `ANTHROPIC_*`), the tool-rules file, the version limit and the time-limit kill.
- **Contract tests** pin the seams in §Contracts. A contract change updates the test in the same commit.
- **Recorded solutions** in `tests/fixtures/solutions/` replay every committed training level to `solved` through the core.
- **CI** (`.github/workflows/ci.yml`, from v1.1) runs the same gates on every push and pull request. It has no secrets, and the hidden levels do not exist there.
- **Manual (owner) checks** are the DoD items that need a person or a live model: playing levels on the screen, swapping a program by hand, watching a replay, and every live Scribe session, which spends the owner's Claude subscription. They count as passed only once the owner confirms them.

## Open decisions

- **Lua through lupa.** The concept leaves the language open. v3.1 starts with a spike that must confirm the following before anything else is built on it:
  - lupa installs from wheels on macOS arm64 and Linux;
  - `lupa.lua54` coroutines can be driven from Python;
  - per-coroutine count hooks work;
  - `max_memory` works;
  - each determinism fix in §Robot language works.

  If any of these fails, the owner chooses the alternative before v3.1 continues.
- **The agent in a container.** v6.1 isolates the agent by tool rules and paths. A container with only the workspace mounted would make "cannot reach" hold at the operating-system level. The decision is made after v6.1's isolation check.
- **Level sources for tiers 2 and 3 and the hidden set.** Which published sets to use, under which licences, is decided in v7.1 and recorded in `levels/README.md`.
