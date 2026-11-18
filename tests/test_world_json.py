"""Saving and restoring a world (the saved world's JSON shape is a contract), and the state key."""

import json

import pytest

from golem.core.level import parse_level
from golem.core.levels import Budget
from golem.core.world import World, from_json, move, new_world, state_key, to_json

TWO_BOXES = (
    "########\n"
    "#      #\n"
    "# $@$  #\n"
    "# .  . #\n"
    "########\n"
)
LEVEL = parse_level(TWO_BOXES, "test/tier1/t")


def start(steps: int = 100) -> World:
    return new_world(LEVEL, Budget(steps=steps, instructions=1000))


def play(world: World, moves: str) -> World:
    for direction in moves:
        world, _ = move(world, direction)
    return world


def saved(**changes) -> dict:
    data = to_json(play(start(), "N"))
    data.update(changes)
    return data


# --- the shape --------------------------------------------------------------------------------


def test_the_saved_shape():
    data = to_json(play(start(), "E"))
    assert data == {
        "level": "test/tier1/t",
        "robot": [2, 4],
        "boxes": [[2, 2], [2, 5]],
        "steps": 1,
        "step_budget": 100,
        "status": "playing",
        "loss_reason": None,
    }
    keys = ["level", "robot", "boxes", "steps", "step_budget", "status", "loss_reason"]
    assert list(data) == keys


def test_boxes_are_sorted_whatever_order_they_were_added_in():
    world = start()
    shuffled = World(level=LEVEL, robot=world.robot, boxes=frozenset([(2, 5), (2, 2)]),
                     steps=0, step_budget=100)
    other = World(level=LEVEL, robot=world.robot, boxes=frozenset([(2, 2), (2, 5)]),
                  steps=0, step_budget=100)
    assert json.dumps(to_json(shuffled)) == json.dumps(to_json(other))
    assert to_json(shuffled)["boxes"] == [[2, 2], [2, 5]]


# --- the round trip ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("moves", "steps", "status"),
    [
        ("", 100, "playing"),
        ("NWS", 100, "playing"),  # the west box pushed south onto a goal
        ("NN", 2, "lost"),  # the budget runs out
    ],
)
def test_round_trip(moves, steps, status):
    world = play(start(steps), moves)
    assert world.status == status
    assert from_json(to_json(world), LEVEL) == world
    assert from_json(json.loads(json.dumps(to_json(world))), LEVEL) == world


def test_round_trip_of_a_solved_and_a_deadlocked_world():
    solved = play(start(), "NWSEENES")  # west box onto (3, 2), east box onto (3, 5)
    assert solved.status == "solved"
    assert from_json(to_json(solved), LEVEL) == solved

    corner = parse_level("######\n#    #\n# @$ #\n#. ###\n######\n", "test/tier1/c")
    lost, _ = move(new_world(corner, Budget(100, 1000)), "E")
    assert (lost.status, lost.loss_reason) == ("lost", "deadlock")
    assert from_json(json.loads(json.dumps(to_json(lost))), corner) == lost


# --- refusals ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("data", "words"),
    [
        ([1, 2], "not a JSON object"),
        ({k: v for k, v in saved().items() if k != "steps"}, "missing key 'steps'"),
        (saved(extra=1), "unknown key 'extra'"),
        (saved(level="test/tier1/other"), "level"),
        (saved(robot=[0, 0]), "robot cell [0, 0] is a wall"),
        (saved(robot=[9, 1]), "robot cell [9, 1] is outside the map"),
        (saved(robot=[1]), "robot must hold"),
        (saved(robot=[1, True]), "robot must hold"),
        (saved(robot="1,2"), "robot must hold"),
        (saved(boxes=[[2, 2]]), "boxes has 1 boxes, the level 2"),
        (saved(boxes=[[2, 2], [2, 2]]), "two boxes in one cell"),
        (saved(boxes=[[2, 2], [0, 3]]), "boxes cell [0, 3] is a wall"),
        (saved(boxes="none"), "boxes must be a list"),
        (saved(robot=[2, 2]), "robot stands on a box"),
        (saved(steps=-1), "steps must be"),
        (saved(steps=1.5), "steps must be"),
        (saved(step_budget=0), "step_budget must be"),
        (saved(status="won"), "unknown status 'won'"),
        (saved(status="lost", loss_reason=None), "does not fit"),
        (saved(status="lost", loss_reason="tired"), "does not fit"),
        (saved(status="playing", loss_reason="steps"), "does not fit"),
    ],
)
def test_from_json_refuses_an_inconsistent_state(data, words):
    with pytest.raises(ValueError) as caught:
        from_json(data, LEVEL)
    assert words in str(caught.value)


def test_from_json_accepts_every_loss_reason():
    for reason in ("steps", "deadlock", "instructions"):
        world = from_json(saved(status="lost", loss_reason=reason), LEVEL)
        assert world.loss_reason == reason


# --- the state key ----------------------------------------------------------------------------


def test_state_key_ignores_the_step_count():
    there_and_back = play(start(), "NS")
    assert there_and_back.steps == 2
    assert state_key(there_and_back) == state_key(start())


def test_state_key_changes_with_the_robot_or_a_box():
    base = start()
    assert state_key(play(base, "N")) != state_key(base)
    pushed = play(base, "E")  # the east box moves one cell
    assert state_key(pushed)[1] != state_key(base)[1]
    assert hash(state_key(base)) == hash(state_key(play(base, "NS")))


# --- code review #1: a saved world cannot put the robot or a box outside the walls ---------------

RAGGED = parse_level("  ####\n###  #\n#@$. #\n######\n", "test/tier1/ragged")


@pytest.mark.parametrize("field", ["robot", "boxes"])
@pytest.mark.parametrize("cell", [[0, 0], [0, 1], [9, 9], [-1, 2]])
def test_from_json_refuses_a_cell_outside_the_walls(field, cell):
    data = to_json(new_world(RAGGED, Budget(100, 1000)))
    data[field] = cell if field == "robot" else [cell]
    with pytest.raises(ValueError) as caught:
        from_json(data, RAGGED)
    assert f"{field} cell {cell} is outside the map" in str(caught.value)
