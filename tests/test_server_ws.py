"""The human game over the WebSocket /ws (a contract): states from the core, errors that keep the
connection open, hidden ids refused like unknown ones, and the current state on connect."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from golem.core.levels import budget_for, load_budgets, load_level
from golem.core.replay import replay
from golem.core.world import World, render
from golem.server.app import create_app
from golem.server.config import Settings
from golem.server.ws import handle

REPO = Path(__file__).resolve().parent.parent
LEVELS = REPO / "levels"
HIDDEN_FIXTURE = REPO / "tests" / "fixtures" / "hidden" / "tier1" / "h-01.txt"
T1 = "training/tier1/t1-01"


def client_for(levels_dir: Path, tmp_path: Path) -> TestClient:
    return TestClient(create_app(Settings("127.0.0.1", 8700, levels_dir, tmp_path / "logs")))


def expected(world: World) -> dict:
    return {
        "type": "state",
        "level": world.level.id,
        "map": render(world),
        "steps": world.steps,
        "budget": world.step_budget,
        "status": world.status,
        "reason": world.loss_reason,
    }


def send(ws, message) -> dict:
    ws.send_text(message if isinstance(message, str) else json.dumps(message))
    return ws.receive_json()


def core_states(level_id: str, moves: str) -> list[World]:
    level = load_level(level_id, LEVELS)
    _, states = replay(level, moves, budget_for(level_id, load_budgets(LEVELS)))
    return states


# --- the game, through the core ----------------------------------------------------------------


def test_a_scripted_client_plays_a_level_and_every_state_matches_the_core(tmp_path):
    with client_for(LEVELS, tmp_path).websocket_connect("/ws") as ws:
        replies = [send(ws, {"type": "load", "level": T1})]
        replies += [send(ws, {"type": "move", "dir": d}) for d in "EE"]
    assert replies == [expected(state) for state in core_states(T1, "EE")]
    assert replies[-1]["status"] == "solved"


def test_a_lost_level_reports_its_reason(tmp_path):
    with client_for(LEVELS, tmp_path).websocket_connect("/ws") as ws:
        send(ws, {"type": "load", "level": T1})
        replies = [send(ws, {"type": "move", "dir": d}) for d in "SENWNEE"]
    assert replies[-1] == expected(core_states(T1, "SENWNEE")[-1])
    assert (replies[-1]["status"], replies[-1]["reason"]) == ("lost", "deadlock")


def test_moves_after_the_end_change_nothing_and_restart_starts_again(tmp_path):
    states = core_states(T1, "EE")
    with client_for(LEVELS, tmp_path).websocket_connect("/ws") as ws:
        send(ws, {"type": "load", "level": T1})
        send(ws, {"type": "move", "dir": "E"})
        solved = send(ws, {"type": "move", "dir": "E"})
        after = send(ws, {"type": "move", "dir": "W"})
        restarted = send(ws, {"type": "restart"})
    assert after == solved == expected(states[-1])
    assert restarted == expected(states[0])


# --- errors keep the connection open ------------------------------------------------------------

ERRORS = [
    ("{not json", "the message is not JSON"),
    ("[1, 2]", "the message is not a JSON object"),
    ('"load"', "the message is not a JSON object"),
    ({"type": "jump"}, "unknown message type; use load, move or restart"),
    ({}, "the message has no type"),
    ({"type": "load"}, "unknown level"),
    ({"type": "load", "level": 5}, "unknown level"),
    ({"type": "load", "level": [T1]}, "unknown level"),
    ({"type": "load", "level": "training/tier1/nope"}, "unknown level"),
    ({"type": "load", "level": "hidden/tier1/h-01"}, "unknown level"),
    ({"type": "load", "level": "../levels/training/tier1/t1-01"}, "unknown level"),
    ({"type": "move", "dir": "N"}, "no level is loaded; send load first"),
    ({"type": "restart"}, "no level is loaded; send load first"),
]


@pytest.mark.parametrize(("message", "detail"), ERRORS)
def test_a_bad_message_gets_an_error_and_the_connection_stays_open(
    root_with_hidden, tmp_path, message, detail
):
    with client_for(root_with_hidden, tmp_path).websocket_connect("/ws") as ws:
        assert send(ws, message) == {"type": "error", "detail": detail}
        assert send(ws, {"type": "load", "level": T1})["type"] == "state"


@pytest.mark.parametrize("move", [{"type": "move", "dir": "X"}, {"type": "move"},
                                  {"type": "move", "dir": ["N"]}, {"type": "move", "dir": "n"}])
def test_a_bad_direction_gets_an_error_and_changes_nothing(tmp_path, move):
    with client_for(LEVELS, tmp_path).websocket_connect("/ws") as ws:
        loaded = send(ws, {"type": "load", "level": T1})
        assert send(ws, move) == {"type": "error", "detail": "dir must be N, E, S or W"}
        assert send(ws, {"type": "restart"}) == loaded


def test_a_binary_frame_gets_an_error(tmp_path):
    with client_for(LEVELS, tmp_path).websocket_connect("/ws") as ws:
        ws.send_bytes(b'{"type": "load"}')
        assert ws.receive_json() == {"type": "error", "detail": "send messages as text frames"}
        assert send(ws, {"type": "load", "level": T1})["type"] == "state"


def test_an_error_never_echoes_the_message(tmp_path):
    with client_for(LEVELS, tmp_path).websocket_connect("/ws") as ws:
        reply = send(ws, {"type": "jump", "note": "ECHO-CANARY"})
    assert "ECHO-CANARY" not in json.dumps(reply)


# --- hidden levels ------------------------------------------------------------------------------


def test_a_hidden_id_is_refused_like_an_unknown_one_and_never_leaks(root_with_hidden, tmp_path):
    with client_for(root_with_hidden, tmp_path).websocket_connect("/ws") as ws:
        replies = [
            send(ws, {"type": "load", "level": "hidden/tier1/h-01"}),
            send(ws, {"type": "load", "level": "hidden/tier1/missing"}),
            send(ws, {"type": "load", "level": "training/tier1/missing"}),
        ]
    assert replies[0] == replies[1] == replies[2] == {"type": "error", "detail": "unknown level"}
    text = json.dumps(replies)
    for line in HIDDEN_FIXTURE.read_text(encoding="utf-8").splitlines():
        if not line.startswith(";"):
            assert line not in text


# --- the game lives in the server ---------------------------------------------------------------


def test_a_new_connection_first_receives_the_current_state(tmp_path):
    client = client_for(LEVELS, tmp_path)
    with client.websocket_connect("/ws") as ws:
        send(ws, {"type": "load", "level": T1})
        moved = send(ws, {"type": "move", "dir": "N"})
    with client.websocket_connect("/ws") as ws:
        assert ws.receive_json() == moved
        assert send(ws, {"type": "move", "dir": "S"})["steps"] == 2


def test_without_a_game_a_new_connection_receives_nothing_first(tmp_path):
    with client_for(LEVELS, tmp_path).websocket_connect("/ws") as ws:
        assert send(ws, {"type": "restart"})["type"] == "error"


def test_the_same_messages_give_the_same_states_on_two_fresh_servers(tmp_path):
    messages = [{"type": "load", "level": T1}] + [{"type": "move", "dir": d} for d in "NSEWEE"]
    runs = []
    for name in ("a", "b"):
        with client_for(LEVELS, tmp_path / name).websocket_connect("/ws") as ws:
            runs.append(json.dumps([send(ws, message) for message in messages]))
    assert runs[0] == runs[1]


def test_handle_leaves_the_game_as_it_was_on_a_bad_message():
    _, game = handle(json.dumps({"type": "load", "level": T1}), None, LEVELS)
    reply, after = handle("{not json", game, LEVELS)
    assert reply["type"] == "error"
    assert after is game


# --- code review #1: only the server's own page may open /ws ------------------------------------


@pytest.mark.parametrize(
    "origin",
    [
        "https://evil.example",
        "null",
        "http://127.0.0.1:9999",
        "http://127.0.0.1.evil.example:8700",
        "https://127.0.0.1:8700",
    ],
)
def test_a_foreign_origin_is_refused_before_the_handshake(tmp_path, origin):
    client = client_for(LEVELS, tmp_path)
    with pytest.raises(WebSocketDisconnect) as caught:
        with client.websocket_connect("/ws", headers={"origin": origin}):
            pass
    assert caught.value.code == 1008


@pytest.mark.parametrize(
    "origin", ["http://127.0.0.1:8700", "http://localhost:8700", "http://[::1]:8700"]
)
def test_the_servers_own_page_may_connect(tmp_path, origin):
    with client_for(LEVELS, tmp_path).websocket_connect("/ws", headers={"origin": origin}) as ws:
        assert send(ws, {"type": "load", "level": T1})["type"] == "state"
