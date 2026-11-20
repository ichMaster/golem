"""The human game over the WebSocket /ws (a contract): states from the core, errors that keep the
connection open, hidden ids refused like unknown ones, and the current state on connect."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from golem.core.level import parse_level
from golem.core.levels import Budget, budget_for, load_budgets, load_level
from golem.core.replay import replay
from golem.core.world import World, new_world, render, to_json
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


PING_ERROR = {"type": "error", "detail": "unknown message type; use load, move or restart"}


def state_on_connect(ws) -> dict:
    """The state the server sends on connect, read without waiting forever when none is sent.

    A harmless bad message goes first, and its error reply always arrives. A missing state then
    fails the test at once instead of hanging it (v2.2 code review #2).
    """
    ws.send_text(json.dumps({"type": "ping"}))
    first = ws.receive_json()
    assert first["type"] == "state", f"no state on connect, got {first}"
    assert ws.receive_json() == PING_ERROR
    return first


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
        assert state_on_connect(ws) == moved
        assert send(ws, {"type": "move", "dir": "S"})["steps"] == 2


def test_without_a_game_a_new_connection_receives_nothing_first(tmp_path):
    with client_for(LEVELS, tmp_path).websocket_connect("/ws") as ws:
        assert send(ws, {"type": "restart"})["type"] == "error"



def test_reading_the_state_on_connect_fails_fast_when_none_is_sent(tmp_path):
    # code review #2: a missing state on connect must fail the test, never hang it
    with client_for(LEVELS, tmp_path).websocket_connect("/ws") as ws:
        with pytest.raises(AssertionError, match="no state on connect"):
            state_on_connect(ws)

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


# --- the game survives a server restart (data/human-game.json) ----------------------------------

T2 = "training/tier1/t1-02"


def saving_client(levels_dir: Path, tmp_path: Path, game_file: Path | None) -> TestClient:
    settings = Settings("127.0.0.1", 8700, levels_dir, tmp_path / "logs", game_file)
    return TestClient(create_app(settings))


def play(client: TestClient, messages: list[dict]) -> list[dict]:
    with client.websocket_connect("/ws") as ws:
        return [send(ws, message) for message in messages]


def moves(directions: str) -> list[dict]:
    return [{"type": "move", "dir": d} for d in directions]


def test_a_restarted_server_finds_the_game_where_it_was(tmp_path):
    game_file = tmp_path / "data" / "human-game.json"
    before = play(saving_client(LEVELS, tmp_path, game_file), [{"type": "load", "level": T2}]
                  + moves("NNW"))
    restarted = saving_client(LEVELS, tmp_path, game_file)
    with restarted.websocket_connect("/ws") as ws:
        assert state_on_connect(ws) == before[-1] == expected(core_states(T2, "NNW")[-1])
        assert send(ws, {"type": "move", "dir": "N"}) == expected(core_states(T2, "NNWN")[-1])


@pytest.mark.parametrize(("directions", "status", "reason"),
                         [("EE", "solved", None), ("SENWNEE", "lost", "deadlock")])
def test_an_ended_game_restores_with_its_status_and_reason(tmp_path, directions, status, reason):
    game_file = tmp_path / "human-game.json"
    before = play(saving_client(LEVELS, tmp_path, game_file), [{"type": "load", "level": T1}]
                  + moves(directions))
    with saving_client(LEVELS, tmp_path, game_file).websocket_connect("/ws") as ws:
        restored = state_on_connect(ws)
    assert restored == before[-1]
    assert (restored["status"], restored["reason"]) == (status, reason)


def test_load_and_restart_overwrite_the_save(tmp_path):
    game_file = tmp_path / "human-game.json"
    client = saving_client(LEVELS, tmp_path, game_file)
    play(client, [{"type": "load", "level": T1}] + moves("E") + [{"type": "load", "level": T2}])
    with saving_client(LEVELS, tmp_path, game_file).websocket_connect("/ws") as ws:
        assert state_on_connect(ws) == expected(core_states(T2, "")[0])
    play(client, moves("NN") + [{"type": "restart"}])
    with saving_client(LEVELS, tmp_path, game_file).websocket_connect("/ws") as ws:
        assert state_on_connect(ws) == expected(core_states(T2, "")[0])


def hidden_save() -> str:
    level = parse_level(HIDDEN_FIXTURE.read_text(encoding="utf-8"), "hidden/tier1/h-01")
    world = new_world(level, Budget(steps=200, instructions=1_000_000))
    return json.dumps({"world": to_json(world)})


def misfit_save() -> str:
    data = to_json(core_states(T1, "")[0])
    data["robot"] = [0, 0]  # a wall cell
    return json.dumps({"world": data})


@pytest.mark.parametrize(
    "text",
    [
        "not json {",
        "[1, 2]",
        '{"other": 1}',
        '{"world": {"level": 7}}',
        '{"world": {"level": "training/tier1/t1-99"}}',
        misfit_save(),
        hidden_save(),
    ],
    ids=["not-json", "not-object", "no-world", "bad-id", "unknown-id", "misfit", "hidden-id"],
)
def test_a_save_that_does_not_restore_starts_without_a_game(root_with_hidden, tmp_path, text):
    game_file = tmp_path / "human-game.json"
    game_file.write_text(text, encoding="utf-8")
    client = saving_client(root_with_hidden, tmp_path, game_file)
    with client.websocket_connect("/ws") as ws:
        # nothing arrives first: the first reply is the answer to restart
        assert send(ws, {"type": "restart"}) == {
            "type": "error", "detail": "no level is loaded; send load first"}
        assert game_file.read_text(encoding="utf-8") == text  # left as it was
        assert send(ws, {"type": "load", "level": T1})["status"] == "playing"
    assert json.loads(game_file.read_text(encoding="utf-8"))["world"]["level"] == T1
    log = (tmp_path / "logs" / "server.log").read_text(encoding="utf-8")
    assert "does not restore" in log
    for line in HIDDEN_FIXTURE.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith(";"):
            assert line not in log


def test_without_a_game_file_nothing_is_saved(tmp_path):
    play(saving_client(LEVELS, tmp_path, None), [{"type": "load", "level": T1}] + moves("EE"))
    assert not [p for p in tmp_path.rglob("*") if p.is_file() and p.suffix != ".log"]


def test_the_save_is_atomic_and_leaves_no_temporary_file(tmp_path):
    game_file = tmp_path / "data" / "human-game.json"
    play(saving_client(LEVELS, tmp_path, game_file),
         [{"type": "load", "level": T2}] + moves("NNWNE") + [{"type": "restart"}])
    assert sorted(p.name for p in game_file.parent.iterdir()) == ["human-game.json"]


def test_a_failed_save_is_logged_and_the_game_goes_on(tmp_path):
    blocker = tmp_path / "blocker"
    blocker.write_text("a file where the directory should be", encoding="utf-8")
    replies = play(saving_client(LEVELS, tmp_path, blocker / "human-game.json"),
                   [{"type": "load", "level": T1}] + moves("EE"))
    assert [reply["type"] for reply in replies] == ["state", "state", "state"]
    assert replies[-1]["status"] == "solved"
    assert "could not be saved" in (tmp_path / "logs" / "server.log").read_text(encoding="utf-8")


def test_the_save_is_byte_identical_on_two_fresh_servers(tmp_path):
    messages = [{"type": "load", "level": T2}] + moves("NNWNE")
    saved = []
    for name in ("a", "b"):
        game_file = tmp_path / name / "human-game.json"
        play(saving_client(LEVELS, tmp_path / name, game_file), messages)
        saved.append(game_file.read_bytes())
    assert saved[0] == saved[1]
    assert json.loads(saved[0])["world"]["status"] == "solved"
