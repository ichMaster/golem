"""Replaying a move string such as ``"NNESW"`` through the rules."""

from golem.core.level import Level
from golem.core.levels import Budget
from golem.core.world import OFFSETS, World, move, new_world


def play(world: World, moves: str) -> tuple[World, list[World]]:
    """Apply every move in turn; return the final world and every state, the start first.

    A character other than N, E, S or W is a ``ValueError`` naming its position (from 1), raised
    before any move is applied. Moves after the level ends change nothing.
    """
    if not isinstance(moves, str):
        raise ValueError(f"moves must be a string, not {moves!r}")
    for position, char in enumerate(moves, start=1):
        if char not in OFFSETS:
            raise ValueError(f"invalid move {char!r} at position {position}; use N, E, S or W")
    states = [world]
    for char in moves:
        world, _ = move(world, char)
        states.append(world)
    return world, states


def replay(level: Level, moves: str, budget: Budget) -> tuple[World, list[World]]:
    """Play a move string from the level's start."""
    return play(new_world(level, budget), moves)
