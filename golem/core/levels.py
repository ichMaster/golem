"""Level ids, listing and loading by id, and the per-tier budgets.

A level id is ``<set>/<tier>/<name>``, for the file ``<levels root>/<set>/<tier>/<name>.txt``.
An id is checked against the listing of its set before anything is read, so it is never used as a
raw path. The id scheme and the ``budgets.toml`` schema are contracts (ARCHITECTURE.md §World and
rules).
"""

import os
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from golem.core.level import Level, parse_level

ID_PART = re.compile(r"[a-z0-9][a-z0-9-]*")
TIER_NAME = re.compile(r"tier[0-9]+")
DEFAULT_LEVELS_DIR = "levels"
BUDGETS_FILE = "budgets.toml"
BUDGET_KEYS = ("instructions", "steps")


class UnknownLevel(LookupError):
    """An id that is malformed or names no level in its set's listing."""

    def __init__(self, level_id: str) -> None:
        self.level_id = level_id
        super().__init__(f"unknown level id: {level_id!r}")


class BudgetsError(ValueError):
    """``budgets.toml`` does not follow the schema."""


@dataclass(frozen=True)
class Budget:
    """The step and instruction budgets of one tier."""

    steps: int
    instructions: int


def levels_root() -> Path:
    """The levels root: ``GOLEM_LEVELS_DIR``, or ``levels``."""
    return Path(os.environ.get("GOLEM_LEVELS_DIR") or DEFAULT_LEVELS_DIR)


def list_levels(set_name: str, root: Path | None = None) -> list[str]:
    """The ids of every level in a set, sorted."""
    if not ID_PART.fullmatch(set_name):
        raise ValueError(f"invalid level set name: {set_name!r}")
    return sorted(_level_files(set_name, root or levels_root()))


def load_level(level_id: str, root: Path | None = None) -> Level:
    """Load and parse a level by id; the id must appear in its set's listing."""
    parts = level_id.split("/")
    if (
        len(parts) != 3
        or not all(ID_PART.fullmatch(part) for part in parts)
        or not TIER_NAME.fullmatch(parts[1])
    ):
        raise UnknownLevel(level_id)
    path = _level_files(parts[0], root or levels_root()).get(level_id)
    if path is None:
        raise UnknownLevel(level_id)
    return parse_level(path.read_text(encoding="utf-8"), level_id)


def load_budgets(root: Path | None = None) -> dict[str, Budget]:
    """Read ``budgets.toml``: one ``[tier<N>]`` table per tier, with ``steps`` and ``instructions``.

    Every value is a positive integer; a missing or unknown key is an error.
    """
    path = (root or levels_root()) / BUDGETS_FILE
    try:
        with path.open("rb") as file:
            data = tomllib.load(file)
    except tomllib.TOMLDecodeError as error:
        raise BudgetsError(f"{BUDGETS_FILE}: {error}") from error

    budgets = {}
    for tier in sorted(data):
        table = data[tier]
        if not TIER_NAME.fullmatch(tier) or not isinstance(table, dict):
            raise BudgetsError(f"{BUDGETS_FILE}: {tier!r} is not a tier table such as [tier1]")
        for key in BUDGET_KEYS:
            if key not in table:
                raise BudgetsError(f"{BUDGETS_FILE}: [{tier}] has no {key!r}")
        extra = sorted(set(table) - set(BUDGET_KEYS))
        if extra:
            raise BudgetsError(f"{BUDGETS_FILE}: [{tier}] has an unknown key {extra[0]!r}")
        for key in BUDGET_KEYS:
            value = table[key]
            if type(value) is not int or value <= 0:
                raise BudgetsError(
                    f"{BUDGETS_FILE}: [{tier}] {key} must be a positive integer, not {value!r}"
                )
        budgets[tier] = Budget(steps=table["steps"], instructions=table["instructions"])
    if not budgets:
        raise BudgetsError(f"{BUDGETS_FILE}: no tier is defined")
    return budgets


def _level_files(set_name: str, root: Path) -> dict[str, Path]:
    """Map every level id of a set to its file. ``set_name`` is already validated."""
    found: dict[str, Path] = {}
    set_dir = root / set_name
    if not set_dir.is_dir():
        return found
    for tier_dir in set_dir.iterdir():
        if not tier_dir.is_dir() or not TIER_NAME.fullmatch(tier_dir.name):
            continue
        for file in tier_dir.iterdir():
            if file.is_file() and file.suffix == ".txt" and ID_PART.fullmatch(file.stem):
                found[f"{set_name}/{tier_dir.name}/{file.stem}"] = file
    return found
