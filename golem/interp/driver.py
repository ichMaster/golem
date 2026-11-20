"""The driver (v2.3): one program on one level, one robot command at a time, ending in one report.

The program runs in a Lua coroutine. Each robot command yields ``{cmd, arg}``; the driver applies
it through the core and resumes the coroutine with the result. A small driver chunk, run in the
runtime's globals, holds ``coroutine``, ``debug``, the instruction counter and the budget sentinel
in its upvalues, where the program cannot reach them:

- the count hook adds ``HOOK_EVERY`` to the counter on every call, and raises the sentinel once the
  counter reaches the level's instruction budget;
- the sentinel is recognized in Lua with ``rawequal`` (Python cannot compare Lua tables by identity,
  see the v2.3 spike), so a program's own ``error("instruction budget exhausted")`` is an ordinary
  error.

Every way a run can end, including a bug in this module, becomes a report; nothing escapes.
"""

import logging

import lupa.lua54 as lua54

from golem.core import world as core
from golem.core.level import Level
from golem.core.levels import Budget
from golem.core.world import PLAYING, World, new_world
from golem.interp.config import InterpSettings
from golem.interp.report import (
    INTERNAL,
    LOST_ON_INSTRUCTIONS,
    OUT_OF_MEMORY,
    PROGRAM_ENDED,
    Ending,
    from_world,
    gave_up,
    lua_error,
    short_report,
)
from golem.interp.sandbox import ProgramLoadError, new_sandbox

LOG = logging.getLogger("golem.interp")

# A give_up reason is cut to 200 characters and an error text to 500; at most 4 bytes a character,
# so no more than 800 and 2000 bytes of them ever cross into Python.
GIVE_UP_BYTES_MAX = 800
ERROR_BYTES_MAX = 2000

DRIVER = r"""
local chunk, every, budget, safe_text, reason_bytes, error_bytes = ...
local SENTINEL = {}
local counter = 0
local co = coroutine.create(chunk)
debug.sethook(co, function()
  counter = counter + every
  if counter >= budget then error(SENTINEL, 0) end
end, "", every)

local function describe(value)
  if type(value) == "string" then return safe_text(string.sub(value, 1, error_bytes)) end
  return "(error object is a " .. type(value) .. " value)"
end

-- step(result) -> "command", cmd, arg, counter | "budget", counter | "error", text, counter
--               | "ended", counter
return function(result)
  local ok, value = coroutine.resume(co, result)
  if not ok then
    if rawequal(value, SENTINEL) then return "budget", counter end
    return "error", describe(value), counter
  end
  if coroutine.status(co) == "dead" then return "ended", counter end
  local arg = value.arg
  if value.cmd == "give_up" then arg = safe_text(string.sub(arg, 1, reason_bytes)) end
  return "command", value.cmd, arg, counter
end
"""


def run_program(level: Level, budget: Budget, source: str, settings: InterpSettings) -> dict:
    """Run ``source`` on ``level`` within ``budget`` and return the short report."""
    world = new_world(level, budget)
    instructions = 0
    try:
        sandbox = new_sandbox(settings)
        try:
            chunk = sandbox.load(source)
        except ProgramLoadError as error:
            return short_report(level.id, world, 0, lua_error(str(error)))
        step = sandbox.runtime.execute(
            DRIVER, chunk, settings.hook_every, budget.instructions, sandbox.safe_text,
            GIVE_UP_BYTES_MAX, ERROR_BYTES_MAX,
        )
        ending, world, instructions = _drive(step, world)
    except lua54.LuaMemoryError:
        ending = OUT_OF_MEMORY
    except Exception:
        LOG.exception("the driver failed on %s", level.id)
        ending = INTERNAL
    return short_report(level.id, world, instructions, ending)


def _drive(step, world: World) -> tuple[Ending, World, int]:
    """Resume the program until the run ends; return the ending, the last world and the count."""
    reply = step(None)
    while True:
        kind = reply[0]
        if kind == "budget":
            return LOST_ON_INSTRUCTIONS, world, reply[1]
        if kind == "error":
            return lua_error(reply[1]), world, reply[2]
        if kind == "ended":
            return PROGRAM_ENDED, world, reply[1]
        if kind != "command":
            raise RuntimeError(f"the driver chunk answered {kind!r}")
        cmd, arg, instructions = reply[1], reply[2], reply[3]
        if cmd == "give_up":
            return gave_up(arg), world, instructions
        result, world = _apply(world, cmd, arg)
        if world.status != PLAYING:
            return from_world(world), world, instructions
        reply = step(result)


def _apply(world: World, cmd: str, arg: str | None) -> tuple[bool | str | int, World]:
    """One robot command through the core: its result for the program, and the next world."""
    if cmd == "move":
        world, moved = core.move(world, arg)
        return moved, world
    if cmd == "look":
        return core.look(world, arg), world
    if cmd == "here":
        return core.here(world), world
    if cmd == "boxes_left":
        return core.boxes_left(world), world
    raise RuntimeError(f"unknown robot command {cmd!r}")
