"""The minimal sandbox (v2.3): one Lua runtime per run, the program's environment, and loading.

The runtime is ``lupa.lua54`` with ``register_eval=False``, ``register_builtins=False`` and
``max_memory``. lupa still leaves a ``python`` table in the runtime's globals, and that table
reaches Python objects (the v2.3 spike, F1), so the set-up chunk removes it, together with the
globals that nothing needs, before any program text is loaded. No Python object is ever passed into
Lua: the set-up is Lua code, and Python passes in only strings.

A program's globals are a fresh table, never ``_G``. Until v4.1 it holds only names whose behaviour
is already deterministic; ``pairs``, ``tostring``, ``string.format``, ``table.sort`` and
``math.random`` arrive in v4.1 in their deterministic versions.
"""

from dataclasses import dataclass

import lupa.lua54 as lua54

from golem.interp.config import InterpSettings

# The runtime's own globals that nothing needs; "python" reaches Python objects (spike F1).
REMOVED_GLOBALS = ("python", "io", "os", "package", "require", "dofile", "loadfile")

# Names a program sees, besides the robot API, memory and the three library tables.
BASE_NAMES = ("assert", "error", "ipairs", "select", "tonumber", "type", "unpack")

SETUP = r"""
local removed = ...
for i = 1, #removed do _G[removed[i]] = nil end

local next, type, error, load = next, type, error, load
local yield = coroutine.yield

local function copy(library, drop)
  local result = {}
  for name, value in next, library do
    if not drop[name] then result[name] = value end
  end
  return result
end

local string_library = copy(string, {dump = true, format = true})
local table_library = copy(table, {sort = true})
local math_library = copy(math, {random = true, randomseed = true})
-- Strings reach the string library through their metatable: point it at the trimmed copy, so that
-- ("").dump and ("").format are nil too.
getmetatable("").__index = string_library

local DIRECTIONS = {N = true, E = true, S = true, W = true}
local memory = {}  -- one per runtime: it belongs to the run, not to the program

local function direction(command, dir)
  if type(dir) ~= "string" or not DIRECTIONS[dir] then
    error(command .. ': the direction must be "N", "E", "S" or "W"', 3)
  end
end

local robot = {
  move = function(dir)
    direction("move", dir)
    return yield({cmd = "move", arg = dir})
  end,
  look = function(dir)
    direction("look", dir)
    return yield({cmd = "look", arg = dir})
  end,
  here = function()
    return yield({cmd = "here"})
  end,
  boxes_left = function()
    return yield({cmd = "boxes_left"})
  end,
  give_up = function(reason)
    if type(reason) ~= "string" then
      error("give_up: the reason must be a string", 2)
    end
    yield({cmd = "give_up", arg = reason})
    error("give_up does not return", 2)
  end,
}

local function new_environment()
  local env = {
    assert = assert, error = error, ipairs = ipairs, select = select,
    tonumber = tonumber, type = type, unpack = table.unpack,
    string = string_library, table = table_library, math = math_library,
    memory = memory,
  }
  for name, command in next, robot do env[name] = command end
  return env
end

-- safe_text(s): s with every byte that is not valid UTF-8 replaced by U+FFFD. lupa decodes
-- every Lua string it hands to Python as UTF-8 and raises on invalid bytes, so any text that a
-- program can shape (an error message, a give_up reason) passes through here first.
local utf8_len, sub, concat = utf8.len, string.sub, table.concat
local function safe_text(s)
  local parts, i = {}, 1
  while true do
    local ok, bad = utf8_len(s, i)
    if ok then parts[#parts + 1] = sub(s, i) break end
    parts[#parts + 1] = sub(s, i, bad - 1)
    parts[#parts + 1] = "\u{FFFD}"
    i = bad + 1
  end
  return concat(parts)
end

-- load_program(source) -> the chunk, or nil and the error message ("program:<line>: ...")
local function load_program(source)
  local chunk, message = load(source, "=program", "t", new_environment())
  if chunk == nil then return nil, safe_text(message) end
  return chunk
end

return load_program, safe_text
"""


class ProgramLoadError(Exception):
    """The program text does not load: a syntax error, or a chunk that is not text."""


@dataclass
class Sandbox:
    """One run's Lua runtime, its loader, and ``safe_text`` (a Lua function for the driver).

    ``runtime`` stays private to the interpreter.
    """

    runtime: lua54.LuaRuntime
    _loader: object
    safe_text: object

    def load(self, source: str | bytes):
        """The program's chunk (a Lua function), or ``ProgramLoadError`` with Lua's message."""
        chunk, message = _pair(self._loader(source))
        if chunk is None:
            raise ProgramLoadError(_text(message))
        return chunk


def new_sandbox(settings: InterpSettings) -> Sandbox:
    """A fresh runtime with the globals trimmed and the program loader installed."""
    runtime = lua54.LuaRuntime(
        register_eval=False,
        register_builtins=False,
        max_memory=settings.lua_max_memory,
    )
    removed = runtime.table_from(list(REMOVED_GLOBALS))
    loader, safe_text = runtime.execute(SETUP, removed)
    return Sandbox(runtime=runtime, _loader=loader, safe_text=safe_text)


def _pair(result) -> tuple:
    if isinstance(result, tuple):
        return (result + (None, None))[:2]
    return result, None


def _text(value) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)
