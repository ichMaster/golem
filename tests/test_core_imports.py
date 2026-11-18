"""The game core imports only the standard library and its own modules."""

import ast
import sys
from pathlib import Path

CORE = Path(__file__).resolve().parent.parent / "golem" / "core"


def _imported_modules(path: Path) -> list[tuple[str, int]]:
    """Every absolute module a file imports, with its line.

    Relative imports are skipped: they stay inside the core.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend((alias.name, node.lineno) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.append((node.module, node.lineno))
    return found


def _allowed(module: str) -> bool:
    top = module.split(".")[0]
    in_core = module == "golem.core" or module.startswith("golem.core.")
    return top in sys.stdlib_module_names or in_core


def test_core_has_python_files():
    assert (CORE / "__init__.py").is_file()


def test_core_imports_only_the_standard_library():
    offending = [
        f"{path.relative_to(CORE.parent.parent)}:{line}: {module}"
        for path in sorted(CORE.rglob("*.py"))
        for module, line in _imported_modules(path)
        if not _allowed(module)
    ]
    message = "golem/core imports outside the standard library:\n" + "\n".join(offending)
    assert offending == [], message
