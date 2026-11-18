"""Recorded solutions and determinism: the concept's phase-1 "done when".

Every committed training level has a recorded solution that replays to solved, twice, with identical
JSON; and saving, restoring and continuing ends where an uninterrupted game ends.
"""

import json
import random
from pathlib import Path

import pytest

from golem.core.levels import Budget, budget_for, list_levels, load_budgets, load_level
from golem.core.replay import play, replay
from golem.core.world import from_json, new_world, state_key, to_json

REPO = Path(__file__).resolve().parent.parent
LEVELS = REPO / "levels"
SOLUTIONS = REPO / "tests" / "fixtures" / "solutions"
TRAINING = list_levels("training", LEVELS)
BUDGETS = load_budgets(LEVELS)
SEEDS = range(20)


def read_solution(level_id: str) -> str:
    """Read a solution file: `;` lines are comments, whitespace is ignored."""
    text = (SOLUTIONS / f"{level_id}.txt").read_text(encoding="utf-8")
    moves = "".join(line for line in text.splitlines() if not line.startswith(";"))
    return "".join(moves.split())


def test_every_training_level_has_a_solution_and_every_solution_a_level():
    recorded = sorted(
        path.relative_to(SOLUTIONS).with_suffix("").as_posix() for path in SOLUTIONS.rglob("*.txt")
    )
    assert recorded == TRAINING


@pytest.mark.parametrize("level_id", TRAINING)
def test_a_recorded_solution_replays_to_solved_twice_with_identical_json(level_id):
    budget = budget_for(level_id, BUDGETS)
    moves = read_solution(level_id)
    runs = [replay(load_level(level_id, LEVELS), moves, budget) for _ in range(2)]

    for final, _ in runs:
        assert final.status == "solved"
        assert final.steps == len(moves) <= budget.steps
    first, second = ([json.dumps(to_json(state)) for state in states] for _, states in runs)
    assert first == second
    assert state_key(runs[0][0]) == state_key(runs[1][0])


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("level_id", TRAINING)
def test_save_restore_and_continue_ends_where_an_uninterrupted_game_ends(level_id, seed):
    rng = random.Random(1000 * TRAINING.index(level_id) + seed)
    moves = "".join(rng.choice("NESW") for _ in range(rng.randint(1, 60)))
    cut = rng.randint(0, len(moves))
    budget = Budget(steps=rng.randint(1, 80), instructions=1)
    start = new_world(load_level(level_id, LEVELS), budget)

    uninterrupted, _ = play(start, moves)

    before, _ = play(start, moves[:cut])
    saved = json.dumps(to_json(before))
    restored = from_json(json.loads(saved), load_level(level_id, LEVELS))
    resumed, _ = play(restored, moves[cut:])

    assert json.dumps(to_json(resumed)) == json.dumps(to_json(uninterrupted))
