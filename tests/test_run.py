"""A run and the swap (v2.5): a second program takes over the same run with the same world, the
same `memory` and the counters carried over, and the old coroutine is dead. Real lupa; programs are
written inline."""

import json
from pathlib import Path

import lupa.lua54 as lua54
import pytest

from golem.core.levels import budget_for, load_budgets, load_level
from golem.interp.config import InterpSettings
from golem.interp.run import Run, SwapRefused, frame, run_program, swap

REPO = Path(__file__).resolve().parent.parent
LEVELS = REPO / "levels"
T1 = "training/tier1/t1-01"
SETTINGS = InterpSettings()
DEADLOCK = " ".join(f'move("{d}")' for d in "SENWNEE")


def new_run(level_id: str = T1, settings: InterpSettings = SETTINGS, on_move=None) -> Run:
    level = load_level(level_id, LEVELS)
    return Run(level, budget_for(level_id, load_budgets(LEVELS)), settings, on_move=on_move)


def swapped(first: str, *more: str, level_id: str = T1, on_move=None) -> Run:
    """Run ``first``, then swap in each of ``more`` in turn, driving each to its end."""
    run = new_run(level_id, on_move=on_move)
    run.start(first)
    run.drive()
    for source in more:
        swap(run, source)
        run.drive()
    return run


def ending(run: Run) -> tuple:
    report = run.report()
    return report["status"], report["reason"], report["error"]


# --- what carries over -------------------------------------------------------------------------


def test_the_second_program_reads_the_memory_the_first_one_wrote():
    run = swapped('memory.note = "from one" memory.list = {1, 2} give_up("done")',
                  'give_up(memory.note .. " " .. #memory.list)')
    assert ending(run) == ("failed", "give_up", "from one 2")


def test_the_steps_continue_from_the_swap_point():
    first = 'move("N") move("S") move("N") give_up("three")'
    run = swapped(first, 'move("S") move("N") give_up("two more")')
    assert run.report()["steps"] == 5
    assert ending(run) == ("failed", "give_up", "two more")


def test_the_instruction_count_carries_over_and_never_goes_back():
    run = new_run()
    run.start('for i = 1, 100000 do end give_up("spent")')
    run.drive()
    spent = run.instructions
    assert spent >= 100000
    swap(run, 'for i = 1, 1000 do end give_up("a little more")')
    run.drive()
    # a counter that restarted at the swap would read about 1000 here
    assert run.instructions >= spent


def test_the_hook_is_active_after_a_swap_and_leaves_the_second_program_only_the_rest():
    # each loop turn is about one instruction, and the tier-one budget is 1,000,000
    second = 'for i = 1, 500000 do end give_up("finished")'
    alone = run_program(load_level(T1, LEVELS), budget_for(T1, load_budgets(LEVELS)), second,
                        SETTINGS)
    assert (alone["status"], alone["error"]) == ("failed", "finished")
    run = swapped('for i = 1, 700000 do end give_up("most of it")', second)
    assert ending(run) == ("lost", "instructions", None)


def test_an_endless_loop_swapped_in_ends_on_the_instruction_budget():
    run = swapped('give_up("first")', "while true do end")
    assert ending(run) == ("lost", "instructions", None)


def test_the_old_coroutine_is_dead_after_a_swap():
    run = swapped('give_up("first")', 'give_up("second")')
    assert tuple(run.resume_previous()) == (False, "cannot resume dead coroutine")


def test_the_frames_continue_across_a_swap():
    level = load_level(T1, LEVELS)
    steps = []
    run = swapped('move("N") move("S") give_up("x")', 'move("E") move("E")',
                  on_move=lambda world, d, moved: steps.append(frame(world, d, moved)["step"]))
    assert steps == [1, 2, 3, 4]
    assert ending(run) == ("solved", None, None) and level.id == run.report()["level"]


# --- when a swap is allowed --------------------------------------------------------------------


@pytest.mark.parametrize(
    "first", ['give_up("stuck")', "local a = 1", "local f = nil f()", "x = = 1"],
    ids=["give_up", "returned", "lua_error", "load_error"])
def test_a_program_that_stopped_while_the_level_goes_on_can_be_swapped(first):
    run = swapped(first, 'move("E") move("E")')
    assert ending(run) == ("solved", None, None)
    assert run.versions == [1, 2]


@pytest.mark.parametrize(
    "first",
    ['move("E") move("E")', 'while true do move("N") end', DEADLOCK, "while true do end"],
    ids=["solved", "lost_on_steps", "lost_on_deadlock", "lost_on_instructions"])
