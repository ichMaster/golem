"""The human game over the WebSocket ``/ws`` (a contract, ARCHITECTURE.md §HTTP API).

The server holds one game. ``handle`` is a plain function that turns one message and the current
game into a reply and the next game, so the protocol is tested without a socket; the route only
moves text. Every state comes from the core: this module never decides a rule.
"""

import json
import logging
from dataclasses import dataclass, replace
from pathlib import Path

from fastapi import FastAPI, WebSocket

from golem.core.level import Level, LevelError
from golem.core.levels import (
    Budget,
    BudgetsError,
    budget_for,
    list_levels,
    load_budgets,
    load_level,
)
from golem.core.world import World, move, new_world, render

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


def allowed_origins(port: int) -> frozenset[str]:
    """The server's own page, the only browser origin that may open ``/ws``."""
    return frozenset(
        f"http://{host}:{port}" for host in ("127.0.0.1", "localhost", "[::1]")
    )


def install_ws(app: FastAPI, levels_dir: Path, port: int) -> None:
    """Add ``/ws``. The game lives on ``app.state.game``, one per server.

    A handshake is accepted only without an ``Origin`` header (a non-browser client) or from the
    server's own page; any other web page is refused with close code 1008 before it is accepted.
    """
    app.state.game = None
    origins = allowed_origins(port)

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
                reply, app.state.game = handle(text, app.state.game, levels_dir)
            await websocket.send_json(reply)
