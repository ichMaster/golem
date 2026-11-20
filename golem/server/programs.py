"""The programs folder (v2.4): the example Lua programs the screen lists, shows and runs.

Programs are read by name, never by path: a name is ``[a-z0-9][a-z0-9_-]*.lua`` (at most 64
characters), and the file it names must resolve to a regular file directly inside the folder, so a
``..``, a separator or a symlink out of the folder never reaches another file. These are pure
functions over a directory; the server's routes are thin over them.
"""

import re
from pathlib import Path

NAME = re.compile(r"[a-z0-9][a-z0-9_-]*\.lua")
NAME_MAX = 64
DESCRIPTION_MAX = 120


class UnknownProgram(LookupError):
    """No program of that name in the folder (an invalid name included)."""


class BadProgram(ValueError):
    """The program file is not UTF-8 text."""


def list_programs(folder: Path | None) -> list[dict]:
    """``[{"name", "description", "size"}]`` for every program in the folder, sorted by name."""
    if folder is None or not folder.is_dir():
        return []
    programs = []
    for name in sorted(entry.name for entry in folder.iterdir()):
        try:
            path = _program_path(folder, name)
        except UnknownProgram:
            continue
        try:
            description = describe(_decode(path.read_bytes()))
        except BadProgram:
            description = ""
        programs.append({"name": name, "description": description, "size": path.stat().st_size})
    return programs


def read_program(folder: Path | None, name: str) -> str:
    """The program's source, with a leading UTF-8 BOM dropped."""
    if folder is None:
        raise UnknownProgram(name)
    return _decode(_program_path(folder, name).read_bytes())


def describe(source: str) -> str:
    """The first line when it is a ``--`` comment, without the dashes; otherwise empty."""
    first = source.split("\n", 1)[0].strip()
    if not first.startswith("--"):
        return ""
    return first.lstrip("-").strip()[:DESCRIPTION_MAX]


def _program_path(folder: Path, name: object) -> Path:
    if not isinstance(name, str) or len(name) > NAME_MAX or not NAME.fullmatch(name):
        raise UnknownProgram(str(name))
    root = folder.resolve()
    path = (root / name).resolve()
    if path.parent != root or not path.is_file():
        raise UnknownProgram(name)
    return path


def _decode(data: bytes) -> str:
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise BadProgram("the program is not UTF-8 text") from None
