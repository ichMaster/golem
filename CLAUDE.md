# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Specification

Read these before planning work. They are the project's contract with itself.

- **[specification/VISION.md](specification/VISION.md)**: what Golem is, for whom, the principles (one core, the agent's isolation, determinism), the non-goals and the glossary. A request that violates a non-goal is a conversation, not a task.
- **[specification/ARCHITECTURE.md](specification/ARCHITECTURE.md)**: the components, the world and the rules, the robot language and the sandbox, execution and budgets, stops and swaps, the validator and the journal, the HTTP API and the CLI, the agent's isolation, the **contracts**, configuration, security, and the acceptance gates.
- **[specification/ROADMAP.md](specification/ROADMAP.md)**: eight versions (v1 Game core … v8 Several agents), one per phase of the concept. Each phase `vA.B` has a Goal, Tasks, a DoD and Tests. Build phases strictly in order and check each against its DoD before moving on.

**Languages of the specification.**

- **English is the only maintained language.** Never create Ukrainian versions of the specification files.
- **`specification/concept.uk.md` is frozen.** Never update it, never treat it as a source of truth, and never require changes to stay in sync with it.
- **`specification/concept.en.md` is the original concept and the short overview.** VISION, ARCHITECTURE and ROADMAP are the source of truth. When a change touches something the concept states (a component, a command, the robot API, a phase), update the concept too.

## Names

- **Golem**: the project, and the robot inside the game world.
- **Scribe**: the first agent, which writes the robot's Lua program.

## Project status

v1 (the game core), v2.1 (the server and the human game over WebSocket) and v2.2 (the text game screen) are built and released; the rest of v2, the prototype (Lua runs and the program swap), is next. Golem is a Sokoban-style sandbox in which an AI agent writes, runs and rewrites its own Lua program that drives a robot through puzzle levels.

Latest release: v2.2.0 (phase v2.2 — the text game screen).

| Version | Phases | What it delivers |
|---|---|---|
| `v1` Game core | v1.1 skeleton + level format · v1.2 rules · v1.3 save, restore, replay | the rules as pure Python; the gates and CI |
| `v2` Prototype | v2.1 server + WebSocket · v2.2 text game screen · v2.3 Lua runs (lupa spike first) · v2.4 swap prototype | the whole loop at its smallest: the owner plays, a program runs, a swapped-in program finishes the level |
| `v3` Game screen | v3.1 the screen's data + ten levels · v3.2 scene + panels · v3.3 motion + small windows | the owner plays ten levels on the "Clay and stone" screen |
| `v4` Interpreter | v4.1 full sandbox + run report · v4.2 stops + snapshot | a program swapped in by hand at a stop finishes the level |
| `v5` Validator and journal | v5.1 HTTP API + CLI · v5.2 validator + journal · v5.3 replay | `golem` from the shell; every version and run kept |
| `v6` Agent | v6.1 orchestrator + isolation · v6.2 Scribe | the agent passes tier one without hints |
| `v7` Experiments | v7.1 tiers 2–3 + hidden sets · v7.2 metrics | where the agent stops coping |
| `v8` Several agents | outline, fixed after v7 | two agents pass what one cannot |

## Layout and commands (planned)

See ARCHITECTURE.md §Repository layout for the full tree. The commands, with the phase that adds each one:

- Server (v2.1): `uv run golem-server`, which listens on `http://127.0.0.1:8700`. The game screen is at `/`.
  The owner's scripts run it in the background: `scripts/start.sh` (opens the page; `--no-open`), `scripts/stop.sh`, `scripts/restart.sh`.
- Local runner (v2.3, `--swap` from v2.4, interactive at stops from v4.2): `uv run golem-local run <level> <program.lua> [--swap <program.lua>] [--stop-on …]`.
- The CLI (v5.1): `uv run golem levels | run | state | continue | swap | validate | versions | show`.
- Orchestrator (v6.1): `uv run golem-orchestrate --set training/tier1 [--max-versions N] [--max-minutes M]`.
- Owner tools: `uv run golem-levels check [--hidden]` (v7.1) and `uv run golem-metrics` (v7.2).

## Acceptance gates

Automated gates need no network and no model:

- the core is pure;
- the server and the CLI are tested in-process (`TestClient`, an httpx ASGI transport);
- lupa runs for real (it is local and deterministic);
- the agent is a fake script.

| Gate | Command | When |
|---|---|---|
| Lint | `uv run ruff check .` | any Python change |
| Tests | `uv run pytest` (one test: `uv run pytest tests/test_x.py::test_name`) | any Python change |

- **Before v1.1** there is no `pyproject.toml`, so the gates are `n/a`, not passed. ruff and pytest are dev dependencies, added by the issue that creates `pyproject.toml`.
- **Manual gates:** the ROADMAP DoD items marked **Manual (owner)** need a person or a live model.
  - Claude may start the server locally and run `golem` or `curl` commands against `127.0.0.1` to check its own work.
  - Playing on the game screen, swapping a program by hand and watching a replay are done or confirmed by the owner.
  - A live Scribe session spends the owner's Claude subscription, so Claude never launches one unless the owner asks.
  - A manual check counts as passed only once the owner confirms it.

## Rules that are easy to break

The full mechanisms live in ARCHITECTURE.md. These are the invariants most often broken by accident:

- **One core.** Every rule (moves, pushes, steps, the corner rule, the win) lives in `golem/core/` and nowhere else: not in the screen's JavaScript, not in the interpreter, not in the validator. `golem/core` imports only the standard library.
- **The agent's isolation.**
  - No API route returns a hidden level's text, a hidden trace or the live world state. Only the snapshot and the run report leave the server.
  - `run` refuses hidden ids, and `validate` reports hidden levels as passed or failed only.
  - The CLI sends program text, never paths, and reads programs only inside `GOLEM_WORKSPACE`.
  - The agent's workspace is outside the repository.
- **The sandbox is an allowlist.** The program's environment is a fresh table, never `_G`.
  - There is no `io`, `os`, `require`, `load`, `debug`, `pcall`, `coroutine`, `next`, metatables or `python`.
  - The runtime is created with `register_eval=False` and `register_builtins=False`, and no Python object is ever passed into Lua.
  - Programs are loaded as text only (mode `"t"`).
- **The budget error is a sentinel**, compared by identity. A program's own `error("…")` is never a budget loss.
- **Determinism.**
  - No clock and no unseeded randomness.
  - `pairs` iterates in a fixed order, `table.sort` is the stable merge sort, `tostring` and `string.format` print no addresses.
  - Every collection that reaches JSON is sorted.
  - The lupa version and `lupa.lua54` are pinned.
  - A fixture program run twice must give byte-identical traces.
- **`memory` belongs to the run**, not to the program. A swap shares the same table, carries over the counters, and never restarts the level.
- **Keep decisions pure:** the rules, the parser, the stop decisions, the `memory` conversion, report assembly, version deduplication and metrics are functions over plain data.
- **Failures are report entries.** A Lua error, an exhausted budget or the memory cap ends the program, never the server.
- **Secrets stay out.**
  - Never read, print, copy or commit anything under `levels/hidden/`. Tests use `tests/fixtures/hidden/`.
  - Never print `.env` (`GOLEM_OWNER_TOKEN`) or anything under `data/`.
  - The agent's environment never contains `GOLEM_OWNER_TOKEN` or any `ANTHROPIC_*` variable.

## Contracts

The list of contracts lives in **ARCHITECTURE.md §Contracts**: the level format and ids, the rules, the robot API, the sandbox, the stops, the JSON shapes, the routes and CLI commands, the WebSocket messages, the journal schema, the trace format, the env var names, the workspace and the tool rules. Changing one updates ARCHITECTURE.md (and `concept.en.md` where it states the same thing) and the test that pins it, in the same commit.

## Delivery workflow (skills)

`.claude/skills/` holds a spec-driven pipeline adapted from the matrix-agora project.

- **Issues:** each ROADMAP phase `vA.B` becomes `specification/implementation/vA.B-issues.md`. Issue ids are `GOLEM-###`, numbered globally and never reset.
- **Implementation:** each issue is one commit. Each phase is then reviewed, and the fix-now findings are fixed.
- **Releases:** a release covers the phases built since the previous release and is numbered after the last of them. v1.1–v1.3 shipped together are `1.3.0` (tag `v1.3.0`); a release of one phase `vA.B` is `A.B.0`. Post-release fixes bump the last digit (`1.3.1`, …).
- **GitHub flow:** `/ship-phase <selector>` (a phase `vA.B`, a version `vA`, or a range) works one version at a time.
  - For each phase of the version it runs `/generate-issues` → `/upload-issues` → `/execute-issues`.
  - Then it stops so that the owner can test the version, and the problems found are fixed together.
  - After the owner says testing is finished, it runs `/review-and-fix-issues` and one `/release-version` for the version.
  - `/harden-findings` runs at the end of the run.
- **Branches are the owner's.** The skills commit, push and tag on the checked-out branch, and never create, switch, merge or delete a branch.
- **Offline flow:** `/ship-solution` runs `/reconcile-issues` → `/execute-issues-file` → `/review-and-fix-issues` → `/release-version` over issues files that already exist.
- **Who releases:** versions are bumped and tagged only by `/release-version`, `/ship-phase`, `/ship-solution` or `/harden-findings --release`.

## Constraints

- The server binds `127.0.0.1` only. Nothing in this project listens on the network.
- Lua is lupa 2.8 with `lupa.lua54`, confirmed by the v2.3 spike and pinned exactly. lupa keeps a `python` table in the runtime's globals that reaches Python objects: the sandbox removes it, and no program ever sees the globals. C functions such as the pattern matcher run without the count hook; the owner decides how to bound them before v4.1.
- v2.4 (the swap prototype) must prove the swap design before anything is built on it. v2 is a prototype: do not polish it beyond its DoD. Its code lives in the final modules, and v3 and v4 extend it rather than rewrite it.
