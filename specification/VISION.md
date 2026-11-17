# Vision — Golem

## In one sentence

Golem is a Sokoban-style sandbox in which an AI agent, Scribe, never moves the robot itself: it writes a Lua program that drives the robot, runs it, reads the run report, and rewrites the program until it passes more levels than the previous version did.

## What we are building

A small test bench for one question: can an agent understand from a report why its program failed, and rewrite the program so that it does better? One Python server holds the game rules and the world. A human plays the levels with arrow keys on a browser screen; the robot plays them under a Lua program that runs in a sandbox. Both go through one game core, so they follow the same rules. The agent is a separate process (Claude Code in non-interactive mode, launched by a small orchestrator) and sees the game only through the `golem` command-line tool. The build order proves each part by hand before any model is involved: first the game core, then the game for a human, then the robot language and the interpreter, then stops and program swaps, then the validator and the journal. Only after that comes the agent, then experiments that measure where it stops coping, and finally several agents on one level.

## For whom

A private research project for the owner alone. Everything runs on the owner's Mac: the server listens on `127.0.0.1` only, the agent runs on the owner's Claude subscription, and nothing can be reached from the network. This is not a product, a public game or a benchmark for others. The repository is public (MIT), but the hidden levels, the journal and the agents' workspaces are not in it.

## The direction: the rewrite is the subject

The game is the means of measurement, not the goal. A solved level is easy to measure and hard to fake, so the game is a good test of the real subject: the loop in which an agent reads evidence about its own program and changes the program. Every part of the design serves that loop:

- The run report is the agent's only evidence.
- The level never restarts, so every mistake has a lasting cost.
- The hidden levels catch a program fitted to specific maps.
- The journal keeps every program version with its reason, so progress and regressions can be counted.

The last version (v8) asks the same question about several agents that have to cooperate.

## Principles

- **Simplicity first.** Complexity is added one version at a time, never all at once. A part that works end to end and has been checked by hand beats a complete design.
- **One core, one set of rules.** Human arrow-key moves and robot commands both go through the same game core. The rules exist nowhere else: not in the screen, not in the interpreter, not in the validator.
- **Every part is testable without a model.** The agent appears only in v6. Before that, every phase has a "done when" check that the owner can perform by hand. The automated tests never use the network or a model.
- **The agent sees the game only through `golem`.** It cannot read the hidden levels, the live world state, the journal or the project's own code. The isolation is built into the server and the agent's tool rules, not into the prompt: no API route returns a hidden map, and the agent's tools reach only its own workspace.
- **The robot sees only what is next to it.** A program gets the robot's own cell and the four neighbouring cells, never the full map and never its absolute position. To find anything, it has to explore and build the map in `memory`.
- **`memory` belongs to the interpreter, not to the program.** It lives for the whole level and survives a program swap, so a new program starts with the map the old one built.
- **The level never restarts.** A swap continues from the current world state with the remaining budget. Every wrong push has a lasting cost, which is what makes diagnosis matter.
- **Stops, not per-step calls.** The interpreter pauses only on events the agent has switched on. The agent never gets a model call per move, which would be too slow and too expensive.
- **Deterministic by construction.** The same program on the same level always gives the same result. That takes no clock and no unseeded randomness, a fixed iteration order inside the sandbox, and a pinned Lua runtime. A run that cannot be reproduced cannot be diagnosed.
- **Failures become report entries, never hangs or crashes.** An infinite loop ends on the instruction budget, a Lua error ends the program, and in both cases the server keeps running. Each failure becomes a line in the report.
- **Everything is kept.** Every program version is stored with the reason for the change, and every run is stored with its report and trace. Any run can be replayed, and any version can be rolled back to.
- **Hidden means hidden.** For a hidden level the agent learns only whether it passed. The hidden levels are not in the public repository, not in the agent's workspace, and never in an API response.
- **The agent runs on the owner's subscription, within limits.** The orchestrator enforces the version and time limits and keeps every API key out of the agent's environment. The server refuses a program version past the limit.
- **English throughout.** Code, comments, tests, the specification, the robot API, the screen and the agent's instructions are in English. `specification/concept.uk.md` is a frozen translation of the original concept and is no longer updated.

