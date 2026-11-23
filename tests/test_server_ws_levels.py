"""The level picker's list over the WebSocket /ws (v3.1, a contract): every training level with its
start map and its inside mask, never a hidden level, and GET /api/levels still without maps."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from golem.core.level import parse_level
from golem.core.levels import budget_for, list_levels, load_budgets, load_level
from golem.core.world import new_world, render
from golem.server.app import create_app
from golem.server.config import Settings
from golem.server.ws import handle

REPO = Path(__file__).resolve().parent.parent
LEVELS = REPO / "levels"
HIDDEN_FIXTURE = REPO / "tests" / "fixtures" / "hidden" / "tier1" / "h-01.txt"
LEVELS_REQUEST = {"type": "levels"}
UNAVAILABLE = {"type": "error", "detail": "the level list cannot be loaded"}
ENTRY_KEYS = ["id", "tier", "width", "height", "budget", "map", "inside"]


def client_for(levels_dir: Path, tmp_path: Path, game_file: Path | None = None) -> TestClient:
    settings = Settings("127.0.0.1", 8700, levels_dir, tmp_path / "logs", game_file)
    return TestClient(create_app(settings))


def send(ws, message: dict) -> dict:
    ws.send_text(json.dumps(message))
    return ws.receive_json()


def ask_levels(client: TestClient) -> dict:
    with client.websocket_connect("/ws") as ws:
        return send(ws, LEVELS_REQUEST)


def hidden_rows() -> set[str]:
    """The fixture hidden map's rows that no training map shares (a border such as `#########` is
    common to both, so it proves nothing)."""
    hidden = render(new_world(
        parse_level(HIDDEN_FIXTURE.read_text(encoding="utf-8"), "hidden/tier1/h-01"),
        load_budgets(LEVELS)["tier1"]))
    training = {row for level_id in list_levels("training", LEVELS)
                for row in render(new_world(load_level(level_id, LEVELS),
                                            budget_for(level_id, load_budgets(LEVELS))))}
    return set(hidden) - training


# --- the list matches the level files and the core ---------------------------------------------


def test_the_reply_lists_every_training_level_with_its_start_map_and_mask(tmp_path):
    client = client_for(LEVELS, tmp_path)
    reply = ask_levels(client)
    api = client.get("/api/levels").json()["levels"]
    assert list(reply) == ["type", "levels"] and reply["type"] == "levels"
    assert [entry["id"] for entry in reply["levels"]] == list_levels("training", LEVELS)
    budgets = load_budgets(LEVELS)
    for entry, listed in zip(reply["levels"], api, strict=True):
        level = load_level(entry["id"], LEVELS)
        assert list(entry) == ENTRY_KEYS
        assert {key: entry[key] for key in listed} == listed
        assert entry["map"] == render(new_world(level, budget_for(level.id, budgets)))
        rows = entry["inside"]
        assert [len(row) for row in rows] == [len(row) for row in entry["map"]]
        assert {(r, c) for r, row in enumerate(rows) for c, char in enumerate(row)
                if char == "1"} == level.inside


def test_the_list_comes_before_any_load_and_leaves_the_game_as_it_was(tmp_path):
    game_file = tmp_path / "human-game.json"
    with client_for(LEVELS, tmp_path, game_file).websocket_connect("/ws") as ws:
        assert send(ws, LEVELS_REQUEST)["type"] == "levels"
        assert send(ws, {"type": "move", "dir": "E"})["type"] == "error"
        assert not game_file.exists()
        send(ws, {"type": "load", "level": "training/tier1/t1-01"})
        moved = send(ws, {"type": "move", "dir": "E"})
        saved = game_file.read_text(encoding="utf-8")
        assert send(ws, {**LEVELS_REQUEST, "extra": [1, 2]})["type"] == "levels"
        assert game_file.read_text(encoding="utf-8") == saved
        after = send(ws, {"type": "move", "dir": "E"})
    assert (moved["steps"], after["steps"], after["status"]) == (1, 2, "solved")


def test_handle_answers_the_list_and_returns_the_same_game():
    reply, game = handle(json.dumps(LEVELS_REQUEST), None, LEVELS)
    assert reply["type"] == "levels" and game is None


def test_two_fresh_servers_give_byte_identical_lists(tmp_path):
    texts = []
    for name in ("a", "b"):
        with client_for(LEVELS, tmp_path / name).websocket_connect("/ws") as ws:
            ws.send_text(json.dumps(LEVELS_REQUEST))
            texts.append(ws.receive_text())
    assert texts[0] == texts[1]


# --- hidden levels never appear -----------------------------------------------------------------


def test_the_list_never_carries_a_hidden_id_or_a_hidden_row(root_with_hidden, tmp_path):
    distinctive = hidden_rows()
    assert distinctive  # the fixture has rows of its own, or this test would prove nothing
    reply = ask_levels(client_for(root_with_hidden, tmp_path))
    assert [entry["id"] for entry in reply["levels"]] == list_levels("training", root_with_hidden)
    text = json.dumps(reply)
    assert "hidden" not in text and "h-01" not in text
    assert not any(row in entry["map"] for entry in reply["levels"] for row in distinctive)
    assert not any(json.dumps(row)[1:-1] in text for row in distinctive)


def test_the_route_still_carries_no_map_and_no_hidden_id(root_with_hidden, tmp_path):
    body = client_for(root_with_hidden, tmp_path).get("/api/levels").json()
    assert all(set(entry) == {"id", "tier", "width", "height", "budget"}
               for entry in body["levels"])
    assert "hidden" not in json.dumps(body)


# --- a list that cannot be built ----------------------------------------------------------------


def test_a_broken_training_level_gets_one_error_and_the_connection_stays_open(
        root_with_hidden, tmp_path):
    (root_with_hidden / "training" / "tier1" / "t1-99.txt").write_text("#####\n#@$x.#\n#####\n")
    with client_for(root_with_hidden, tmp_path).websocket_connect("/ws") as ws:
        assert send(ws, LEVELS_REQUEST) == UNAVAILABLE
        assert send(ws, {"type": "load", "level": "training/tier1/t1-01"})["type"] == "state"


def test_a_budgets_file_broken_after_start_gets_the_same_error(root_with_hidden, tmp_path):
    client = client_for(root_with_hidden, tmp_path)
    (root_with_hidden / "budgets.toml").write_text("[tier1\n")
    with client.websocket_connect("/ws") as ws:
        assert send(ws, LEVELS_REQUEST) == UNAVAILABLE
        assert send(ws, {"type": "ping"})["type"] == "error"
