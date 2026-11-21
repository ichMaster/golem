# v2 — Owner Test

One section per `/ship-phase` run that builds part of v2.

## v2.1 (`/ship-phase 2.1`)

**Date:** 2026-11-19
**Branch:** v2-dev
**Built:** v2.1 (GOLEM-011…013), commits 25873cc…5fc4c07

### What was handed over for testing

- The gates: `uv run ruff check . && uv run pytest -q` (327 tests, CI green).
- `uv run golem-server`, and `curl -s http://127.0.0.1:8700/api/levels`.
- An interactive WebSocket client (a `websockets` script) that plays `training/tier1/t1-02`.
- A reconnect that receives the current state.
- `GOLEM_HOST=0.0.0.0 uv run golem-server` refusing to start.

Claude ran each of these before the handover.

### Problems found and fixed

None reported.

### Moved to later work

- **Hands-on testing of the human game:** the owner will test it through the game screen in v2.2. It is
  part of v2.2's owner test and of v2.2's own Manual (owner) DoD (playing ten levels).

### End of testing

The owner answered (translated): "I'll check it through the client in the next version; do the
release". No problem was reported.

## v2.2 (`/ship-phase v2.2`)

**Date:** 2026-11-20
**Branch:** v2-dev
**Built:** v2.2 (GOLEM-014…017), commits 6d44ded…586d031

### What was handed over for testing

- The gates: `uv run ruff check . && uv run pytest -q` (381 tests, CI green).
- `uv run golem-server`, then the text page at http://127.0.0.1:8700/, with the steps of GOLEM-017 (#17):
  1. pass t1-01, t1-02 and t1-03 by hand;
  2. push a box into a corner and see lost on deadlock;
  3. run out of steps and see lost on steps;
  4. press `R` to restart the level;
  5. restart the server with a level half played: the page shows `reconnecting…`, then continues the
     game where it was.

Before the handover, Claude checked the routes and the restart with `curl` and a `websockets` client.

### Problems found and fixed

None reported.

### Added at the owner's request during the test

- **Start scripts** (77715a3), outside the phase's issues: `scripts/start.sh` (background start, opens the
  page; `--no-open`), `scripts/stop.sh` and `scripts/restart.sh`. They are documented in README.md,
  CLAUDE.md and ARCHITECTURE's repository layout. `tests/test_scripts.py` checks that they are executable,
  valid bash, strict, and never widen the host.
- **A person's name removed** from a design-system comment (6b26037), in
  `specification/design/golem-clay/_ds/nocturne-…/styles.css`. The name remains in the git history
  (e172718). Rewriting that history needs a force-push, which is the owner's decision; it was not done.

### Moved to later work

Nothing.

### End of testing

The owner answered (translated): "testing is finished; do the review and the release". No problem was reported. Claude records GOLEM-017's three Manual (owner) checks as confirmed
by the owner on these words.

## v2.3 (`/ship-phase v2.3`)

**Date:** 2026-11-20
**Branch:** v2-dev
**Built:** v2.3 (GOLEM-018…021), commits d69ca00…a27e842

### What was handed over for testing

- The gates: `uv run ruff check . && uv run pytest -q` (519 tests, CI green).
- `uv run golem-local run training/tier1/<t1-01|t1-02|t1-03> tests/fixtures/programs/t1_solver.lua`.
- The other fixture programs on t1-01: `infinite_loop`, `syntax_error`, `runtime_error`, `give_up` and
  `own_budget_error`.
- A hidden id refused with exit 1.
- Writing a program by hand with the v2.3 robot API.
- The spike's findings: F1, fixed in the sandbox, and R1, an open decision for the owner before v4.1.

Claude ran each command before the handover.

### Problems found and fixed

None reported.

### Added at the owner's request during the test

- **The repository is English only** (950bf03, f084eb9):
  - CLAUDE.md gains a Language section;
  - the owner's quoted words in these records are translated;
  - a test string is made English;
  - ship-phase records the owner's words in English;
  - `tests/test_english_only.py` fails on Cyrillic text outside the frozen `concept.uk.md`.
- **A red commit:** 950bf03 was pushed with a failing test. The new guard found its own Cyrillic sample, and
  a `| tail` hid pytest's exit code. f084eb9 fixed it within minutes, and the gates now run with
  `pipefail`.

### Moved to later work

- **R1, a decision for the owner before v4.1:** how to bound C functions such as the pattern matcher, which
  run without the count hook. It is recorded in ARCHITECTURE §Open decisions.

### End of testing

