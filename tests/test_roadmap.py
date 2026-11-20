"""The roadmap follows the releases: every phase up to VERSION's A.B is marked released, and no
later phase is (v2.3 code review #3: v2.2 still read "planned" after v2.2.0)."""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ROADMAP = (REPO / "specification" / "ROADMAP.md").read_text(encoding="utf-8")
RELEASED = "✅ released"


def version() -> tuple[int, int]:
    major, minor, _ = (REPO / "VERSION").read_text(encoding="utf-8").strip().split(".")
    return int(major), int(minor)


def phase(name: str) -> tuple[int, int]:
    major, minor = name.removeprefix("v").split(".")
    return int(major), int(minor)


def table_rows() -> dict[str, str]:
    rows = re.findall(r"^\| (v\d+\.\d+) \| [^|]+ \| ([^|]+?) \| [^|]+ \|$", ROADMAP, re.M)
    return dict(rows)


def status_lines() -> dict[str, str]:
    found = re.findall(r"^### (v\d+\.\d+) — .*?\n\n\*\*Status:\*\* ([^\n]+)", ROADMAP, re.M | re.S)
    return dict(found)


def test_the_status_table_and_the_phase_sections_agree_with_the_version():
    current = version()
    rows, lines = table_rows(), status_lines()
    assert rows and set(rows) <= set(lines)
    for name, status in rows.items():
        released = phase(name) <= current
        assert status.startswith(RELEASED) == released, f"table: {name} is '{status}'"
        assert lines[name].startswith(RELEASED) == released, f"section: {name} is '{lines[name]}'"
