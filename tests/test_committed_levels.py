"""The committed training levels and budgets.toml. Nothing here lists or reads levels/hidden/."""

from pathlib import Path

import pytest

from golem.core.level import LevelError, parse_level
from golem.core.levels import list_levels, load_budgets, load_level

ROOT = Path(__file__).resolve().parent.parent / "levels"
TRAINING = list_levels("training", ROOT)


def test_the_training_set_is_the_ten_levels_of_tiers_one_and_two():
    assert TRAINING == [
        *(f"training/tier1/t1-0{n}" for n in range(1, 6)),
        *(f"training/tier2/t2-0{n}" for n in range(1, 6)),
    ]


@pytest.mark.parametrize("level_id", TRAINING)
def test_every_training_level_parses(level_id):
    level = load_level(level_id, ROOT)
    assert level.id == level_id
    assert len(level.boxes) == len(level.goals)


@pytest.mark.parametrize("level_id", [i for i in TRAINING if i.split("/")[1] == "tier1"])
def test_tier_one_levels_have_one_box(level_id):
    assert len(load_level(level_id, ROOT).boxes) == 1


@pytest.mark.parametrize("level_id", [i for i in TRAINING if i.split("/")[1] == "tier2"])
def test_tier_two_levels_have_several_boxes(level_id):
    assert len(load_level(level_id, ROOT).boxes) > 1


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
