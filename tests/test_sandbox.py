"""The minimal sandbox (v2.3, a contract): the allowlist, text-only loading, the robot API wrappers
that yield {cmd, arg}, one memory per runtime, and the runtime's trimmed globals. Real lupa."""

import json
import subprocess
import sys
from pathlib import Path

import lupa.lua54 as lua54
import pytest

from golem.interp.config import (
    DEFAULT_HOOK_EVERY,
    DEFAULT_LUA_MAX_MEMORY,
    InterpConfigError,
    InterpSettings,
    load_interp_settings,
)
from golem.interp.sandbox import (
    PROGRAM_TOO_LARGE,
    REMOVED_GLOBALS,
    ProgramLoadError,
    new_sandbox,
)

STEPPER = """function(chunk)
  local co = coroutine.create(chunk)
  return function(value)
    local ok, a = coroutine.resume(co, value)
    if not ok then return "error", a end
    if coroutine.status(co) == "dead" then return "done", a end
    return "cmd", a.cmd, a.arg
  end
end"""

ABSENT = [
    "python", "io", "os", "require", "load", "loadstring", "dofile", "loadfile", "debug", "pcall",
    "xpcall", "coroutine", "next", "rawget", "rawset", "rawequal", "rawlen", "setmetatable",
    "getmetatable", "collectgarbage", "print", "package", "_G", "pairs", "tostring", "string.dump",
    "string.format", "table.sort", "math.random", "math.randomseed", "_ENV.python", "_ENV._G",
]


def run(source: str, answers: dict | None = None):
    """Run a program to its end; answer each command from ``answers`` (by command name).

    Returns the commands it yielded and how it ended: ("done", value) or ("error", message).
    """
    sandbox = new_sandbox(InterpSettings())
    step = sandbox.runtime.eval(STEPPER)(sandbox.load(source))
    commands, reply = [], step(None)
    while reply[0] == "cmd":
        commands.append(reply[1:])
        reply = step((answers or {}).get(reply[1]))
    return commands, reply[:2]


@pytest.mark.parametrize("name", ABSENT)
def test_a_name_outside_the_allowlist_is_nil(name):
    assert run(f"return {name} == nil") == ([], ("done", True))


def test_strings_reach_only_the_trimmed_string_library():
    assert run("return ('').dump == nil and ('').format == nil and ('ab'):upper() == 'AB'") == (
        [], ("done", True))


def test_a_bytecode_chunk_is_refused():
    # made by a separate runtime that hands raw bytes back to Python
    bytecode = lua54.LuaRuntime(encoding=None).eval("string.dump(function() return 1 end)")
    assert isinstance(bytecode, bytes) and bytecode.startswith(b"\x1bLua")
    sandbox = new_sandbox(InterpSettings())
    with pytest.raises(ProgramLoadError, match="attempt to load a binary chunk"):
        sandbox.load(bytecode)


def test_the_allowed_names_work():
    source = """
    local t = {}
    for i, v in ipairs({3, 1, 2}) do t[#t + 1] = v * i end
    assert(type(t) == "table" and select("#", 1, 2, 3) == 3)
    local a, b = unpack({tonumber("4"), math.floor(2.7)})
    table.insert(t, a + b)
    return table.concat(t, ",") .. "|" .. string.rep("x", 2) .. ("y"):rep(2) .. math.max(1, 9)
    """
    assert run(source) == ([], ("done", "3,2,6,6|xxyy9"))


def test_error_and_assert_end_the_program_with_their_line():
    assert run("\nerror('boom')") == ([], ("error", "program:2: boom"))
    assert run("\n\nassert(false, 'no')") == ([], ("error", "program:3: no"))


def test_a_program_cannot_change_the_drivers_libraries():
    sandbox = new_sandbox(InterpSettings())
    step = sandbox.runtime.eval(STEPPER)(sandbox.load("string.upper = nil; math.floor = nil"))
    assert step(None)[0] == "done"
    assert sandbox.runtime.eval("string.upper('a') .. math.floor(1.5)") == "A1"


def test_memory_is_one_plain_table_per_runtime():
    sandbox = new_sandbox(InterpSettings())
    stepper = sandbox.runtime.eval(STEPPER)
    stepper(sandbox.load("memory.seen = 'first'"))(None)
    # a second program in the same runtime (a swap, from v2.5) sees the same memory
    assert stepper(sandbox.load("return memory.seen"))(None) == ("done", "first")
    assert sandbox.runtime.eval("getmetatable")(sandbox.runtime.eval("memory")) is None
    assert run("return memory.seen") == ([], ("done", None))  # a new runtime, a new memory


def test_each_command_yields_its_name_and_argument_and_returns_the_answer():
    source = """
    local seen = look("N")
    local moved = move("E")
    return seen .. tostring_free(moved) .. here() .. boxes_left()
    """.replace("tostring_free(moved)", '(moved and "T" or "F")')
    commands, ending = run(source, {"look": "wall", "move": True, "here": "goal", "boxes_left": 3})
    assert commands == [("look", "N"), ("move", "E"), ("here", None), ("boxes_left", None)]
    assert ending == ("done", "wallTgoal3")
    commands, _ = run('give_up("stuck")')
    assert commands == [("give_up", "stuck")]


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("\nmove('X')", 'program:2: move: the direction must be "N", "E", "S" or "W"'),
        ("\n\nlook(1)", 'program:3: look: the direction must be "N", "E", "S" or "W"'),
        ("move()", 'program:1: move: the direction must be "N", "E", "S" or "W"'),
        ("\ngive_up(7)", "program:2: give_up: the reason must be a string"),
        ("give_up()", "program:1: give_up: the reason must be a string"),
    ],
)
def test_a_bad_argument_is_a_lua_error_at_the_programs_line(source, message):
    assert run(source) == ([], ("error", message))


