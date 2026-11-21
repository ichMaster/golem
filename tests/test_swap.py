"""The swap fixtures (v2.5): explore.lua maps a tier-one level into `memory` and gives up, and
finish.lua, swapped in on that give-up, solves the level from the map alone. The frames mark the
swap point. Real lupa, the three tier-one levels."""

import json
from pathlib import Path

import pytest

from golem.core.levels import budget_for, load_budgets, load_level
from golem.interp.config import InterpSettings
from golem.interp.run import run_with_frames

REPO = Path(__file__).resolve().parent.parent
LEVELS = REPO / "levels"
PROGRAMS = REPO / "tests" / "fixtures" / "programs"
TIER1 = ["training/tier1/t1-01", "training/tier1/t1-02", "training/tier1/t1-03"]
EXPLORE = (PROGRAMS / "explore.lua").read_text(encoding="utf-8")
FINISH = (PROGRAMS / "finish.lua").read_text(encoding="utf-8")


def framed(level_id: str, first: str, second: str | None = None) -> tuple[dict, list, list]:
    """``first`` on the level, with ``second`` swapped in when it gives up or returns: the report,
    the frames and the swaps."""
    level = load_level(level_id, LEVELS)
    budget = budget_for(level_id, load_budgets(LEVELS))
    return run_with_frames(level, budget, first, InterpSettings(), second=second)


@pytest.mark.parametrize("level_id", TIER1)
def test_explore_alone_maps_the_level_and_gives_up(level_id):
    report, frames, swaps = framed(level_id, EXPLORE)
    assert (report["status"], report["reason"], report["error"]) == ("failed", "give_up", "mapped")
    assert report["versions"] == [1] and {f["version"] for f in frames} == {1} and swaps == []


@pytest.mark.parametrize("level_id", TIER1)
def test_finish_swapped_in_after_explore_solves_the_level(level_id):
    report, _, _ = framed(level_id, EXPLORE, FINISH)
    assert (report["status"], report["reason"], report["error"]) == ("solved", None, None)
    assert report["versions"] == [1, 2]


@pytest.mark.parametrize("level_id", TIER1)
def test_the_swap_log_says_where_and_why_the_second_program_took_over(level_id):
    explored, _, _ = framed(level_id, EXPLORE)
    _, _, swaps = framed(level_id, EXPLORE, FINISH)
    assert swaps == [{
        "step": explored["steps"], "version": 2, "instructions": explored["instructions"],
        "ended": {"status": "failed", "reason": "give_up", "error": "mapped"},
    }]


@pytest.mark.parametrize("level_id", TIER1)
def test_the_frames_mark_the_swap_and_the_steps_continue_from_it(level_id):
    explored, explore_frames, _ = framed(level_id, EXPLORE)
    swapped, frames, _ = framed(level_id, EXPLORE, FINISH)
    point = len(explore_frames)
    # the swapped run replays exploration exactly, then one swap frame, then the finish moves
    assert frames[:point] == explore_frames
    swap_frame = frames[point]
    assert swap_frame == {**explore_frames[-1], "dir": None, "moved": None, "version": 2}
    assert swap_frame["step"] == explored["steps"]
    after = frames[point + 1:]
    assert after and {f["version"] for f in after} == {2} and all(f["dir"] for f in after)
    assert [f["step"] for f in after] == list(range(explored["steps"] + 1, swapped["steps"] + 1))
    assert swapped["steps"] == explored["steps"] + len(after)


def test_finish_alone_finds_no_map_and_never_looks():
    report, _, _ = framed(TIER1[0], FINISH)
    assert (report["status"], report["reason"], report["error"]) == (
        "failed", "give_up", "no map in memory")
    assert "look(" not in FINISH


@pytest.mark.parametrize(
    "first", ['move("E") move("E")', "while true do end", 'error("boom")'],
    ids=["solved", "lost", "lua_error"])
def test_a_first_program_that_does_not_give_up_is_never_swapped(first):
    report, frames, swaps = framed(TIER1[0], first, FINISH)
    assert report["versions"] == [1] and {f["version"] for f in frames} == {1} and swaps == []


@pytest.mark.parametrize("level_id", TIER1)
def test_the_swapped_run_twice_gives_byte_identical_reports_and_frames(level_id):
    assert json.dumps(framed(level_id, EXPLORE, FINISH)) == json.dumps(
        framed(level_id, EXPLORE, FINISH))
