"""The world state and the Sokoban rules.

A ``World`` is immutable; ``move`` returns a new one. The rules are in ARCHITECTURE.md
§World and rules, and they exist nowhere else: the human game, the interpreter, the validator
and replays all call this module.
"""

from dataclasses import dataclass, replace

from golem.core.level import Cell, Level
from golem.core.levels import Budget

PLAYING = "playing"
SOLVED = "solved"
LOST = "lost"

OFFSETS: dict[str, Cell] = {"N": (-1, 0), "E": (0, 1), "S": (1, 0), "W": (0, -1)}


@dataclass(frozen=True)
class World:
    """One state of a level being played.

    ``status`` is ``"playing"``, ``"solved"`` or ``"lost"``. ``loss_reason`` is ``None``
    unless the level is lost: ``"steps"`` or ``"deadlock"`` here, or ``"instructions"``, which
    the interpreter sets.
    """

    level: Level
    robot: Cell
    boxes: frozenset[Cell]
    steps: int
    step_budget: int
    status: str = PLAYING
    loss_reason: str | None = None


def new_world(level: Level, budget: Budget) -> World:
    """The level's starting state, with the step budget of its tier."""
    world = World(
        level=level, robot=level.robot, boxes=level.boxes, steps=0, step_budget=budget.steps
    )
    if level.boxes <= level.goals:
        return replace(world, status=SOLVED)
    return world


def offset(direction: str) -> Cell:
    """The (row, column) offset of a direction; anything but N, E, S or W is an error."""
    try:
        return OFFSETS[direction]
    except (KeyError, TypeError):
        raise ValueError(f"invalid direction {direction!r}; use 'N', 'E', 'S' or 'W'") from None


def move(world: World, direction: str) -> tuple[World, bool]:
    """Move the robot one cell, pushing a box if the cell behind it is free.

    Returns the new world and whether anything moved. Every move on a playing world counts one step.
    A move on a solved or lost world changes nothing, returns ``False`` and counts no step.
    """
    dr, dc = offset(direction)
    if world.status != PLAYING:
        return world, False

    walls = world.level.walls
    target = (world.robot[0] + dr, world.robot[1] + dc)
    robot, boxes, moved, pushed = world.robot, world.boxes, False, None
    if target in world.boxes:
        behind = (target[0] + dr, target[1] + dc)
        if behind not in walls and behind not in world.boxes:
            boxes = (world.boxes - {target}) | {behind}
            robot, moved, pushed = target, True, behind
    elif target not in walls:
        robot, moved = target, True

    steps = world.steps + 1
    status, reason = PLAYING, None
    if boxes <= world.level.goals:
        status = SOLVED
    elif pushed is not None and in_corner(world.level, pushed):
        status, reason = LOST, "deadlock"
    elif steps >= world.step_budget:
        status, reason = LOST, "steps"
    return replace(world, robot=robot, boxes=boxes, steps=steps, status=status,
                   loss_reason=reason), moved


def in_corner(level: Level, cell: Cell) -> bool:
    """The corner rule: a cell that is not a goal, with walls on two orthogonal sides."""
    if cell in level.goals:
        return False
    r, c = cell
    north = (r - 1, c) in level.walls
    east = (r, c + 1) in level.walls
    south = (r + 1, c) in level.walls
    west = (r, c - 1) in level.walls
    return (north and east) or (east and south) or (south and west) or (west and north)
