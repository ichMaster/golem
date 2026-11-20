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

The owner answered: "я перевірю вже через клієнт в наст версії, роби реліз" ("I'll check it through the
client in the next version; do the release"). No problem was reported.

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

The owner answered: "тестування завершено, роби ревʼю і реліз" ("testing is finished; do the review and
the release"). No problem was reported. Claude records GOLEM-017's three Manual (owner) checks as confirmed
by the owner on these words.