The owner answered (translated): "testing is finished; do the review and the release". No problem was
reported.

## v2.4 (`/ship-phase v2.4`)

**Date:** 2026-11-21
**Branch:** v2-dev
**Built:** v2.4 (GOLEM-022…026), commits 3befc7c…6f4a0ad

### What was handed over for testing

- The gates: `uv run ruff check . && uv run pytest -q` (616 tests, CI green).
- `scripts/restart.sh` (or `scripts/start.sh`), then the text page at http://127.0.0.1:8700/, with the steps
  of GOLEM-026 (#26):
  1. click each program in Programs and read its code;
  2. run `t1_solver.lua` on t1-01, t1-02 and t1-03 and watch the playback;
  3. run `lost_on_steps.lua`, `lost_on_deadlock.lua` (t1-01), `endless_loop.lua`, `gives_up.lua` and
     `runtime_error.lua`, and see each ending, the error with its line (`program:6:`);
  4. edit or add a program in `programs/`, reload the page, and see the change without a restart.

Before the handover, Claude checked the routes on a live server and the panel in a node harness.

### Problems found and fixed

None reported.

### Moved to later work

- **R1** now also reaches the server: a pathological program in `programs/` could hold one worker thread.
  It stays the owner's decision before v4.1 (ARCHITECTURE §Open decisions).

### End of testing

The owner answered (translated): "Release it." No problem was reported. Claude records GOLEM-026's four
Manual (owner) checks as confirmed by the owner on these words.

## v2.5 (`/ship-phase v2.5`)

**Date:** 2026-11-21
**Branch:** v2-dev
**Built:** v2.5 (GOLEM-027…034), commits fbdcb16…df57218

### What was handed over for testing

- The gates: `uv run ruff check . && uv run pytest -q` (667 tests at the first handover, 699 at the
  second; CI green).
- `uv run golem-local run training/tier1/<t1-01|t1-02|t1-03> tests/fixtures/programs/explore.lua --swap
  tests/fixtures/programs/finish.lua`, `explore.lua` and `finish.lua` alone, a first program that solves on
  its own, and `infinite_loop.lua` swapped in.
- After the owner's request, the swap on the text page (GOLEM-034, #34): `explore.lua` with `finish.lua`
  in "Swap in" on t1-01, t1-02 and t1-03, and `t1_solver.lua` with a swap chosen.

Before each handover, Claude checked the route on a scratch server (port 8711) and the panel in a node
harness.

### Added at the owner's request during the test

- **The swap on the text page** (GOLEM-032…034, 302afab…04fe979). The owner asked: "can this
  functionality be moved to the web interface?". The owner chose to add it to v2.5, as a swap in one run
  with both programs chosen before Run. ROADMAP §v2.5 gained the task, a Manual (owner) DoD item and its
  tests.
- **The run log on the page** (df57218). The owner asked: "I want to see the swap log". The swap frame
  showed for 150 ms only, and the first program's give-up reason never reached the page.
  - The program route now returns `swaps`: the step, the instruction count, the version swapped in and
    how the program before it ended.
  - The page's run log lists the start, each ending, each swap and the outcome.
  - The server log names the swap's step, never a program's text.
  - Tests: `tests/test_swap.py::test_the_swap_log_says_where_and_why_the_second_program_took_over`,
    `tests/test_server_programs.py`, `tests/test_server_screen.py::test_the_run_log_is_built_from_the_swaps_and_grows_with_the_playback`.

### Problems found and fixed

- **The server log named a swap that had not happened** (found by Claude's live check, not by the owner):
  `ran t1_solver.lua with finish.lua swapped in` for a run solved by the first program. Fixed in 2df93fd;
  test `tests/test_server_programs.py::test_the_log_names_a_swap_only_when_it_happened`.

### Moved to later work

- **`explorer.lua` and `explore.lua` are easy to confuse.** The owner ran `explorer.lua` (the v2.4 example,
  which reports its map in the give-up text) with `finish.lua` swapped in. The run log showed it correctly:
  `finish.lua gave up: no map in memory`. Claude offered to rename `explorer.lua` and to make
  `finish.lua`'s message name `explore.lua`. The owner released without choosing, so this stays in the
  backlog.
- **R1** still stands for the owner before v4.1.
- **The Lua panic on a program text larger than the memory cap** (found in GOLEM-027, pre-existing since
  v2.3) goes to the v2.5 code review.

### End of testing

The owner answered (translated): "Release it." Claude records GOLEM-034's Manual (owner) check as
confirmed by the owner on these words.