## Non-goals

- A Sokoban solver written by the owner, or any help with the robot's program. The program is the agent's own work. The repository ships only hand-written test programs that prove the interpreter works.
- Rules beyond classic Sokoban: no pulling, no pushing two boxes at once, no diagonal moves. v8 adds several robots and nothing else.
- Deadlock detection beyond the loss rule. A box pushed into a corner with no goal loses the level. Avoiding every other dead position is the program's job.
- A full map, absolute coordinates or any other shortcut for the robot. The partial view is the point.
- A model call per move, or an agent that watches the run step by step. The agent acts only at stops and after runs.
- A networked or multi-user game: no accounts, no access from other machines, no hosting.
- Graphics beyond a grid on a canvas: no frameworks, no build step, no CDN for the screen. Wrapping the page with pywebview is possible but outside this roadmap.
- Training or fine-tuning a model. The agent is an off-the-shelf Claude Code session; only its program and its notes change.
- Other agents. The interface allows the agent to be replaced, but this roadmap builds only Scribe (and, in v8, several Scribes).

## Glossary

- **Golem**: the project, and the robot inside the game world.
- **Scribe**: the first agent, a Claude Code session in non-interactive mode that writes the robot's Lua program.
- **Owner**: the one human. The owner plays levels by hand, runs the experiments and confirms the manual checks.
- **Game core**: the pure-Python world state and Sokoban rules (`golem/core/`), the only place where the rules exist.
- **Level**: one map in the standard Sokoban text format, with a tier and a step and instruction budget.
- **Level id**: `<set>/<tier>/<name>`, e.g. `training/tier1/t1-03`. Hidden levels have opaque names such as `hidden/tier2/h-07`.
- **Tier**: a difficulty class. Tier 1 is one box in an open room, tier 2 is several boxes and corridors, tier 3 is levels with traps.
- **Training levels**: the levels the agent may run and gets full reports for (`levels/training/`, committed).
- **Hidden levels**: the levels the agent can reach only through `golem validate`, and only as passed or failed (`levels/hidden/`, never committed).
- **Program**: a Lua source file written by the agent. One level can be driven by several programs in a row.
- **Program version**: a distinct program text sent to the server. The journal stores it with the reason for the change.
- **Robot API**: the five commands a program can call: `move`, `look`, `here`, `boxes_left` and `give_up`.
- **Sandbox**: the Lua environment a program runs in. It holds the robot API, `memory` and an allowlist of safe Lua functions, and nothing else.
- **`memory`**: the Lua table that the interpreter owns for the whole level. It survives a swap.
- **Step**: one `move` call, whether or not the robot moved. Steps count against the step budget.
- **Instruction**: one Lua VM instruction, counted through `debug.sethook` against the instruction budget.
- **Run**: one level played from its start to its end, possibly through several program versions.
- **Stop**: a pause in a run on an event the agent has switched on: `error`, `deadlock`, `give_up`, `half_budget` or `repeat`.
- **Snapshot**: what the agent gets at a stop: `memory`, the latest actions, the stop reason and the remaining budget.
- **Swap**: starting a new program from the current world state, with the same `memory` and the remaining budget.
- **Run report**: the result for one level: the status, the step and instruction counts, the error text, the last 20 actions and the final map. For a hidden level the report says only passed or failed.
- **Trace**: the full record of a run (every command with its result, every stop and swap), kept as a JSON file. Replays are built from it.
- **Journal**: the SQLite database of sessions, program versions, runs and validations.
- **Validator**: runs one program over level sets with every stop off and writes the reports to the journal.
- **Session**: one agent's working period: its workspace, its version and time limits, and its journal entries.
- **Workspace**: the agent's own directory, outside the repository. It is the only place the agent's file tools can reach.
- **Orchestrator**: the Python program that opens a session, prepares its workspace, launches the agent and enforces the limits.
