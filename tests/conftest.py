"""Shared fixtures. Tests never read levels/hidden/; they use tests/fixtures/hidden/."""

import shutil
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
LEVELS = REPO / "levels"
HIDDEN_FIXTURES = REPO / "tests" / "fixtures" / "hidden"


@pytest.fixture
def root_with_hidden(tmp_path: Path) -> Path:
    """A levels root with the committed training set and budgets, and the fixture hidden levels."""
    root = tmp_path / "levels"
    shutil.copytree(LEVELS / "training", root / "training")
    shutil.copy(LEVELS / "budgets.toml", root / "budgets.toml")
    shutil.copytree(HIDDEN_FIXTURES, root / "hidden")
    return root
