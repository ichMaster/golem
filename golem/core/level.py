"""Levels in the standard Sokoban text format.

``parse_level`` turns a level's text into an immutable ``Level``, or raises a ``LevelError``
that names the line and the column of the problem. The character table and the validity rules are in
ARCHITECTURE.md §World and rules.
"""

from collections import deque
from dataclasses import dataclass

Cell = tuple[int, int]
"""A ``(row, column)`` pair, counted from 0; row 0 is the first map line after comments."""

FLOOR_CHARS = frozenset(" -_")
DIRECTIONS: tuple[Cell, ...] = ((-1, 0), (0, 1), (1, 0), (0, -1))  # N, E, S, W


class LevelError(ValueError):
    """A level that cannot be parsed or is not valid.

    ``line`` and ``column`` are counted from 1 in the file's own lines, comment lines included.
    """

    def __init__(self, level_id: str, line: int, column: int, message: str) -> None:
        self.level_id = level_id
        self.line = line
        self.column = column
        self.message = message
        super().__init__(f"{level_id}:{line}:{column}: {message}")


@dataclass(frozen=True)
class Level:
    """A parsed, valid level: its size, walls and goals, and where the boxes and the robot start.

    ``inside`` holds every non-wall cell the robot's start reaches without crossing a wall (boxes do
    not block it): the only cells a robot or a box can ever occupy.
    """

    id: str
    width: int
    height: int
    walls: frozenset[Cell]
    goals: frozenset[Cell]
    boxes: frozenset[Cell]
    robot: Cell
    inside: frozenset[Cell]


def parse_level(text: str, level_id: str) -> Level:
    """Parse one level in the standard Sokoban text format and check that it is valid."""
    numbered = [
        (number, line)
        for number, line in enumerate(text.replace("\r", "").split("\n"), start=1)
        if not line.startswith(";")
    ]
    while numbered and numbered[0][1].strip(" ") == "":
        numbered.pop(0)
    while numbered and numbered[-1][1].strip(" ") == "":
        numbered.pop()
    if not numbered:
        raise LevelError(level_id, 1, 1, "the level has no map lines")

    line_of = [number for number, _ in numbered]
    rows = [line for _, line in numbered]

    walls: set[Cell] = set()
    goals: set[Cell] = set()
    boxes: set[Cell] = set()
    robots: list[Cell] = []
    for r, row in enumerate(rows):
        for c, char in enumerate(row):
            cell = (r, c)
            if char == "#":
                walls.add(cell)
            elif char in FLOOR_CHARS:
                pass
            elif char == "$":
                boxes.add(cell)
            elif char == ".":
                goals.add(cell)
            elif char == "*":
                boxes.add(cell)
                goals.add(cell)
            elif char == "@":
                robots.append(cell)
            elif char == "+":
                robots.append(cell)
                goals.add(cell)
            else:
                raise LevelError(level_id, line_of[r], c + 1, f"unknown character {char!r}")

    def error_at(cell: Cell, message: str) -> LevelError:
        return LevelError(level_id, line_of[cell[0]], cell[1] + 1, message)

    first = (0, 0)
    if not robots:
        raise error_at(first, "the level has no robot")
    if len(robots) > 1:
        raise error_at(robots[1], "a second robot; a level has exactly one")
    if not boxes:
        raise error_at(first, "the level has no box")
    if len(boxes) != len(goals):
        raise error_at(first, f"{len(boxes)} boxes but {len(goals)} goals; the counts must match")

    robot = robots[0]
    inside = _inside_cells(rows, walls, robot, error_at)

    return Level(
        id=level_id,
        width=max(len(row) for row in rows),
        height=len(rows),
        walls=frozenset(walls),
        goals=frozenset(goals),
        boxes=frozenset(boxes),
        robot=robot,
        inside=frozenset(inside),
    )


def _inside_cells(rows: list[str], walls: set[Cell], robot: Cell, error_at) -> set[Cell]:
    """Flood-fill from the robot over non-wall cells; stepping outside the map is an error."""

    def inside(cell: Cell) -> bool:
        r, c = cell
        return 0 <= r < len(rows) and 0 <= c < len(rows[r])

    seen = {robot}
    queue = deque([robot])
    while queue:
        cell = queue.popleft()
        for dr, dc in DIRECTIONS:
            nxt = (cell[0] + dr, cell[1] + dc)
            if not inside(nxt):
                raise error_at(cell, "the map is not closed: the robot can walk off it here")
            if nxt in walls or nxt in seen:
                continue
            seen.add(nxt)
            queue.append(nxt)
    return seen