def test_a_level_that_has_ended_refuses_a_swap_and_stays_as_it_was(first):
    run = swapped(first)
    before = (run.report(), list(run.versions))
    with pytest.raises(SwapRefused):
        swap(run, 'give_up("never")')
    assert (run.report(), run.versions) == before


def test_a_program_that_is_still_running_refuses_a_swap():
    run = new_run()
    run.start('give_up("x")')
    with pytest.raises(SwapRefused):
        swap(run, 'give_up("y")')


def test_a_program_that_hits_the_memory_cap_can_be_swapped():
    # inside the program the cap is an ordinary Lua error, and the runtime stays usable
    small = InterpSettings(lua_max_memory=2 * 1024 * 1024)
    run = new_run(settings=small)
    run.start("memory.t = {} for i = 1, 1e7 do memory.t[i] = i end")
    run.drive()
    assert ending(run) == ("failed", "error", "not enough memory")
    swap(run, 'move("E") move("E")')
    run.drive()
    assert ending(run) == ("solved", None, None)


def test_a_memory_error_outside_the_program_refuses_a_swap(monkeypatch):
    def out_of_memory(*args):
        raise lua54.LuaMemoryError("not enough memory")

    run = new_run()
    run.start('move("E")')
    with monkeypatch.context() as patch:
        patch.setattr("golem.interp.run.drive", out_of_memory)
        run.drive()
    assert ending(run) == ("failed", "error", "not enough memory")
    with pytest.raises(SwapRefused):
        swap(run, 'move("E") move("E")')


def test_a_driver_failure_refuses_a_swap(monkeypatch):
    def broken(*args):
        raise RuntimeError("a bug in the core")

    run = new_run()
    run.start('move("E")')
    with monkeypatch.context() as patch:
        patch.setattr("golem.core.world.move", broken)
        run.drive()
    assert ending(run) == ("failed", "internal", "internal error")
    with pytest.raises(SwapRefused):
        swap(run, 'move("E") move("E")')


def test_a_swapped_in_program_that_does_not_load_ends_the_run_with_its_error():
    run = swapped('give_up("first")', "local a = 1\nx = = 1")
    status, reason, error = ending(run)
    assert (status, reason) == ("failed", "error") and error.startswith("program:2: ")
    assert run.versions == [1, 2]
    swap(run, 'move("E") move("E")')
    run.drive()
    assert ending(run) == ("solved", None, None) and run.versions == [1, 2, 3]


# --- the versions in the report (GOLEM-028) ----------------------------------------------------


def test_the_report_names_the_versions_that_drove_the_run():
    level = load_level(T1, LEVELS)
    single = run_program(level, budget_for(T1, load_budgets(LEVELS)), 'move("E")', SETTINGS)
    assert single["versions"] == [1]
    assert swapped('give_up("a")', 'move("E") move("E")').report()["versions"] == [1, 2]
    # a swapped-in program that does not load still counts: the error in the report is its own
    assert swapped('give_up("a")', "x = = 1").report()["versions"] == [1, 2]
    report = swapped('give_up("a")', 'give_up("b")', 'move("E") move("E")').report()
    assert (report["status"], report["versions"]) == ("solved", [1, 2, 3])


# --- the sandbox and determinism ---------------------------------------------------------------

HIDDEN_NAMES = ("install", "step", "resume_previous", "previous", "co", "counter", "SENTINEL",
                "coroutine", "debug", "_G", "python")


def test_neither_program_reaches_the_driver_or_the_runtimes_globals():
    probe = "give_up(" + ' .. "," .. '.join(f"type({name})" for name in HIDDEN_NAMES) + ")"
    expected = ",".join("nil" for _ in HIDDEN_NAMES)
    run = new_run()
    run.start(probe)
    run.drive()
    assert ending(run) == ("failed", "give_up", expected)
    swap(run, probe)
    run.drive()
    assert ending(run) == ("failed", "give_up", expected)


def test_a_swapped_run_twice_gives_byte_identical_reports_and_frames():
    def once() -> str:
        frames = []
        run = swapped('memory.n = 0 for i = 1, 5000 do memory.n = memory.n + 1 end '
                      'move("N") move("S") give_up("n")',
                      'move("E") if memory.n == 5000 then move("E") end',
                      on_move=lambda world, d, moved: frames.append(frame(world, d, moved)))
        return json.dumps([run.report(), run.versions, frames])

    assert once() == once()
