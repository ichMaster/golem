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

``swap_on_give_up`` is the swap that ``golem-local --swap`` and the text page use (v2.5): a second
program takes over when the first one gives up or returns. ``run_program`` runs one program from the
start of a level, and ``run_with_frames`` runs one, or two with that swap, and keeps the frames.
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
    program (the v2.4 frames), and ``on_swap(world, version)`` at every swap.
    """

    def __init__(
        self, level: Level, budget: Budget, settings: InterpSettings, on_move=None, on_swap=None
    ):
        self.level = level
        self.world: World = new_world(level, budget)
        self.instructions = 0
        self.versions: list[int] = []
        # One entry per swap: where it happened and how the program before it ended (the run log).
        self.swaps: list[dict] = []
        self.ending: Ending | None = None
        self._budget = budget
        self._settings = settings
        self._on_move = on_move
        self._on_swap = on_swap
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
    run.swaps.append(swap_entry(run.world.steps, len(run.versions) + 1, run.instructions,
                                run.ending))
    run.versions.append(len(run.versions) + 1)
    run._guarded(lambda: _swap_in(run, source))


def swap_entry(step: int, version: int, instructions: int, ended: Ending) -> dict:
    """One swap of the run log: the step and the instruction count at the swap point, the version
    swapped in, and how the program before it ended (its give-up reason or error text in ``error``,
    cut as in the report)."""
    return {
        "step": step, "version": version, "instructions": instructions,
        "ended": {"status": ended.status, "reason": ended.reason, "error": ended.error},
    }


def _swap_in(run: Run, source: str) -> None:
    if run._on_swap is not None:
        run._on_swap(run.world, run.versions[-1])
    run._load(source)


def swap_on_give_up(run: Run, source: str | None) -> None:
    """When the run's program gave up or returned, swap ``source`` in and drive it to its end.

    Any other ending (solved, lost, a Lua error, a failure) leaves the run as it is, and ``source``
    is never loaded; a swap on a Lua error belongs to the stops of v4.2. This is the swap of
    ``golem-local --swap`` and of the text page.
    """
    if source is None or run.ending is None:
        return
    if (run.ending.status, run.ending.reason) == ("failed", "give_up"):
        swap(run, source)
        run.drive()


def run_program(level: Level, budget: Budget, source: str, settings: InterpSettings) -> dict:
    """Run ``source`` on ``level`` within ``budget`` and return the short report."""
    run = Run(level, budget, settings)
    run.start(source)
    run.drive()
    return run.report()


def run_with_frames(
    level: Level, budget: Budget, source: str, settings: InterpSettings, second: str | None = None
) -> tuple[dict, list[dict], list[dict]]:
    """Run like ``run_program``, with ``second`` swapped in by ``swap_on_give_up`` when it is given,
    and return the report, the frames and the swaps (``swap_entry``, empty without a swap). The
    frames are the map before the first move and after every ``move``, rendered by the core.

    Each frame is ``{"step", "dir", "moved", "version", "map"}``, where ``version`` is the program
    that was driving. The first has step 0, ``dir`` and ``moved`` set to ``None``, and version 1.
    A swap adds a frame at the swap point: the same step and map, ``dir`` and ``moved`` set to
    ``None``, and the new version. ``look``, ``here`` and ``boxes_left`` add no frame, so the frames
    are bounded by the step budget plus one, plus one for each swap.
    """
    frames = [frame(new_world(level, budget), None, None, 1)]
    versions: list[int] = []

    def on_move(world: World, direction: str, moved: bool) -> None:
        frames.append(frame(world, direction, moved, versions[-1]))

    def on_swap(world: World, version: int) -> None:
        frames.append(frame(world, None, None, version))

    run = Run(level, budget, settings, on_move=on_move, on_swap=on_swap)
    versions = run.versions
    run.start(source)
    run.drive()
    swap_on_give_up(run, second)
    return run.report(), frames, [dict(entry) for entry in run.swaps]


def frame(world: World, direction: str | None, moved: bool | None, version: int) -> dict:
    """One frame of the playback: the step, the move, the program's version, and the map rendered
    by the core."""
    return {
        "step": world.steps, "dir": direction, "moved": moved, "version": version,
        "map": core.render(world),
    }
