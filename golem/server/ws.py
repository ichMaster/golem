"""The human game over the WebSocket ``/ws`` (a contract, ARCHITECTURE.md §HTTP API).

The server holds one game. ``handle`` is a plain function that turns one message and the current
game into a reply and the next game, so the protocol is tested without a socket; the route only
moves text. Every state comes from the core: this module never decides a rule.

The game is saved to a file after every change and restored from it at start, so a page that
reconnects after a server restart finds the game where it was.
"""

import contextlib
import json
import logging
import os
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path

from fastapi import FastAPI, WebSocket

from golem.core.level import Level, LevelError
from golem.core.levels import (
    Budget,
    BudgetsError,
    UnknownLevel,
    budget_for,
    list_levels,
    load_budgets,
    load_level,
)
from golem.core.world import World, from_json, move, new_world, render, to_json

LOG = logging.getLogger("golem.ws")
UNKNOWN_LEVEL = "unknown level"


@dataclass(frozen=True)
class Game:
    """The human game the server holds: the level, its budget and the current world."""

    level: Level
    budget: Budget
    world: World


def state_message(game: Game) -> dict:
    world = game.world
    return {
        "type": "state",
        "level": game.level.id,
        "map": render(world),
        "steps": world.steps,
        "budget": world.step_budget,
        "status": world.status,
        "reason": world.loss_reason,
    }


def error_message(detail: str) -> dict:
    return {"type": "error", "detail": detail}


def handle(text: str, game: Game | None, levels_dir: Path) -> tuple[dict, Game | None]:
    """One client message → the reply and the next game. A bad message leaves the game as it was."""
    try:
        data = json.loads(text)
    except (ValueError, RecursionError):
        return error_message("the message is not JSON"), game
    if not isinstance(data, dict):
        return error_message("the message is not a JSON object"), game

    kind = data.get("type")
    if kind == "load":
        return _load(data.get("level"), game, levels_dir)
    if kind in ("move", "restart") and game is None:
        return error_message("no level is loaded; send load first"), game
    if kind == "move":
        try:
            world, _ = move(game.world, data.get("dir"))
        except ValueError:
            return error_message("dir must be N, E, S or W"), game
        if world.status != game.world.status:
            LOG.info("%s %s after %d steps (%s)", game.level.id, world.status, world.steps,
                     world.loss_reason)
        moved = replace(game, world=world)
        return state_message(moved), moved
    if kind == "restart":
        restarted = replace(game, world=new_world(game.level, game.budget))
        return state_message(restarted), restarted
    if kind is None:
        return error_message("the message has no type"), game
    return error_message("unknown message type; use load, move or restart"), game


def _load(level_id: object, game: Game | None, levels_dir: Path) -> tuple[dict, Game | None]:
    """Only training ids load; a hidden, unknown or non-string id gets the same error."""
    if not isinstance(level_id, str) or level_id not in list_levels("training", levels_dir):
        return error_message(UNKNOWN_LEVEL), game
    try:
        level = load_level(level_id, levels_dir)
        budget = budget_for(level_id, load_budgets(levels_dir))
    except (LevelError, BudgetsError, OSError) as error:
        LOG.error("training level %s does not load: %s", level_id, error)
        return error_message(f"level {level_id} cannot be loaded"), game
    loaded = Game(level=level, budget=budget, world=new_world(level, budget))
    LOG.info("loaded %s", level_id)
    return state_message(loaded), loaded


def saved_text(game: Game) -> str:
    """The save file's text: ``{"world": to_json(world)}``, keys sorted, one line."""
    return json.dumps({"world": to_json(game.world)}, sort_keys=True, ensure_ascii=False) + "\n"


def save_game(game: Game, path: Path) -> None:
    """Write the game atomically: a temporary file in the same directory, then ``os.replace``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            file.write(saved_text(game))
        os.replace(temporary, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(temporary)
        raise


def restore_game(path: Path, levels_dir: Path) -> Game | None:
    """The saved game, or ``None`` when there is none or it does not restore.

    Only a training level restores, as with ``load``. A save that does not restore is logged with
    a fixed reason, never with the file's contents or a level's text, and the file is left as it
    is; the next change overwrites it.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except (OSError, UnicodeDecodeError):
        return _no_saved_game(path, "it cannot be read")
    try:
        data = json.loads(text)
    except (ValueError, RecursionError):
        return _no_saved_game(path, "it is not JSON")
    saved = data.get("world") if isinstance(data, dict) else None
    level_id = saved.get("level") if isinstance(saved, dict) else None
    if not isinstance(level_id, str):
        return _no_saved_game(path, "it is not a saved game")
    if level_id not in list_levels("training", levels_dir):
        return _no_saved_game(path, "its level is not a training level")
    try:
        level = load_level(level_id, levels_dir)
        budget = budget_for(level_id, load_budgets(levels_dir))
    except (LevelError, UnknownLevel, BudgetsError, OSError):
        return _no_saved_game(path, "its level does not load")
    try:
        world = from_json(saved, level)
    except ValueError:
        return _no_saved_game(path, "it does not fit its level")
    LOG.info("restored the game on %s from %s", level_id, path.name)
    return Game(level=level, budget=budget, world=world)


def _no_saved_game(path: Path, reason: str) -> None:
    LOG.warning("the saved game %s does not restore: %s; starting without a game", path, reason)
    return None


def allowed_origins(port: int) -> frozenset[str]:
    """The server's own page, the only browser origin that may open ``/ws``."""
    return frozenset(
        f"http://{host}:{port}" for host in ("127.0.0.1", "localhost", "[::1]")
    )


def install_ws(app: FastAPI, levels_dir: Path, port: int, game_file: Path | None = None) -> None:
    """Add ``/ws``. The game lives on ``app.state.game``, one per server.

    With a ``game_file``, the game is restored from it now and saved to it after every change.
    A handshake is accepted only without an ``Origin`` header (a non-browser client) or from the
    server's own page; any other web page is refused with close code 1008 before it is accepted.
    """
    app.state.game = restore_game(game_file, levels_dir) if game_file is not None else None
    origins = allowed_origins(port)

    def keep(game: Game | None) -> None:
        """Hold the next game, and save it when it changed. A failed save is only logged."""
        if game is app.state.game:
            return
        app.state.game = game
        if game_file is None or game is None:
            return
        try:
            save_game(game, game_file)
        except OSError as error:
            LOG.error("the game could not be saved to %s: %s", game_file, error)

    @app.websocket("/ws")
    async def human_game(websocket: WebSocket) -> None:
        origin = websocket.headers.get("origin")
        if origin is not None and origin not in origins:
            LOG.warning("refused a WebSocket from origin %r", origin)
            await websocket.close(code=1008)
            return
        await websocket.accept()
        if app.state.game is not None:
            await websocket.send_json(state_message(app.state.game))
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                return
            text = message.get("text")
            if text is None:
                reply = error_message("send messages as text frames")
            else:
                reply, game = handle(text, app.state.game, levels_dir)
                keep(game)
            await websocket.send_json(reply)
