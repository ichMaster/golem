# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

Golem is a Sokoban-style sandbox in which an AI agent writes, runs, monitors and rewrites its own Lua program that drives a robot through puzzle levels. The repository is at the design stage: it holds only `README.md`, `LICENSE` (MIT) and a Python `.gitignore`. There is no code yet, so there are no build, lint or test commands. Add them here as soon as the first phase lands.

The design is in `specification/concept.en.md`, with a Ukrainian version of the same text in `specification/concept.uk.md`. The two files have the same sections in the same order; when the design changes, update both. Read the English spec before starting any component: it is the source for everything below.

## Names

- **Golem**: the project, and the robot inside the game world.
- **Scribe**: the first agent, which writes the robot's Lua program.

## Architecture (planned)

One Python server holds the game rules and the world state. The game screen and the agent are separate processes that reach the server only through its interface.

- **Game core**: pure Python with no dependencies and no graphics, deterministic, with save and restore of the world state. Human arrow-key moves and robot program commands both go through this one core, so they follow the same rules.
- **Server**: FastAPI on uvicorn. It serves the HTTP API for the CLI and a WebSocket for the game screen.
- **`golem` CLI**: Typer plus httpx, a thin wrapper that turns commands into HTTP requests. Every response is JSON. Commands: `levels`, `run <level> <program>`, `state`, `continue`, `swap <program>`, `validate <program>`.
- **Interpreter**: Lua through `lupa` (the choice of Lua is still open). Each robot command is a coroutine yield, so execution can stop after any move. Step and instruction budgets are counted through `debug.sethook`, so an infinite loop ends as a report entry rather than a hang. The sandbox disables `io`, `os` and `require`.
- **Validator and journal**: run a program over level sets. Runs and program versions go to SQLite; traces go to JSON files. Each program version is stored with the reason for the change, so a rollback is possible.
- **Levels**: text files in the standard Sokoban format, split into training and hidden sets.
- **Game screen**: one HTML page with canvas and plain JavaScript, no frameworks. It also replays recorded program runs.
- **Agent**: Claude Code in non-interactive mode, launched as a subprocess by a small Python orchestrator that enforces the version and time limits and keeps the journal.

### Invariants that the design depends on

- **Isolation of the agent.** The agent sees the game only through `golem` commands. It must not be able to read hidden levels or the world state. For hidden levels, `validate` returns only passed or failed; for training levels it returns the full report.
- **Partial view.** The robot sees only its own cell and the four neighbouring cells. The program never receives the full map and has to build it in `memory`.
- **`memory` lives outside the program.** The interpreter owns the `memory` table for the whole level. A `swap` starts the new program from the current world state with the same `memory` and the remaining budget. The level never restarts, so every wrong push has a lasting cost.
- **Determinism.** The same program on the same level always gives the same result.
- **Stops, not per-step calls.** The interpreter stops on events the agent sets: a Lua error, a deadlock, a `give_up` call, half the budget spent with no box on a goal, or a repeated world state. At a stop the agent gets a snapshot (memory, latest actions, stop reason, remaining budget) and either continues or swaps the program. The agent does not get a model call per move.

### Robot API inside the Lua sandbox

| Command | Returns |
| --- | --- |
| `move(dir)` with `dir` in N, E, S, W; pushes a box if the cell behind it is free | `true` or `false` |
| `look(dir)` | `wall`, `box`, `goal`, `box_on_goal` or `empty` |
| `here()` | `goal` or `empty` |
| `boxes_left()` | number of boxes not on goals |
| `give_up(reason)` | stops the run; the reason goes into the report |

A level is lost when the step budget runs out, the instruction budget runs out, or a box is pushed into a corner that has no goal.

The run report is the agent's only source of information about a run. Per level it contains the status, step and instruction counts, the error text, the robot's last 20 actions and the final map.

## Implementation order

The spec defines eight phases: core, human game, language and interpreter, stops and program swap, validator and journal, agent, experiments, several agents. The agent appears only in phase 6, so every earlier part must be testable by hand without a model. Each phase has a "done when" criterion in the spec; use it as the acceptance test.

Phase 4 (stops and program swap) decides how `memory` and the interpreter are built. The spec says to prototype it right after phase 3, before polishing anything else.
