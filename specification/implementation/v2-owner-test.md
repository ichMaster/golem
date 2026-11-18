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
