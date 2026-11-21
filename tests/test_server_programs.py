"""The program routes (v2.4, a contract; the swap from v2.5): list, source and run, by name from
one folder only; training levels only, with hidden and unknown ids refused alike. In-process, real
lupa."""

import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from golem.core.levels import budget_for, load_budgets, load_level
from golem.interp.config import InterpSettings
from golem.interp.run import run_with_frames
from golem.server.app import create_app
from golem.server.config import Settings

REPO = Path(__file__).resolve().parent.parent
LEVELS = REPO / "levels"
PROGRAMS = REPO / "programs"
HIDDEN_FIXTURE = REPO / "tests" / "fixtures" / "hidden" / "tier1" / "h-01.txt"
T1 = "training/tier1/t1-01"
UNKNOWN_LEVEL = {"error": "unknown_level", "detail": "unknown level"}
UNKNOWN_PROGRAM = {"error": "not_found", "detail": "unknown program"}


@pytest.fixture
def folder(tmp_path) -> Path:
    copy = tmp_path / "programs"
    shutil.copytree(PROGRAMS, copy)
    return copy


def client_for(tmp_path: Path, folder: Path, levels_dir: Path = LEVELS) -> TestClient:
    settings = Settings("127.0.0.1", 8700, levels_dir, tmp_path / "logs", programs_dir=folder)
    return TestClient(create_app(settings))


def run(client: TestClient, name: str, body) -> tuple[int, dict]:
    response = client.post(f"/api/programs/{name}/run", json=body)
    return response.status_code, response.json()


def test_the_list_and_the_source(tmp_path, folder):
    client = client_for(tmp_path, folder)
    listing = client.get("/api/programs").json()["programs"]
    assert [p["name"] for p in listing] == sorted(p.name for p in folder.glob("*.lua"))
    assert set(listing[0]) == {"name", "description", "size"}
    body = client.get("/api/programs/t1_solver.lua").json()
    assert body == {"name": "t1_solver.lua",
                    "source": (folder / "t1_solver.lua").read_text(encoding="utf-8")}


def test_a_run_returns_the_report_and_the_drivers_frames(tmp_path, folder):
    status, body = run(client_for(tmp_path, folder), "t1_solver.lua", {"level": T1})
    assert status == 200 and set(body) == {"report", "frames"}
    assert body["report"]["status"] == "solved"
    level = load_level(T1, LEVELS)
    source = (folder / "t1_solver.lua").read_text(encoding="utf-8")
    report, frames = run_with_frames(level, budget_for(T1, load_budgets(LEVELS)), source,
                                     InterpSettings())
    assert body == {"report": report, "frames": frames}


def test_two_identical_runs_give_byte_identical_json(tmp_path, folder):
    client = client_for(tmp_path, folder)
    first = client.post("/api/programs/explorer.lua/run", json={"level": T1}).content
    assert first == client.post("/api/programs/explorer.lua/run", json={"level": T1}).content


@pytest.mark.parametrize(
    "name", ["missing.lua", "..%2fpyproject.toml", "%2e%2e%2fpyproject.toml", "notes.txt",
             "Upper.lua", "link.lua"])
def test_anything_but_a_program_in_the_folder_is_not_found(tmp_path, folder, name):
    (folder / "notes.txt").write_text("not a program\n", encoding="utf-8")
    (folder / "Upper.lua").write_text("-- upper case\n", encoding="utf-8")
    outside = tmp_path / "secret.lua"
    outside.write_text("-- SECRET outside the folder\n", encoding="utf-8")
    (folder / "link.lua").symlink_to(outside)
    client = client_for(tmp_path, folder)
    for response in (client.get(f"/api/programs/{name}"),
                     client.post(f"/api/programs/{name}/run", json={"level": T1})):
        assert response.status_code == 404, name
        assert set(response.json()) == {"error", "detail"}
        assert "SECRET" not in response.text and "[project]" not in response.text


@pytest.mark.parametrize(
    "body",
    [{"level": "hidden/tier1/h-01"}, {"level": "training/tier1/missing"}, {}, {"level": 5},
     {"level": None}, None],
)
def test_hidden_unknown_missing_and_odd_levels_are_refused_alike(
        tmp_path, folder, root_with_hidden, body):
    status, reply = run(client_for(tmp_path, folder, root_with_hidden), "t1_solver.lua", body)
    assert (status, reply) == (404, UNKNOWN_LEVEL)
    text = json.dumps(reply)
    for line in HIDDEN_FIXTURE.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith(";"):
            assert line not in text


@pytest.mark.parametrize("body", ["a string", [1, 2]])
def test_a_body_that_is_not_an_object_is_a_bad_request(tmp_path, folder, body):
    status, reply = run(client_for(tmp_path, folder), "t1_solver.lua", body)
    assert status == 422 and reply["error"] == "bad_request"


def test_an_unknown_program_is_refused_before_the_level(tmp_path, folder):
    status, reply = run(client_for(tmp_path, folder), "missing.lua", {"level": "hidden/x/y"})
    assert (status, reply) == (404, UNKNOWN_PROGRAM)


