# golem

Sokoban-style sandbox where an AI agent writes, runs, monitors and rewrites its own Lua program to drive a robot through puzzle levels.

Status: v1, the game core (the level format, the rules, save and replay), v2.1, the server with the human game over WebSocket, v2.2, the text game screen, v2.3, Lua programs that drive the robot (`golem-local run`), and v2.4, Lua programs run from the web page, are built; v2.5, the program swap, is next. See the specification: [VISION.md](specification/VISION.md), [ARCHITECTURE.md](specification/ARCHITECTURE.md) and [ROADMAP.md](specification/ROADMAP.md) (the phased plan). The original concept is in [concept.en.md](specification/concept.en.md).

## Running the game

```sh
scripts/start.sh     # start golem-server in the background and open http://127.0.0.1:8700/
scripts/restart.sh   # restart it; an open page reconnects and the game goes on where it was
scripts/stop.sh      # stop it
```

`uv run golem-server` runs it in the foreground instead. The server's console output goes to
`data/logs/server.out`, and its log to `data/logs/server.log`.

Run a Lua program on a training level, in-process, and print its report:

```sh
uv run golem-local run training/tier1/t1-01 programs/t1_solver.lua
```

## Programs on the page

The page's Programs panel lists the Lua programs in `programs/` (or in `GOLEM_PROGRAMS_DIR`), shows the
chosen one's code, runs it on a training level and plays the robot's moves back step by step, with the
report at the end. A program's file name is lower-case letters, digits, `-` and `_`, ending in `.lua`;
its first line, when it is a `--` comment, is its description in the list. A changed or added program
shows up after a reload of the page, without a restart of the server.

## License

MIT — see [LICENSE](LICENSE).
