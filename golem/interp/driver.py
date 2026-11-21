"""The driver (v2.3, the swap from v2.5): a program's coroutine, one robot command at a time.

The program runs in a Lua coroutine. Each robot command yields ``{cmd, arg}``; the driver applies
it through the core and resumes the coroutine with the result. A small driver chunk, run in the
runtime's globals, holds ``coroutine``, ``debug``, the instruction counter and the budget sentinel
in its upvalues, where the program cannot reach them:

- the count hook adds ``HOOK_EVERY`` to the counter on every call, and raises the sentinel once the
  counter reaches the level's instruction budget;
- the sentinel is recognized in Lua with ``rawequal`` (Python cannot compare Lua tables by identity,
  see the v2.3 spike), so a program's own ``error("instruction budget exhausted")`` is an ordinary
  error;
- ``install(chunk)`` makes a chunk the running program. A swap (v2.5) installs a second chunk into
  the same closure: the old coroutine is closed, the hook goes onto the new one, and the counter
  carries over.

``golem.interp.run`` builds a run on this module: the runtime, the world and the programs that drive
it. Every way a run can end, including a bug here, becomes a report there; nothing escapes.
"""

from golem.core import world as core
from golem.core.world import PLAYING, World
from golem.interp.report import (
    LOST_ON_INSTRUCTIONS,
    PROGRAM_ENDED,
    Ending,
    from_world,
    gave_up,
    lua_error,
)

# A give_up reason is cut to 200 characters and an error text to 500; at most 4 bytes a character,
# so no more than 800 and 2000 bytes of them ever cross into Python.
GIVE_UP_BYTES_MAX = 800
ERROR_BYTES_MAX = 2000

DRIVER = r"""
local every, budget, safe_text, reason_bytes, error_bytes = ...
local SENTINEL = {}
local counter = 0
local co, previous

local function hook()
  counter = counter + every
  if counter >= budget then error(SENTINEL, 0) end
end

local function describe(value)
  if type(value) == "string" then return safe_text(string.sub(value, 1, error_bytes)) end
  return "(error object is a " .. type(value) .. " value)"
end

-- install(chunk): the chunk becomes the program's coroutine, with the count hook on it. A coroutine
-- installed before is closed, so it can never be resumed again; the counter carries over.
local function install(chunk)
  if co ~= nil then
    coroutine.close(co)
    previous = co
  end
  co = coroutine.create(chunk)
  debug.sethook(co, hook, "", every)
end

-- step(result) -> "command", cmd, arg, counter | "budget", counter | "error", text, counter
--               | "ended", counter
local function step(result)
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

-- resume_previous() -> false, message: the coroutine that a swap closed, resumed again. Only the
-- tests call it, to show that a swapped-out program can never run again.
local function resume_previous()
  return coroutine.resume(previous)
end

return step, install, resume_previous
"""


def drive(step, world: World, on_move=None) -> tuple[Ending, World, int]:
    """Resume the installed program until it ends; return the ending, the last world and the count.

    ``on_move(world, direction, moved)``, when given, is called after every ``move``.
    """
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
        if cmd == "move" and on_move is not None:
            on_move(world, arg, result)
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
