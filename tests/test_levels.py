"""Level ids, listing and loading, and the budgets.toml schema (contracts)."""

from pathlib import Path

import pytest

from golem.core.levels import (
    Budget,
    BudgetsError,
    UnknownLevel,
    levels_root,
    list_levels,
    load_budgets,
    load_level,
)

LEVEL = "#####\n#@$.#\n#####\n"


def write(root: Path, relative: str, text: str = LEVEL) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def root(tmp_path: Path) -> Path:
    for relative in [
        "training/tier2/t2-01.txt",
        "training/tier1/t1-02.txt",
        "training/tier1/t1-01.txt",
        "training/tier1/notes.md",  # not .txt
        "training/tier1/Upper.txt",  # not a valid name
        "training/drafts/d-01.txt",  # not a tier directory
        "training/tier1/sub/s-01.txt",  # nested below a tier
        "other/tier1/o-01.txt",  # another set
    ]:
        write(tmp_path, relative)
    return tmp_path


# --- listing ----------------------------------------------------------------------------------


def test_listing_is_sorted_and_skips_what_is_not_a_level(root):
    assert list_levels("training", root) == [
        "training/tier1/t1-01",
        "training/tier1/t1-02",
        "training/tier2/t2-01",
    ]


def test_listing_one_set_only(root):
    assert list_levels("other", root) == ["other/tier1/o-01"]


def test_listing_a_missing_set_is_empty(root):
    assert list_levels("nothing", root) == []


@pytest.mark.parametrize("set_name", ["..", "", "Training", "a/b", "/abs"])
def test_listing_refuses_an_invalid_set_name(root, set_name):
    with pytest.raises(ValueError):
        list_levels(set_name, root)


# --- loading ----------------------------------------------------------------------------------


def test_loading_by_id(root):
    level = load_level("training/tier1/t1-02", root)
    assert level.id == "training/tier1/t1-02"
    assert level.robot == (1, 1)


@pytest.mark.parametrize(
    "level_id",
    [
        "training/tier1/nope",  # well formed, not in the listing
        "training/drafts/d-01",  # the file exists, but not in a tier directory
        "training/tier1/Upper",  # the file exists, but the name is invalid
        "training/tier1/notes",  # only notes.md exists
        "training/../t1-01",
        "training/tier1/..",
        "../training/tier1/t1-01",
        "/training/tier1/t1-01",
        "training/tier1",
        "training/tier1/t1-01/x",
        "training/tier1/sub/s-01",
        "training\\tier1\\t1-01",
        "training/tier1/t1-01\\",
        "training/tier1/t1-01.txt",
        "",
    ],
)
def test_loading_refuses_ids_outside_the_listing(root, level_id):
    with pytest.raises(UnknownLevel) as caught:
        load_level(level_id, root)
    assert caught.value.level_id == level_id
    assert str(root) not in str(caught.value)


def test_unknown_level_is_a_lookup_error(root):
    with pytest.raises(LookupError):
        load_level("training/tier9/x", root)


# --- levels root --------------------------------------------------------------------------------


def test_levels_root_defaults_to_levels(monkeypatch):
    monkeypatch.delenv("GOLEM_LEVELS_DIR", raising=False)
    assert levels_root() == Path("levels")


def test_levels_root_from_the_environment(monkeypatch, root):
    monkeypatch.setenv("GOLEM_LEVELS_DIR", str(root))
    assert levels_root() == root
    assert list_levels("other") == ["other/tier1/o-01"]


# --- budgets.toml -------------------------------------------------------------------------------


def write_budgets(root: Path, text: str) -> None:
    (root / "budgets.toml").write_text(text, encoding="utf-8")


def test_budgets_schema(tmp_path):
    write_budgets(
        tmp_path,
        "# comment\n"
        "[tier2]\nsteps = 1000\ninstructions = 5_000_000\n"
        "[tier1]\nsteps = 200\ninstructions = 1_000_000\n",
    )
    budgets = load_budgets(tmp_path)
    assert budgets == {
        "tier1": Budget(steps=200, instructions=1_000_000),
        "tier2": Budget(steps=1000, instructions=5_000_000),
    }
    assert list(budgets) == ["tier1", "tier2"]


@pytest.mark.parametrize(
    ("text", "names"),
    [
        ("[tier1]\ninstructions = 10\n", ["tier1", "steps"]),
        ("[tier1]\nsteps = 10\n", ["tier1", "instructions"]),
        ("[tier1]\nsteps = 10\ninstructions = 10\nmemory = 5\n", ["tier1", "memory"]),
        ('[tier1]\nsteps = "10"\ninstructions = 10\n', ["tier1", "steps"]),
        ("[tier1]\nsteps = 0\ninstructions = 10\n", ["tier1", "steps"]),
        ("[tier1]\nsteps = 10\ninstructions = -1\n", ["tier1", "instructions"]),
        ("[tier1]\nsteps = 10.0\ninstructions = 10\n", ["tier1", "steps"]),
        ("[tier1]\nsteps = true\ninstructions = 10\n", ["tier1", "steps"]),
        ("[easy]\nsteps = 10\ninstructions = 10\n", ["easy"]),
        ("tier1 = 5\n", ["tier1"]),
        ("", ["no tier"]),
        ("[tier1\n", ["budgets.toml"]),
    ],
)
def test_budgets_schema_errors_name_the_tier_and_the_key(tmp_path, text, names):
    write_budgets(tmp_path, text)
    with pytest.raises(BudgetsError) as caught:
        load_budgets(tmp_path)
    for name in names:
        assert name in str(caught.value)
