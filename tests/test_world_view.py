"""The robot's view (look, here, boxes_left) and the rendered map."""

from pathlib import Path

import pytest

from golem.core.level import parse_level
from golem.core.levels import Budget, list_levels, load_level
from golem.core.world import World, boxes_left, here, look, move, new_world, render

LEVELS = Path(__file__).resolve().parent.parent / "levels"
BUDGET = Budget(steps=100, instructions=1000)
NEIGHBOURS = {"N": (1, 2), "E": (2, 3), "S": (3, 2), "W": (2, 1)}
KIND_CHAR = {"wall": "#", "box": "$", "goal": ".", "box_on_goal": "*", "empty": " "}


def world_of(text: str) -> World:
    return new_world(parse_level(text, "test/tier1/t"), BUDGET)


def around(direction: str, kind: str) -> str:
    """A 3x3 room with the robot in the middle and `kind` in the cell towards `direction`.

    One box and one goal sit in interior corners, which are never the robot's neighbours, and a
    second goal or box keeps the counts equal.
    """
    cells = {(1, 1): "$", (3, 3): "."}
    neighbour = NEIGHBOURS[direction]
    cells[neighbour] = KIND_CHAR[kind]
    if kind == "box":
        cells[(3, 1)] = "."
    if kind == "goal":
        cells[(1, 3)] = "$"
    cells[(2, 2)] = "@"
    rows = []
    for r in range(5):
        row = ""
        for c in range(5):
            if r in (0, 4) or c in (0, 4):
                row += "#"
            else:
                row += cells.get((r, c), " ")
        rows.append(row)
    return "\n".join(rows) + "\n"


def map_lines(text: str) -> list[str]:
    """A level's map lines as render prints them: no comments, no blank lines around the map,
    `-` and `_` as spaces, no trailing spaces."""
    lines = [line for line in text.replace("\r", "").split("\n") if not line.startswith(";")]
    while lines and lines[0].strip(" ") == "":
        lines.pop(0)
    while lines and lines[-1].strip(" ") == "":
        lines.pop()
    return [line.replace("-", " ").replace("_", " ").rstrip(" ") for line in lines]


# --- look, here, boxes_left --------------------------------------------------------------------


@pytest.mark.parametrize("direction", ["N", "E", "S", "W"])
@pytest.mark.parametrize("kind", ["wall", "box", "goal", "box_on_goal", "empty"])
def test_look_names_the_neighbouring_cell(direction, kind):
    assert look(world_of(around(direction, kind)), direction) == kind


def test_look_refuses_an_invalid_direction():
    with pytest.raises(ValueError):
        look(world_of(around("N", "wall")), "up")


def test_here_on_and_off_a_goal():
    assert here(world_of("#####\n#@$.#\n#####\n")) == "empty"
    assert here(world_of("#####\n#+$ #\n#####\n")) == "goal"


def test_here_after_walking_onto_a_goal():
    world, _ = move(world_of("#######\n#@. $ #\n#######\n"), "E")
    assert here(world) == "goal"
    world, _ = move(world, "E")
    assert here(world) == "empty"


def test_boxes_left_as_a_box_reaches_a_goal_and_leaves_it():
    world = world_of("#########\n#@$.  $.#\n#########\n")
    assert boxes_left(world) == 2
    world, _ = move(world, "E")
    assert boxes_left(world) == 1
    world, _ = move(world, "E")
    assert boxes_left(world) == 2


# --- render ------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "#####\n#@$.#\n#####\n",
        "########\n#+ -_$*#\n#$.    #\n########\n",
        "; a title\n####\n#@$.###\n; between\n#     #\n#######\n",
        "  ####\n###  #\n#@$. #\n######\n",
        "\n\n#####\r\n#@$.#\r\n#####\r\n\n",
    ],
)
def test_render_round_trips_the_level_text(text):
    assert render(world_of(text)) == map_lines(text)


@pytest.mark.parametrize("level_id", list_levels("training", LEVELS))
def test_render_round_trips_every_committed_training_level(level_id):
    _, tier, name = level_id.split("/")
    path = LEVELS / "training" / tier / f"{name}.txt"
    world = new_world(load_level(level_id, LEVELS), BUDGET)
    assert render(world) == map_lines(path.read_text(encoding="utf-8"))


def test_render_after_moves_shows_the_robot_and_the_boxes():
    room = "#######\n#     #\n# @$ .#\n#     #\n#######\n"
    world, _ = move(world_of(room), "E")
    assert render(world)[2] == "#  @$.#"
    world, _ = move(world, "E")
    assert render(world)[2] == "#   @*#"


def test_render_shows_the_robot_on_a_goal():
    world, _ = move(world_of("#######\n#@. $ #\n#######\n"), "E")
    assert render(world) == ["#######", "# + $ #", "#######"]
