# Levels

One level per `.txt` file, in the standard Sokoban text format. The character table, the comment and
ragged-row rules and what makes a level valid are in
[ARCHITECTURE.md §World and rules](../specification/ARCHITECTURE.md#world-and-rules). In short: `#` wall,
space, `-` or `_` floor, `$` box, `.` goal, `*` box on a goal, `@` robot, `+` robot on a goal, and lines
that start with `;` are comments.

## Ids and layout

A level's id is `<set>/<tier>/<name>`, for the file `levels/<set>/<tier>/<name>.txt`. Each part uses
lowercase letters, digits and `-`, and a tier directory is `tier<N>`. Files with other names are not
levels and are ignored.

- `training/`: the levels the agent may run and gets full reports for. Committed.
- `hidden/`: the owner's hidden levels, reachable only through `golem validate`. Not committed; see
  [hidden/README.md](hidden/README.md).
- `budgets.toml`: the step and instruction budgets per tier.

## Recorded solutions

Every training level has a recorded solution in `tests/fixtures/solutions/<level id>.txt`: a move string
of `N`, `E`, `S` and `W`, where lines that start with `;` are comments and whitespace is ignored. A new
training level needs one; `tests/test_solutions.py` checks that each level has a solution and that each
solution replays to `solved`.

## Tiers

1. One box in an open room.
2. Several boxes and corridors (from v7.1).
3. Levels with traps, where a careless push during exploration loses the level at once (from v7.1).

## Sources and licences

| Level | Source | Licence |
|---|---|---|
| `training/tier1/t1-01` | written for this project | MIT, as the repository |
| `training/tier1/t1-02` | written for this project | MIT, as the repository |
| `training/tier1/t1-03` | written for this project | MIT, as the repository |