def test_safe_text_replaces_bytes_that_are_not_utf8():
    sandbox = new_sandbox(InterpSettings())
    assert sandbox.safe_text(b"ok \x93 \xff\xfe end") == "ok \ufffd \ufffd\ufffd end"
    assert sandbox.safe_text("naïve café → ok") == "naïve café → ok"
    assert sandbox.safe_text(b"") == ""


def test_a_syntax_error_carries_its_line():
    with pytest.raises(ProgramLoadError, match=r"^program:2: "):
        new_sandbox(InterpSettings()).load("local a = 1\nx = = 1")


def test_the_runtimes_unneeded_globals_are_removed():
    runtime = new_sandbox(InterpSettings()).runtime
    for name in REMOVED_GLOBALS:
        assert runtime.eval(name) is None, name
    # the driver's own tools stay
    assert runtime.eval("type(debug.sethook) .. type(coroutine.create) .. type(load)") == (
        "functionfunctionfunction")


def test_the_same_program_yields_the_same_commands_in_two_fresh_runtimes():
    source = """
    for i = 1, 50 do
      local d = ({"N", "E", "S", "W"})[i % 4 + 1]
      if look(d) == "empty" then move(d) end
    end
    give_up("done " .. #memory)
    """
    answers = {"look": "empty", "move": False}
    assert run(source, answers) == run(source, answers)


# --- settings -----------------------------------------------------------------------------------


def test_the_settings_have_their_defaults():
    assert load_interp_settings({}) == InterpSettings(DEFAULT_LUA_MAX_MEMORY, DEFAULT_HOOK_EVERY)
    assert (DEFAULT_LUA_MAX_MEMORY, DEFAULT_HOOK_EVERY) == (64 * 1024 * 1024, 1000)


def test_the_settings_read_the_environment():
    settings = load_interp_settings({"LUA_MAX_MEMORY": "1048576", "HOOK_EVERY": "100"})
    assert settings == InterpSettings(lua_max_memory=1048576, hook_every=100)


@pytest.mark.parametrize("name", ["LUA_MAX_MEMORY", "HOOK_EVERY"])
@pytest.mark.parametrize("value", ["abc", "0", "-5", "1.5"])
def test_a_bad_setting_is_refused(name, value):
    with pytest.raises(InterpConfigError, match=name):
        load_interp_settings({name: value})


def test_lupa_is_imported_only_by_the_interpreter():
    import ast
    from pathlib import Path

    package = Path(__file__).resolve().parent.parent / "golem"
    for path in package.rglob("*.py"):
        if path.is_relative_to(package / "interp"):
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            assert not any(n.split(".")[0] == "lupa" for n in names), path


# --- a program text that does not fit (v2.5 code review #1) -------------------------------------
# lupa pushes the text outside a protected call, so a failed allocation there makes Lua abort the
# whole process. These runs happen in a child process: a regression fails the test instead of
# killing pytest.

REPO = Path(__file__).resolve().parent.parent
CHILD_PRELUDE = """
import json
from pathlib import Path
from golem.core.levels import budget_for, load_budgets, load_level
from golem.interp.config import InterpSettings
from golem.interp.run import Run, run_program, swap
LEVELS = Path("levels")
T1 = "training/tier1/t1-01"
LEVEL, BUDGET = load_level(T1, LEVELS), budget_for(T1, load_budgets(LEVELS))
"""


def in_child(code: str) -> dict:
    done = subprocess.run([sys.executable, "-c", CHILD_PRELUDE + code], cwd=REPO,
                          capture_output=True, text=True, timeout=120)
    assert "PANIC" not in done.stderr and done.returncode == 0, done.stderr[-2000:]
    return json.loads(done.stdout.strip().splitlines()[-1])


def test_a_program_text_larger_than_the_memory_cap_is_refused_not_a_crash():
    report = in_child("""
small = InterpSettings(lua_max_memory=2 * 1024 * 1024)
print(json.dumps(run_program(LEVEL, BUDGET, "x = '" + "y" * (3 * 1024 * 1024) + "'", small)))
""")
    assert (report["status"], report["reason"], report["error"]) == (
        "failed", "error", PROGRAM_TOO_LARGE)


def test_a_swapped_in_text_that_does_not_fit_in_the_room_left_is_refused_not_a_crash():
    report = in_child("""
run = Run(LEVEL, BUDGET, InterpSettings())
run.start('give_up("first")')
run.drive()
runtime = run._sandbox.runtime
# as if the first program had left memory nearly full
runtime.set_max_memory(runtime.get_memory_used() + 1000)
swap(run, "-- " + "z" * 5000 + "\\nmove('E')")
run.drive()
print(json.dumps(run.report()))
""")
    assert (report["status"], report["reason"], report["error"]) == (
        "failed", "error", PROGRAM_TOO_LARGE)
    assert report["versions"] == [1, 2]


def test_garbage_is_collected_before_a_text_is_refused():
    sandbox = new_sandbox(InterpSettings(lua_max_memory=2 * 1024 * 1024))
    runtime = sandbox.runtime
    # with the automatic collector stopped, the garbage stays until load() collects it
    runtime.execute("collectgarbage('stop') "
                    "local garbage = {} for i = 1, 1200 do garbage[i] = string.rep('g', 1000) end")
    text = "-- " + "t" * (850 * 1024) + "\nreturn 1"
    limit = runtime.get_max_memory()
    assert runtime.get_memory_used() + len(text) > limit - 4096  # it fits only once collected
    assert callable(sandbox.load(text))
