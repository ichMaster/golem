"""The repository is English only (CLAUDE.md §Language): no Cyrillic text in the code, the tests,
the interface or the documents. The frozen specification/concept.uk.md is the one exception.

It never reads levels/hidden/, data/ or .env.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCANNED = ["golem", "tests", "specification", "scripts", "levels/training", ".claude/skills",
           "programs"]
TOP_LEVEL = ["README.md", "CLAUDE.md", "RELEASE.txt", "pyproject.toml", ".env.example"]
EXCEPTIONS = {REPO / "specification" / "concept.uk.md"}
TEXT_SUFFIXES = {".py", ".lua", ".md", ".txt", ".toml", ".html", ".js", ".css", ".sh", ".json",
                 ".yml", ".yaml", ""}
CYRILLIC = re.compile("[\u0400-\u04ff]")


def text_files() -> list[Path]:
    files = [REPO / name for name in TOP_LEVEL if (REPO / name).is_file()]
    for directory in SCANNED:
        files += [p for p in (REPO / directory).rglob("*")
                  if p.is_file() and p.suffix in TEXT_SUFFIXES and "__pycache__" not in p.parts]
    return sorted(set(files) - EXCEPTIONS)


def test_no_tracked_text_is_written_in_cyrillic():
    found = []
    for path in text_files():
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        found += [f"{path.relative_to(REPO)}:{n}" for n, line in enumerate(lines, 1)
                  if CYRILLIC.search(line)]
    assert found == []


def test_the_check_would_catch_cyrillic():
    assert CYRILLIC.search("\u0433\u043e\u0442\u043e\u0432\u043e")  # a Cyrillic word
    assert not CYRILLIC.search("naïve café → ok")
