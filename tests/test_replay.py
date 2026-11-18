"""Replaying a move string: the final world and the list of states."""

import pytest

from golem.core.level import parse_level
from golem.core.levels import Budget
from golem.core.replay import play, replay
from golem.core.world import new_world, render

ROOM = parse_level(
    "#######\n"
    "#     #\n"
    "# @$ .#\n"
    "#     #\n"
    "#######\n",
    "test/tier1/room",
)
BUDGET = Budget(steps=100, instructions=1000)


def test_a_replay_that_solves_the_level():
    final, states = replay(ROOM, "NSEE", BUDGET)
    assert final.status == "solved"
    assert final.steps == 4
    assert len(states) == 5
    assert states[0] == new_world(ROOM, BUDGET)
    assert states[-1] is final
    assert [state.steps for state in states] == [0, 1, 2, 3, 4]


def test_the_states_follow_the_moves():
    _, states = replay(ROOM, "E", BUDGET)
    assert render(states[0])[2] == "# @$ .#"
    assert render(states[1])[2] == "#  @$.#"


def test_the_empty_string_gives_the_start_only():
    final, states = replay(ROOM, "", BUDGET)
    assert states == [new_world(ROOM, BUDGET)]
    assert final == states[0]


@pytest.mark.parametrize(("moves", "position"), [("NX", 2), ("e", 1), ("NN S", 3), ("EEN\n", 4)])
def test_an_invalid_character_is_refused_before_any_move(moves, position):
    with pytest.raises(ValueError) as caught:
        replay(ROOM, moves, BUDGET)
    assert f"at position {position}" in str(caught.value)


def test_moves_must_be_a_string():
    with pytest.raises(ValueError):
        replay(ROOM, ["N", "E"], BUDGET)  # type: ignore[arg-type]


def test_moves_after_the_end_add_equal_states():
    final, states = replay(ROOM, "EENNW", BUDGET)
    assert final.status == "solved"
    assert final.steps == 2
    assert len(states) == 6
    assert states[2] == states[3] == states[4] == states[5]


def test_play_continues_from_a_world_in_the_middle():
    middle, _ = replay(ROOM, "NS", BUDGET)
    final, states = play(middle, "EE")
    assert states[0] is middle
    assert final.status == "solved"
    assert final.steps == 4
    assert final == replay(ROOM, "NSEE", BUDGET)[0]
