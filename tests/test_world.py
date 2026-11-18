"""The rules: moves, pushes, steps, the step budget, the win and the corner rule (contracts)."""

import dataclasses

import pytest

from golem.core.level import parse_level
from golem.core.levels import Budget, BudgetsError, budget_for
from golem.core.world import World, move, new_world

ROOM = (
    "#######\n"
    "#     #\n"
    "# @$ .#\n"
    "#     #\n"
    "#######\n"
)


def world_of(text: str, steps: int = 100) -> World:
    return new_world(parse_level(text, "test/tier1/t"), Budget(steps=steps, instructions=1000))


def play(world: World, moves: str) -> tuple[World, list[bool]]:
    results = []
    for direction in moves:
        world, moved = move(world, direction)
        results.append(moved)
    return world, results


# --- the starting state -------------------------------------------------------------------------


def test_new_world_starts_from_the_level():
    world = world_of(ROOM, steps=50)
    assert world.robot == (2, 2)
    assert world.boxes == frozenset({(2, 3)})
    assert (world.steps, world.step_budget) == (0, 50)
    assert (world.status, world.loss_reason) == ("playing", None)


def test_a_level_whose_boxes_start_on_goals_is_solved_at_once():
    world = world_of("#####\n#@* #\n#####\n")
    assert world.status == "solved"


def test_the_world_is_immutable_and_move_never_changes_its_argument():
    world = world_of(ROOM)
    before = dataclasses.replace(world)
    move(world, "E")
    assert world == before
    with pytest.raises(dataclasses.FrozenInstanceError):
        world.steps = 5  # type: ignore[misc]


# --- moves -------------------------------------------------------------------------------------


def test_a_move_onto_floor():
    world, moved = move(world_of(ROOM), "N")
    assert moved is True
    assert world.robot == (1, 2)
    assert world.steps == 1


def test_a_move_onto_a_goal():
    world, moved = move(world_of("#######\n#@. $ #\n#######\n"), "E")
    assert moved is True
    assert world.robot == (1, 2)
    assert world.status == "playing"


def test_a_move_into_a_wall_changes_nothing_but_counts_a_step():
    start = world_of("#####\n#@$.#\n#####\n")
    world, moved = move(start, "N")
    assert moved is False
    assert (world.robot, world.boxes) == (start.robot, start.boxes)
    assert world.steps == 1


# --- pushes ------------------------------------------------------------------------------------


def test_a_push_onto_floor():
    world, moved = move(world_of(ROOM), "E")
    assert moved is True
    assert world.robot == (2, 3)
    assert world.boxes == frozenset({(2, 4)})


def test_a_push_onto_a_goal_solves_the_level():
    world, results = play(world_of(ROOM), "EE")
    assert results == [True, True]
    assert world.boxes == frozenset({(2, 5)})
    assert (world.status, world.loss_reason) == ("solved", None)


def test_a_push_into_a_wall_is_refused():
    start = world_of("######\n#@$# #\n#   .#\n######\n")
    world, moved = move(start, "E")
    assert moved is False
    assert (world.robot, world.boxes) == (start.robot, start.boxes)
    assert world.steps == 1


def test_a_push_into_another_box_is_refused():
    start = world_of("#######\n#@$$..#\n#######\n")
    world, moved = move(start, "E")
    assert moved is False
    assert (world.robot, world.boxes) == (start.robot, start.boxes)
    assert world.steps == 1


def test_the_robot_never_pulls_a_box():
    world, _ = play(world_of(ROOM), "E")  # box (2, 4), robot (2, 3)
    world, moved = move(world, "W")
    assert moved is True
    assert world.robot == (2, 2)
    assert world.boxes == frozenset({(2, 4)})


# --- steps and the step budget -----------------------------------------------------------------


def test_every_move_counts_one_step_moved_or_not():
    world, results = play(world_of(ROOM), "NSWWN")
    assert results == [True, True, True, False, True]
    assert world.steps == 5


def test_reaching_the_step_budget_loses_on_steps():
    world, results = play(world_of(ROOM, steps=3), "NSN")
    assert results == [True, True, True]
    assert (world.steps, world.status, world.loss_reason) == (3, "lost", "steps")


def test_solving_on_the_last_step_of_the_budget_wins():
    world, _ = play(world_of(ROOM, steps=2), "EE")
    assert (world.status, world.loss_reason) == ("solved", None)


@pytest.mark.parametrize(("moves", "steps"), [("EE", 100), ("NN", 2)])
def test_no_move_and_no_step_after_the_level_ends(moves, steps):
    ended, _ = play(world_of(ROOM, steps=steps), moves)
    assert ended.status in ("solved", "lost")
    world, moved = move(ended, "S")
    assert moved is False
    assert world is ended


# --- directions --------------------------------------------------------------------------------


@pytest.mark.parametrize("direction", ["X", "n", "", "NE", None, 1, ["N"]])
def test_an_invalid_direction_is_an_error(direction):
    with pytest.raises(ValueError):
        move(world_of(ROOM), direction)


def test_an_invalid_direction_is_an_error_even_after_the_end():
    ended, _ = play(world_of(ROOM), "EE")
    with pytest.raises(ValueError):
        move(ended, "Q")


# --- budgets per tier --------------------------------------------------------------------------


def test_budget_for_takes_the_tier_from_the_id():
    budgets = {"tier1": Budget(200, 1000), "tier2": Budget(1000, 5000)}
    assert budget_for("training/tier2/t2-01", budgets) == Budget(1000, 5000)


def test_budget_for_a_tier_without_a_budget_is_an_error():
    with pytest.raises(BudgetsError) as caught:
        budget_for("training/tier9/x", {"tier1": Budget(200, 1000)})
    assert "tier9" in str(caught.value)
