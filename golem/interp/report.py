"""The short report (v2.3): the run report's first six fields, assembled from plain data.

A run ends in exactly one ``Ending``. ``short_report`` turns it, the level id, the final world's
step count and the instruction count into the report, with its keys in the contract's order. v2.4
and v4.1 add the run report's other fields (ARCHITECTURE §Execution, budgets and the report).
"""

from dataclasses import dataclass

from golem.core.world import World

REPORT_KEYS = ("level", "status", "reason", "steps", "instructions", "error")
GIVE_UP_REASON_MAX = 200
ERROR_TEXT_MAX = 500


@dataclass(frozen=True)
class Ending:
    """How a run ended: ``status`` (solved, lost or failed), ``reason`` and ``error``."""

    status: str
    reason: str | None = None
    error: str | None = None


LOST_ON_INSTRUCTIONS = Ending("lost", "instructions")
PROGRAM_ENDED = Ending("failed", "give_up", "program ended")
OUT_OF_MEMORY = Ending("failed", "error", "not enough memory")
INTERNAL = Ending("failed", "internal", "internal error")


def from_world(world: World) -> Ending:
    """A solved or lost world's ending, as the core decided it (the win, a corner, the steps)."""
    if world.status == "solved":
        return Ending("solved")
    if world.status == "lost":
        return Ending("lost", world.loss_reason)
    raise ValueError(f"a {world.status} world has not ended")


def gave_up(reason: str) -> Ending:
    """``give_up(reason)``: the reason cut to 200 characters."""
    return Ending("failed", "give_up", reason[:GIVE_UP_REASON_MAX])


def lua_error(message: str) -> Ending:
    """A Lua error at load or at run time, with its ``program:<line>:`` prefix when Lua gave one.

    The text is cut to 500 characters, so a program cannot put megabytes into its report.
    """
    return Ending("failed", "error", message[:ERROR_TEXT_MAX])


def short_report(level_id: str, world: World, instructions: int, ending: Ending) -> dict:
    return {
        "level": level_id,
        "status": ending.status,
        "reason": ending.reason,
        "steps": world.steps,
        "instructions": instructions,
        "error": ending.error,
    }