def test_a_program_that_is_not_utf8_is_refused(tmp_path, folder):
    (folder / "binary.lua").write_bytes(b"\xff\xfe\x00 not text")
    client = client_for(tmp_path, folder)
    assert client.get("/api/programs/binary.lua").status_code == 422
    status, reply = run(client, "binary.lua", {"level": T1})
    assert status == 422 and reply["error"] == "bad_program"


def test_an_edited_or_added_program_is_served_without_a_restart(tmp_path, folder):
    client = client_for(tmp_path, folder)
    (folder / "fresh.lua").write_text("-- Added later.\ngive_up('first')\n", encoding="utf-8")
    assert "fresh.lua" in [p["name"] for p in client.get("/api/programs").json()["programs"]]
    assert run(client, "fresh.lua", {"level": T1})[1]["report"]["error"] == "first"
    (folder / "fresh.lua").write_text("-- Edited.\ngive_up('second')\n", encoding="utf-8")
    assert client.get("/api/programs/fresh.lua").json()["source"].startswith("-- Edited.")
    assert run(client, "fresh.lua", {"level": T1})[1]["report"]["error"] == "second"


def test_without_a_programs_folder_nothing_is_listed(tmp_path):
    client = client_for(tmp_path, None)
    assert client.get("/api/programs").json() == {"programs": []}
    assert client.get("/api/programs/t1_solver.lua").json() == UNKNOWN_PROGRAM


# --- the swap (v2.5): a second program, swapped in when the first one gives up or returns -------

FIXTURES = REPO / "tests" / "fixtures" / "programs"


@pytest.fixture
def swap_folder(folder) -> Path:
    for name in ("explore.lua", "finish.lua"):
        shutil.copy(FIXTURES / name, folder / name)
    return folder


def test_a_run_with_a_swap_returns_the_drivers_report_and_frames(tmp_path, swap_folder):
    status, body = run(client_for(tmp_path, swap_folder), "explore.lua",
                       {"level": T1, "swap": "finish.lua"})
    assert status == 200
    assert (body["report"]["status"], body["report"]["versions"]) == ("solved", [1, 2])
    level = load_level(T1, LEVELS)
    report, frames = run_with_frames(
        level, budget_for(T1, load_budgets(LEVELS)),
        (FIXTURES / "explore.lua").read_text(encoding="utf-8"), InterpSettings(),
        second=(FIXTURES / "finish.lua").read_text(encoding="utf-8"))
    assert body == {"report": report, "frames": frames}
    swaps = [f for f in body["frames"][1:] if f["dir"] is None]
    assert len(swaps) == 1 and swaps[0]["version"] == 2


def test_a_null_swap_is_no_swap(tmp_path, swap_folder):
    client = client_for(tmp_path, swap_folder)
    plain = client.post("/api/programs/explore.lua/run", json={"level": T1}).content
    assert client.post("/api/programs/explore.lua/run",
                       json={"level": T1, "swap": None}).content == plain
    assert json.loads(plain)["report"]["versions"] == [1]


def test_a_first_program_that_solves_is_never_swapped(tmp_path, swap_folder):
    status, body = run(client_for(tmp_path, swap_folder), "t1_solver.lua",
                       {"level": T1, "swap": "finish.lua"})
    assert (status, body["report"]["status"], body["report"]["versions"]) == (200, "solved", [1])
    assert {f["version"] for f in body["frames"]} == {1}


@pytest.mark.parametrize("swap", ["missing.lua", "../finish.lua", "Finish.lua", "", 5, ["x"],
                                  {"name": "finish.lua"}, False])
def test_an_unknown_or_invalid_swap_program_is_not_found_before_the_level(
        tmp_path, swap_folder, swap):
    status, reply = run(client_for(tmp_path, swap_folder), "explore.lua",
                        {"level": "hidden/tier1/h-01", "swap": swap})
    assert (status, reply) == (404, UNKNOWN_PROGRAM)


def test_a_swap_program_that_is_not_utf8_is_refused(tmp_path, swap_folder):
    (swap_folder / "binary.lua").write_bytes(b"\xff\xfe\x00 not text")
    status, reply = run(client_for(tmp_path, swap_folder), "explore.lua",
                        {"level": T1, "swap": "binary.lua"})
    assert status == 422 and reply["error"] == "bad_program"


def test_a_hidden_level_is_refused_with_a_valid_swap_too(tmp_path, swap_folder, root_with_hidden):
    status, reply = run(client_for(tmp_path, swap_folder, root_with_hidden), "explore.lua",
                        {"level": "hidden/tier1/h-01", "swap": "finish.lua"})
    assert (status, reply) == (404, UNKNOWN_LEVEL)
    for line in HIDDEN_FIXTURE.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith(";"):
            assert line not in json.dumps(reply)


def test_two_identical_swapped_runs_give_byte_identical_json(tmp_path, swap_folder):
    client = client_for(tmp_path, swap_folder)
    body = {"level": T1, "swap": "finish.lua"}
    first = client.post("/api/programs/explore.lua/run", json=body).content
    assert first == client.post("/api/programs/explore.lua/run", json=body).content
