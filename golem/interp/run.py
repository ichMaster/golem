"""A run (v2.5): one level, one Lua runtime, and the programs that drive it one after another.

A ``Run`` holds the sandbox's runtime, the world, the instruction count, the versions loaded and the
driver's functions. ``memory`` belongs to the run, not to a program: it is one table per runtime,
made by the sandbox's set-up chunk, and every program environment points to it.

``swap(run, source)`` starts a new program in the same run once the current one has stopped on
``give_up``, on its return or on a Lua error:
- the new text is loaded with a new environment that shares ``memory``;
- the old coroutine is closed and can never be resumed;
- the count hook goes onto the new coroutine;
- the world, the step count and the instruction count carry over, and the level never restarts.

``run_program`` and ``run_with_frames`` run one program from the start of a level.
"""

import logging

import lupa.lua54 as lua54

from golem.core import world as core
from golem.core.level import Level
from golem.core.levels import Budget
from golem.core.world import PLAYING, World, new_world
from golem.interp.config import InterpSettings
from golem.interp.driver import DRIVER, ERROR_BYTES_MAX, GIVE_UP_BYTES_MAX, drive
from golem.interp.report import INTERNAL, OUT_OF_MEMORY, Ending, lua_error, short_report
from golem.interp.sandbox import ProgramLoadError, new_sandbox

LOG = logging.getLogger("golem.interp")

# The endings after which the program has stopped but the level goes on, so a swap may follow.
SWAPPABLE_REASONS = ("give_up", "error")


class SwapRefused(Exception):
    """A swap that the run does not allow now; the run is unchanged."""


class Run:
    """One run of a level: its runtime, world, counters and versions.

    ``on_move(world, direction, moved)``, when given, is called after every ``move`` of every
    program (the v2.4 frames).
    """

    def __init__(self, level: Level, budget: Budget, settings: InterpSettings, on_move=None):
        self.level = level
        self.world: World = new_world(level, budget)
        self.instructions = 0
        self.versions: list[int] = []
        self.ending: Ending | None = None
        self._budget = budget
        self._settings = settings
        self._on_move = on_move
        self._sandbox = None
        self._step = self._install = self._resume_previous = None
        # A memory error escaped the program's protected call, or the driver failed: nothing may
        # follow. A program that hits the memory cap itself ends on an ordinary Lua error.
        self._broken = False

    def start(self, source: str) -> None:
        """Create the runtime and load version 1. A program that does not load ends the run."""
        if self.versions:
            raise RuntimeError("the run has already started")
        self.versions.append(1)
        self._guarded(lambda: self._open(source))

    def drive(self) -> Ending:
        """Resume the current program until it ends, and return how it ended."""
        if self.ending is None:
            self._guarded(self._drive)
        return self.ending

    def can_swap(self) -> bool:
        """The program stopped on give_up, its return or a Lua error, and the level goes on."""
        ending = self.ending
        return (
            not self._broken
            and ending is not None
            and ending.status == "failed"
            and ending.reason in SWAPPABLE_REASONS
            and self.world.status == PLAYING
        )

    def report(self) -> dict:
        """The run's short report; the run must have ended."""
        if self.ending is None:
            raise RuntimeError("the run has not ended")
        return short_report(
            self.level.id, self.world, self.instructions, self.ending, self.versions)

    def resume_previous(self) -> tuple:
        """Resume the coroutine that the last swap closed; only the tests call it."""
        return self._resume_previous()

    # --- inside the run ------------------------------------------------------------------------

    def _open(self, source: str) -> None:
        self._sandbox = new_sandbox(self._settings)
        self._step, self._install, self._resume_previous = self._sandbox.runtime.execute(
            DRIVER, self._settings.hook_every, self._budget.instructions, self._sandbox.safe_text,
            GIVE_UP_BYTES_MAX, ERROR_BYTES_MAX,
        )
        self._load(source)

    def _load(self, source: str) -> None:
        try:
            chunk = self._sandbox.load(source)
        except ProgramLoadError as error:
            self.ending = lua_error(str(error))
            return
        self._install(chunk)
        self.ending = None

    def _drive(self) -> None:
        self.ending, self.world, self.instructions = drive(self._step, self.world, self._on_move)

    def _guarded(self, action) -> None:
        """Run ``action``; the memory cap and any failure of the driver become the run's ending."""
        try:
            action()
        except lua54.LuaMemoryError:
            self.ending, self._broken = OUT_OF_MEMORY, True
        except Exception:
            LOG.exception("the driver failed on %s", self.level.id)
            self.ending, self._broken = INTERNAL, True


def swap(run: Run, source: str) -> None:
    """Load ``source`` as the run's next version, in place of the program that stopped.

    Raises ``SwapRefused`` when the level has ended, the program has not stopped, or the run failed
    in the driver or on a memory error outside the program. A program that does not load ends the
    run with its error, and a later swap may still replace it.
    """
    if not run.can_swap():
        raise SwapRefused("the run cannot take a new program now")
    run.versions.append(len(run.versions) + 1)
    run._guarded(lambda: run._load(source))


def run_program(level: Level, budget: Budget, source: str, settings: InterpSettings) -> dict:
    """Run ``source`` on ``level`` within ``budget`` and return the short report."""
    run = Run(level, budget, settings)
    run.start(source)
    run.drive()
    return run.report()


def run_with_frames(
    level: Level, budget: Budget, source: str, settings: InterpSettings
) -> tuple[dict, list[dict]]:
    """Run like ``run_program``, and also return the frames: the map before the first move and after
    every ``move``, rendered by the core.

    Each frame is ``{"step", "dir", "moved", "map"}``; the first has ``step`` 0 and ``dir`` and
    ``moved`` set to ``None``. ``look``, ``here`` and ``boxes_left`` change nothing on the map and
    add no frame, so the frames are bounded by the step budget.
    """
    frames = [frame(new_world(level, budget), None, None)]

    def on_move(world: World, direction: str, moved: bool) -> None:
        frames.append(frame(world, direction, moved))

    run = Run(level, budget, settings, on_move=on_move)
    run.start(source)
    run.drive()
    return run.report(), frames


def frame(world: World, direction: str | None, moved: bool | None) -> dict:
    """One frame of the playback: the step, the move, and the map rendered by the core."""
    return {"step": world.steps, "dir": direction, "moved": moved, "map": core.render(world)}
