"""The short report (v2.3, a contract): the run report's first six fields, from plain data."""

from pathlib import Path

import pytest

from golem.core.levels import budget_for, load_budgets, load_level
from golem.core.replay import replay
from golem.interp.report import (
    INTERNAL,
    LOST_ON_INSTRUCTIONS,
    OUT_OF_MEMORY,
    PROGRAM_ENDED,
    REPORT_KEYS,
    Ending,
    from_world,
    gave_up,
    lua_error,
    short_report,
)

LEVELS = Path(__file__).resolve().parent.parent / "levels"
T1 = "training/tier1/t1-01"


def world_after(moves: str):
    final, _ = replay(load_level(T1, LEVELS), moves, budget_for(T1, load_budgets(LEVELS)))
    return final


@pytest.mark.parametrize(
    ("ending", "expected"),
    [
        (Ending("solved"), ("solved", None, None)),
        (Ending("lost", "steps"), ("lost", "steps", None)),
        (Ending("lost", "deadlock"), ("lost", "deadlock", None)),
        (LOST_ON_INSTRUCTIONS, ("lost", "instructions", None)),
        (gave_up("x"), ("failed", "give_up", "x")),
        (PROGRAM_ENDED, ("failed", "give_up", "program ended")),
        (lua_error("program:3: boom"), ("failed", "error", "program:3: boom")),
        (OUT_OF_MEMORY, ("failed", "error", "not enough memory")),
        (INTERNAL, ("failed", "internal", "internal error")),
    ],
)
def test_every_ending_fills_the_report_in_the_contracts_key_order(ending, expected):
    report = short_report(T1, world_after("E"), 3000, ending)
    assert tuple(report) == REPORT_KEYS == (
        "level", "status", "reason", "steps", "instructions", "error")
    assert (report["level"], report["steps"], report["instructions"]) == (T1, 1, 3000)
    assert (report["status"], report["reason"], report["error"]) == expected


def test_the_core_decides_a_solved_or_lost_world():
    assert from_world(world_after("EE")) == Ending("solved")
    assert from_world(world_after("SENWNEE")) == Ending("lost", "deadlock")
    with pytest.raises(ValueError):
        from_world(world_after("E"))


def test_a_give_up_reason_is_cut_to_200_characters():
    assert gave_up("é" * 500).error == "é" * 200
