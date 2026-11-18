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


def look(world: World, direction: str) -> str:
    """What is in the neighbouring cell: wall, box, goal, box_on_goal or empty."""
    dr, dc = offset(direction)
    cell = (world.robot[0] + dr, world.robot[1] + dc)
    if cell in world.level.walls:
        return "wall"
    on_goal = cell in world.level.goals
    if cell in world.boxes:
        return "box_on_goal" if on_goal else "box"
    return "goal" if on_goal else "empty"


def here(world: World) -> str:
    """What is in the robot's own cell: goal or empty."""
    return "goal" if world.robot in world.level.goals else "empty"


def boxes_left(world: World) -> int:
    """The number of boxes not on goals."""
    return len(world.boxes - world.level.goals)


def render(world: World) -> list[str]:
    """The current map as Sokoban text lines, without trailing spaces (the report's final map)."""
    level = world.level
    lines = []
    for r in range(level.height):
        chars = []
        for c in range(level.width):
            cell = (r, c)
            on_goal = cell in level.goals
            if cell in level.walls:
                chars.append("#")
            elif cell == world.robot:
                chars.append("+" if on_goal else "@")
            elif cell in world.boxes:
                chars.append("*" if on_goal else "$")
            else:
                chars.append("." if on_goal else " ")
        lines.append("".join(chars).rstrip(" "))
    return lines


# --- save, restore and the state key -----------------------------------------------------------

JSON_KEYS = ("level", "robot", "boxes", "steps", "step_budget", "status", "loss_reason")
LOSS_REASONS = ("steps", "deadlock", "instructions")


def to_json(world: World) -> dict:
    """The state as plain JSON data: keys in a fixed order, boxes sorted."""
    return {
        "level": world.level.id,
        "robot": list(world.robot),
        "boxes": [list(cell) for cell in sorted(world.boxes)],
        "steps": world.steps,
        "step_budget": world.step_budget,
        "status": world.status,
        "loss_reason": world.loss_reason,
    }


def from_json(data: object, level: Level) -> World:
    """Restore a state saved by ``to_json`` onto its level.

    Anything inconsistent with the level or with itself is a ``ValueError`` that names the field.
    """
    if not isinstance(data, dict):
        raise ValueError("saved world: not a JSON object")
    for key in JSON_KEYS:
        if key not in data:
            raise ValueError(f"saved world: missing key {key!r}")
    extra = sorted(set(data) - set(JSON_KEYS))
    if extra:
        raise ValueError(f"saved world: unknown key {extra[0]!r}")
    if data["level"] != level.id:
        raise ValueError(f"saved world: level {data['level']!r} is not {level.id!r}")

    robot = _saved_cell(data["robot"], "robot", level)
    if not isinstance(data["boxes"], list):
        raise ValueError("saved world: boxes must be a list of cells")
    boxes = [_saved_cell(cell, "boxes", level) for cell in data["boxes"]]
    if len(set(boxes)) != len(boxes):
        raise ValueError("saved world: boxes has two boxes in one cell")
    if len(boxes) != len(level.boxes):
        raise ValueError(f"saved world: boxes has {len(boxes)} boxes, the level {len(level.boxes)}")
    if robot in boxes:
        raise ValueError("saved world: robot stands on a box")

    steps, step_budget = data["steps"], data["step_budget"]
    if type(steps) is not int or steps < 0:
        raise ValueError(f"saved world: steps must be a non-negative integer, not {steps!r}")
    if type(step_budget) is not int or step_budget <= 0:
        raise ValueError(
            f"saved world: step_budget must be a positive integer, not {step_budget!r}"
        )

    status, reason = data["status"], data["loss_reason"]
    if status not in (PLAYING, SOLVED, LOST):
        raise ValueError(f"saved world: unknown status {status!r}")
    if (status == LOST) != (reason in LOSS_REASONS) or (status != LOST and reason is not None):
        raise ValueError(f"saved world: loss_reason {reason!r} does not fit status {status!r}")

    return World(level=level, robot=robot, boxes=frozenset(boxes), steps=steps,
                 step_budget=step_budget, status=status, loss_reason=reason)


def _saved_cell(value: object, field: str, level: Level) -> Cell:
    """A ``[row, column]`` pair inside the level's walls (in ``level.inside``)."""
    if (
        not isinstance(value, list | tuple)
        or len(value) != 2
        or any(type(part) is not int for part in value)
    ):
        raise ValueError(f"saved world: {field} must hold [row, column] pairs, not {value!r}")
    cell = (value[0], value[1])
    if cell in level.walls:
        raise ValueError(f"saved world: {field} cell {list(cell)} is a wall")
    if cell not in level.inside:
        raise ValueError(f"saved world: {field} cell {list(cell)} is outside the map")
    return cell


def state_key(world: World) -> tuple[Cell, tuple[Cell, ...]]:
    """The position, for repeat detection: the robot cell and the sorted box cells."""
    return world.robot, tuple(sorted(world.boxes))
