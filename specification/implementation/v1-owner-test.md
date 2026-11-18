# v1 — Owner Test

**Date:** 2026-11-18
**Branch:** v1-dev
**Built:** v1.1 (GOLEM-001…004), v1.2 (GOLEM-005…007), v1.3 (GOLEM-008…010); commits 05390d4…a8c715e

## What was handed over for testing

- The gates: `uv run ruff check . && uv run pytest -q` (261 tests, CI green).
- Replaying the recorded solution of `training/tier1/t1-02` (`NNWNE`) and printing every state; it ends
  `solved` after 5 steps.
- Pushing the box into a corner off the goal on `training/tier1/t1-01` (`SENWNEE`); it ends `lost` /
  `deadlock` after 7 steps, and the saved world's JSON is printed.
- Parsing a malformed level; it reports `demo:2:4: unknown character 'x'`.

## Problems found and fixed

None reported.

## Moved to later work

Nothing.

## End of testing

The owner answered "продовжуй" ("continue") to the handover, which said that the review and the release
follow once testing is finished. No problem was reported.
