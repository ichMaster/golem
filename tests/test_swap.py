"""The swap fixtures (v2.5): explore.lua maps a tier-one level into `memory` and gives up, and
finish.lua, swapped in on that give-up, solves the level from the map alone. Real lupa, the three
tier-one levels."""

import json
from pathlib import Path

import pytest

from golem.core.levels import budget_for, load_budgets, load_level
from golem.core.world import new_world
from golem.interp.config import InterpSettings
from golem.interp.run import Run, frame, swap

REPO = Path(__file__).resolve().parent.parent
LEVELS = REPO / "levels"
PROGRAMS = REPO / "tests" / "fixtures" / "programs"
TIER1 = ["training/tier1/t1-01", "training/tier1/t1-02", "training/tier1/t1-03"]
EXPLORE = (PROGRAMS / "explore.lua").read_text(encoding="utf-8")
FINISH = (PROGRAMS / "finish.lua").read_text(encoding="utf-8")


def framed_run(level_id: str, first: str, *more: str) -> tuple[Run, list[dict]]:
    """Run ``first``, swap in each of ``more`` when the program before it stops, keep the frames."""
    level = load_level(level_id, LEVELS)
    budget = budget_for(level_id, load_budgets(LEVELS))
    frames = [frame(new_world(level, budget), None, None)]
    run = Run(level, budget, InterpSettings(),
              on_move=lambda world, d, moved: frames.append(frame(world, d, moved)))
    run.start(first)
    run.drive()
    for source in more:
        swap(run, source)
        run.drive()
    return run, frames


@pytest.mark.parametrize("level_id", TIER1)
def test_explore_alone_maps_the_level_and_gives_up(level_id):
    report = framed_run(level_id, EXPLORE)[0].report()
    assert (report["status"], report["reason"], report["error"]) == ("failed", "give_up", "mapped")
    assert report["versions"] == [1]


@pytest.mark.parametrize("level_id", TIER1)
def test_finish_swapped_in_after_explore_solves_the_level(level_id):
    run, _ = framed_run(level_id, EXPLORE, FINISH)
    report = run.report()
    assert (report["status"], report["reason"], report["error"]) == ("solved", None, None)
    assert report["versions"] == [1, 2]


@pytest.mark.parametrize("level_id", TIER1)
def test_the_step_count_continues_from_the_swap_point(level_id):
    explored, explore_frames = framed_run(level_id, EXPLORE)
    swapped, frames = framed_run(level_id, EXPLORE, FINISH)
    explore_steps = explored.report()["steps"]
    # the swapped run replays exploration exactly, then the finish moves follow with no gap
    assert frames[:len(explore_frames)] == explore_frames
    assert [f["step"] for f in frames] == list(range(len(frames)))
    finish_moves = len(frames) - len(explore_frames)
    assert finish_moves > 0
    assert swapped.report()["steps"] == explore_steps + finish_moves


def test_finish_alone_finds_no_map_and_never_looks():
    report = framed_run(TIER1[0], FINISH)[0].report()
    assert (report["status"], report["reason"], report["error"]) == (
        "failed", "give_up", "no map in memory")
    assert "look(" not in FINISH


@pytest.mark.parametrize("level_id", TIER1)
def test_the_swapped_run_twice_gives_byte_identical_reports_and_frames(level_id):
    def once() -> str:
        run, frames = framed_run(level_id, EXPLORE, FINISH)
        return json.dumps([run.report(), frames])

    assert once() == once()
