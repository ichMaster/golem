"""``golem-local``: the in-process runner, the owner's hand tool until the ``golem`` CLI (v5.1).

    uv run golem-local run <level> <program.lua> [--swap <program.lua>]

It runs the program on a training level in this process, with no server, and prints the run report
as one JSON line. With ``--swap`` (v2.5), when the first program gives up or returns, the second one
takes over the same run: the same world and ``memory``, the counters carried over. Any other ending
(solved, lost, a Lua error, a failure) ends the run there, and the second program is never loaded;
a swap on a Lua error belongs to the stops of v4.2. Both files are read before anything runs.

Exit codes, as the CLI's:
- 0: a report was printed, whatever its status;
- 1: the request was refused, and ``{"error", "detail"}`` was printed (an unknown level, a program
  file that cannot be read, a broken level or setting);
- 2: a usage error (argparse).

``.env`` is read from the working directory only, without overriding the environment, and without
changing this process's environment.
"""

import argparse
import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path

from golem.core.level import LevelError
from golem.core.levels import BudgetsError, budget_for, list_levels, load_budgets, load_level
from golem.interp.config import InterpConfigError, load_interp_settings
from golem.interp.run import Run, swap_on_give_up

DEFAULT_LEVELS_DIR = "levels"


class Refused(Exception):
    """A request ``golem-local`` refuses: printed as ``{"error", "detail"}``, exit 1."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code, self.detail = code, detail


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        second = Path(args.swap) if args.swap is not None else None
        report = _run(args.level, Path(args.program), _environment(), second)
    except Refused as refused:
        _print({"error": refused.code, "detail": refused.detail})
        return 1
    _print(report)
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="golem-local", description="Run a Lua program on a training level, in-process.")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="run a program and print its report as JSON")
    run.add_argument("level", help="a training level id, e.g. training/tier1/t1-01")
    run.add_argument("program", help="the Lua program file")
    run.add_argument(
        "--swap", metavar="PROGRAM",
        help="a second Lua program file, swapped in when the first one gives up or returns")
    return parser


def _environment() -> Mapping[str, str]:
    """The process environment over ``./.env``: the environment wins, and nothing is changed."""
    env_file = Path.cwd() / ".env"
    values: dict[str, str] = {}
    if env_file.is_file():
        from dotenv import dotenv_values

        values = {k: v for k, v in dotenv_values(env_file).items() if v is not None}
    return {**values, **os.environ}


def _run(level_id: str, program: Path, environ: Mapping[str, str], second: Path | None) -> dict:
    root = Path(environ.get("GOLEM_LEVELS_DIR") or DEFAULT_LEVELS_DIR)
    try:
        settings = load_interp_settings(environ)
    except InterpConfigError as error:
        raise Refused("bad_setting", str(error)) from None
    # Training ids only; a hidden, unknown or malformed id gets the same answer.
    if level_id not in list_levels("training", root):
        raise Refused("unknown_level", "unknown level")
    try:
        level = load_level(level_id, root)
        budget = budget_for(level_id, load_budgets(root))
    except (LevelError, BudgetsError, OSError) as error:
        raise Refused("level_error", str(error)) from None
    source = _read_program(program)
    second_source = _read_program(second) if second is not None else None
    run = Run(level, budget, settings)
    run.start(source)
    run.drive()
    swap_on_give_up(run, second_source)
    return run.report()


def _read_program(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise Refused("bad_program", f"{path}: no such file") from None
    except UnicodeDecodeError:
        raise Refused("bad_program", f"{path}: not UTF-8 text") from None
    except OSError as error:
        raise Refused("bad_program", f"{path}: {error.strerror or error}") from None


def _print(data: dict) -> None:
    sys.stdout.write(json.dumps(data, ensure_ascii=False) + "\n")
    sys.stdout.flush()
