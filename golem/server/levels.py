"""The training levels as the server lists them: one entry builder for ``GET /api/levels`` and the
WebSocket's ``levels`` reply (contracts, ARCHITECTURE.md §HTTP API).

Only the training set is ever listed. The route's entries carry no map, because the same route
serves ``golem levels`` and the agent must not see a level's map before it runs the level. The
screen's WebSocket reply adds each level's start ``map`` and its ``inside`` mask; the agent never
uses that channel.
"""

import logging
from pathlib import Path

from golem.core.level import LevelError
from golem.core.levels import BudgetsError, budget_for, list_levels, load_budgets, load_level
from golem.core.world import inside_rows, new_world, render

LOG = logging.getLogger("golem")


class LevelListError(Exception):
    """The list cannot be built. ``code`` is ``budgets_error`` or ``level_error``.

    ``detail`` says why, and the cause is already logged.
    """

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(detail)


def training_levels(levels_dir: Path, with_maps: bool = False) -> list[dict]:
    """One entry per training level, sorted by id: id, tier, size and budgets.

    With ``with_maps``, each entry also has the start ``map`` (``render`` of the level's start) and
    ``inside`` (``inside_rows`` of the level).
    """
    try:
        budgets = load_budgets(levels_dir)
    except (BudgetsError, OSError) as error:
        LOG.error("budgets.toml does not load: %s", error)
        raise LevelListError("budgets_error", str(error)) from error
    entries = []
    for level_id in list_levels("training", levels_dir):
        try:
            level = load_level(level_id, levels_dir)
            budget = budget_for(level_id, budgets)
        except (LevelError, BudgetsError) as error:
            LOG.error("training level %s does not load: %s", level_id, error)
            raise LevelListError("level_error", str(error)) from error
        entry = {
            "id": level_id,
            "tier": level_id.split("/")[1],
            "width": level.width,
            "height": level.height,
            "budget": {"steps": budget.steps, "instructions": budget.instructions},
        }
        if with_maps:
            entry["map"] = render(new_world(level, budget))
            entry["inside"] = inside_rows(level)
        entries.append(entry)
    return entries
