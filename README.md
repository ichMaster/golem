# golem

Sokoban-style sandbox where an AI agent writes, runs, monitors and rewrites its own Lua program to drive a robot through puzzle levels.

Status: v1, the game core (the level format, the rules, save and replay), and v2.1, the server with the human game over WebSocket, are built; the rest of v2, the prototype (a text game screen, Lua runs and the program swap), is next. See the specification: [VISION.md](specification/VISION.md), [ARCHITECTURE.md](specification/ARCHITECTURE.md) and [ROADMAP.md](specification/ROADMAP.md) (the phased plan). The original concept is in [concept.en.md](specification/concept.en.md).

## Running the game

```sh
scripts/start.sh     # start golem-server in the background and open http://127.0.0.1:8700/
scripts/restart.sh   # restart it; an open page reconnects and the game goes on where it was
scripts/stop.sh      # stop it
```

`uv run golem-server` runs it in the foreground instead. The server's console output goes to
`data/logs/server.out`, and its log to `data/logs/server.log`.

## License

MIT — see [LICENSE](LICENSE).
