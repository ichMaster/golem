"""What the interpreter relies on in lupa's Lua 5.4 runtime (the v2.3 spike, kept as tests).

See specification/implementation/v2.3-lupa-spike.md. Real lupa, no network.
"""

import re
import tomllib
from pathlib import Path

import lupa
import lupa.lua54 as lua54
import pytest

REPO = Path(__file__).resolve().parent.parent


def fresh(**kwargs) -> lua54.LuaRuntime:
    return lua54.LuaRuntime(register_eval=False, register_builtins=False, **kwargs)


def test_lupa_is_the_pinned_version_with_lua_5_4():
    dependencies = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))["project"][
        "dependencies"
    ]
    pins = [re.fullmatch(r"lupa==([\d.]+)", d) for d in dependencies]
    pinned = [m.group(1) for m in pins if m]
    assert pinned == [lupa.__version__]
    assert fresh().lua_version == (5, 4)


def test_python_resumes_a_coroutine_that_yields_commands():
    make = fresh().eval("""
    function(src)
      local env = {look = function(d) return coroutine.yield({cmd = "look", arg = d}) end}
      local co = coroutine.create(assert(load(src, "=program", "t", env)))
      return function(value)
        local ok, a = coroutine.resume(co, value)
        if not ok then return "error", a end
        if coroutine.status(co) == "dead" then return "done", a end
        return "cmd", a.cmd, a.arg
      end
    end""")
    step = make(
        "local n = 0 for i = 1, 300 do if look('N') == 'wall' then n = n + 1 end end return n")
    reply = step(None)
    commands = 0
    while reply[0] == "cmd":
        assert reply[1:] == ("look", "N")
        commands += 1
        reply = step("wall")
    assert commands == 300
    assert reply == ("done", 300)


HOOKED = """
function(src, every, budget)
  local SENTINEL = {}
  local counter = 0
  local co = coroutine.create(assert(load(src, "=program", "t", {error = error})))
  debug.sethook(co, function()
    counter = counter + every
    if counter >= budget then error(SENTINEL, 0) end
  end, "", every)
  local ok, err = coroutine.resume(co)
  for i = 1, 100000 do end  -- the main state carries no hook
  return ok, rawequal(err, SENTINEL), type(err) == "string" and err or type(err), counter
end"""


def test_the_count_hook_ends_an_endless_loop_with_the_sentinel():
    ok, is_sentinel, _, counter = fresh().eval(HOOKED)("while true do end", 1000, 50_000)
    assert (ok, is_sentinel, counter) == (False, True, 50_000)


def test_a_programs_own_budget_message_is_not_the_sentinel():
    ok, is_sentinel, message, _ = fresh().eval(HOOKED)(
        'error("instruction budget exhausted")', 1000, 50_000)
    assert (ok, is_sentinel) == (False, False)
    assert message == "program:1: instruction budget exhausted"


def test_python_cannot_tell_lua_table_identity_so_the_sentinel_check_stays_in_lua():
    first, second = fresh().eval("function() local t = {} return t, t end")()
    assert first is not second


def test_max_memory_raises_and_the_runtime_survives():
    runtime = fresh(max_memory=1 << 20)
    with pytest.raises(lua54.LuaMemoryError):
        runtime.execute("local s = string.rep('x', 4 * 1024 * 1024)")
    inside = runtime.eval("""function()
      local big = function() return string.rep('x', 4 * 1024 * 1024) end
      return coroutine.resume(coroutine.create(big))
    end""")()
    assert inside == (False, "not enough memory")
    assert runtime.eval("1 + 1") == 2


def test_lupa_keeps_a_python_table_that_reaches_python_objects_until_it_is_removed():
    # F1 in the spike note: register_eval/register_builtins do not remove the table itself
    runtime = fresh()
    assert runtime.eval("type(python)") == "table"
    assert runtime.eval("python.none.__class__") is type(None)
    runtime.execute("python = nil")
    assert runtime.eval("python") is None
    assert runtime.eval("function(x) return x * 2 end")(21) == 42


def test_text_mode_refuses_bytecode_and_errors_carry_the_line():
    runtime = fresh()
    assert runtime.eval("load(string.dump(function() return 1 end), '=program', 't', {})") == (
        None, "attempt to load a binary chunk (mode is 't')")
    assert runtime.eval("select(2, load('x = = 1', '=program', 't', {}))").startswith("program:1:")
