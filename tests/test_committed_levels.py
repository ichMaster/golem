"""The committed training levels and budgets.toml. Nothing here lists or reads levels/hidden/."""

from pathlib import Path

import pytest

from golem.core.level import LevelError, parse_level
from golem.core.levels import list_levels, load_budgets, load_level

ROOT = Path(__file__).resolve().parent.parent / "levels"
TRAINING = list_levels("training", ROOT)


def test_the_first_three_tier_one_levels_are_listed():
    assert {
        "training/tier1/t1-01",
        "training/tier1/t1-02",
        "training/tier1/t1-03",
    } <= set(TRAINING)


@pytest.mark.parametrize("level_id", TRAINING)
def test_every_training_level_parses(level_id):
    level = load_level(level_id, ROOT)
    assert level.id == level_id


@pytest.mark.parametrize("level_id", [i for i in TRAINING if i.split("/")[1] == "tier1"])
def test_tier_one_levels_have_one_box(level_id):
    assert len(load_level(level_id, ROOT).boxes) == 1


def test_the_committed_budgets_define_three_tiers():
    assert set(load_budgets(ROOT)) == {"tier1", "tier2", "tier3"}


def test_every_tier_with_training_levels_has_a_budget():
    tiers = {level_id.split("/")[1] for level_id in TRAINING}
    assert tiers <= set(load_budgets(ROOT))


def test_a_malformed_copy_of_a_committed_level_names_line_and_column():
    text = (ROOT / "training" / "tier1" / "t1-01.txt").read_text(encoding="utf-8")
    broken = text.replace("$", "x")
    with pytest.raises(LevelError) as caught:
        parse_level(broken, "training/tier1/t1-01")
    assert (caught.value.line, caught.value.column) == (4, 4)
