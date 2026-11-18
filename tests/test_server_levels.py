"""GET /api/levels: the training levels with their tier, size and budgets (a contract)."""

from pathlib import Path

from fastapi.testclient import TestClient

from golem.core.level import parse_level
from golem.core.levels import budget_for, list_levels, load_budgets, load_level
from golem.server.app import create_app
from golem.server.config import Settings

REPO = Path(__file__).resolve().parent.parent
LEVELS = REPO / "levels"
HIDDEN_FIXTURE = REPO / "tests" / "fixtures" / "hidden" / "tier1" / "h-01.txt"


def client_for(levels_dir: Path, tmp_path: Path) -> TestClient:
    settings = Settings("127.0.0.1", 8700, levels_dir, tmp_path / "logs")
    return TestClient(create_app(settings))


def test_the_fixture_hidden_level_is_a_valid_level():
    parse_level(HIDDEN_FIXTURE.read_text(encoding="utf-8"), "hidden/tier1/h-01")


def test_levels_match_the_level_files_and_the_budgets(tmp_path):
    response = client_for(LEVELS, tmp_path).get("/api/levels")
    assert response.status_code == 200
    budgets = load_budgets(LEVELS)
    expected = []
    for level_id in list_levels("training", LEVELS):
        level = load_level(level_id, LEVELS)
        budget = budget_for(level_id, budgets)
        expected.append({
            "id": level_id,
            "tier": level_id.split("/")[1],
            "width": level.width,
            "height": level.height,
            "budget": {"steps": budget.steps, "instructions": budget.instructions},
        })
    assert response.json() == {"levels": expected}
    ids = [entry["id"] for entry in response.json()["levels"]]
    assert ids == sorted(ids)
    assert {"training/tier1/t1-01", "training/tier1/t1-02", "training/tier1/t1-03"} <= set(ids)


def test_the_shape_of_one_entry(tmp_path):
    first = client_for(LEVELS, tmp_path).get("/api/levels").json()["levels"][0]
    assert first == {
        "id": "training/tier1/t1-01",
        "tier": "tier1",
        "width": 7,
        "height": 5,
        "budget": {"steps": 200, "instructions": 1_000_000},
    }


def test_hidden_levels_never_appear(root_with_hidden, tmp_path):
    response = client_for(root_with_hidden, tmp_path).get("/api/levels")
    assert response.status_code == 200
    body = response.text
    assert "hidden" not in body
    assert "h-01" not in body
    for line in HIDDEN_FIXTURE.read_text(encoding="utf-8").splitlines():
        if not line.startswith(";"):
            assert line not in body


def test_a_broken_training_level_gives_a_level_error(root_with_hidden, tmp_path):
    (root_with_hidden / "training" / "tier1" / "t1-99.txt").write_text("#####\n#@$x.#\n#####\n")
    response = client_for(root_with_hidden, tmp_path).get("/api/levels")
    assert response.status_code == 500
    assert response.json() == {
        "error": "level_error",
        "detail": "training/tier1/t1-99:2:4: unknown character 'x'",
    }


def test_a_budgets_file_broken_after_start_gives_a_budgets_error(root_with_hidden, tmp_path):
    client = client_for(root_with_hidden, tmp_path)
    (root_with_hidden / "budgets.toml").write_text("[tier1\n")
    response = client.get("/api/levels")
    assert response.status_code == 500
    assert response.json()["error"] == "budgets_error"
