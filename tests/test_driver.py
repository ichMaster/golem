"""The driver (v2.3): commands through the core, the step and instruction budgets, every ending, and
byte-identical reports on a second run. Real lupa; programs are written inline."""

import json
from pathlib import Path

import pytest

from golem.core.levels import budget_for, load_budgets, load_level
from golem.core.replay import replay
from golem.core.world import boxes_left, here, look, render
from golem.interp.config import InterpSettings
from golem.interp.run import run_program, run_with_frames

REPO = Path(__file__).resolve().parent.parent
LEVELS = REPO / "levels"
T1 = "training/tier1/t1-01"
SETTINGS = InterpSettings()


def run(source: str, level_id: str = T1, settings: InterpSettings = SETTINGS) -> dict:
    level = load_level(level_id, LEVELS)
    return run_program(level, budget_for(level_id, load_budgets(LEVELS)), source, settings)


def moves_program(moves: str) -> str:
    return "\n".join(f'move("{d}")' for d in moves)


PROGRAMS = {
    "solve": moves_program("EE"),
    "wall": 'while true do move("N") end',
    "deadlock": moves_program("SENWNEE"),
    "loop": "while true do end",
    "look_loop": 'while true do look("N") end',
    "own_budget": 'error("instruction budget exhausted")',
    "give_up": 'give_up("x")',
    "ends": "local a = 1",
    "syntax": "local a = 1\nx = = 1",
    "runtime": "local a = 1\n\nlocal f = nil\nf()",
    "table_error": "error({})",
}


def test_the_recorded_solution_solves_the_level_with_the_cores_step_count():
    final, _ = replay(load_level(T1, LEVELS), "EE", budget_for(T1, load_budgets(LEVELS)))
    report = run(PROGRAMS["solve"])
    assert report == {"level": T1, "status": "solved", "reason": None, "steps": final.steps,
                      "instructions": 0, "error": None}


def test_look_here_and_boxes_left_answer_as_the_core_does():
    level = load_level(T1, LEVELS)
    _, states = replay(level, "", budget_for(T1, load_budgets(LEVELS)))
    world = states[0]
    expected = [look(world, d) for d in "NESW"] + [here(world), str(boxes_left(world))]
    program = """
    local seen = {look("N"), look("E"), look("S"), look("W"), here(), boxes_left() .. ""}
    give_up(table.concat(seen, ","))
    """
    assert run(program)["error"] == ",".join(expected)


def test_moves_into_a_wall_spend_the_step_budget():
    report = run(PROGRAMS["wall"])
    assert (report["status"], report["reason"], report["steps"]) == ("lost", "steps", 200)


def test_a_push_into_a_corner_is_lost_on_deadlock():
    report = run(PROGRAMS["deadlock"])
    assert (report["status"], report["reason"], report["steps"]) == ("lost", "deadlock", 7)


@pytest.mark.parametrize("name", ["loop", "look_loop"])
def test_an_endless_loop_ends_on_the_instruction_budget(name):
    report = run(PROGRAMS[name])
    budget = budget_for(T1, load_budgets(LEVELS)).instructions
    assert (report["status"], report["reason"]) == ("lost", "instructions")
    assert budget <= report["instructions"] < budget + SETTINGS.hook_every


def test_a_programs_own_budget_message_is_an_error_not_a_loss():
    report = run(PROGRAMS["own_budget"])
    assert (report["status"], report["reason"]) == ("failed", "error")
    assert report["error"] == "program:1: instruction budget exhausted"


def test_give_up_ends_the_run_with_its_reason_cut_to_200_characters():
    assert run(PROGRAMS["give_up"])["error"] == "x"
    report = run('give_up(string.rep("é", 500))')
    assert (report["status"], report["reason"]) == ("failed", "give_up")
    assert report["error"] == "é" * 200


def test_a_program_that_returns_has_given_up():
    report = run(PROGRAMS["ends"])
    assert (report["status"], report["reason"], report["error"]) == (
        "failed", "give_up", "program ended")


def test_syntax_and_runtime_errors_carry_their_line():
    syntax = run(PROGRAMS["syntax"])
    assert (syntax["status"], syntax["reason"]) == ("failed", "error")
    assert syntax["error"].startswith("program:2: ")
    runtime = run(PROGRAMS["runtime"])
    assert runtime["error"].startswith("program:4: attempt to call a nil value")


def test_an_error_value_that_is_not_a_string_gets_a_fixed_text():
    assert run(PROGRAMS["table_error"])["error"] == "(error object is a table value)"
    assert run("error(print)")["error"] == "(error object is a nil value)"


def test_text_that_is_not_utf8_reaches_the_report_cleaned():
    assert run('error("\\147 bad", 0)')["error"] == "� bad"
    assert run('give_up("\\255ok")')["error"] == "�ok"


def test_the_memory_cap_ends_the_program_and_the_next_run_works():
    small = InterpSettings(lua_max_memory=2 * 1024 * 1024)
    report = run("local s = string.rep('x', 8 * 1024 * 1024)", settings=small)
    assert (report["status"], report["reason"], report["error"]) == (
        "failed", "error", "not enough memory")
    assert run(PROGRAMS["solve"], settings=small)["status"] == "solved"


def test_a_driver_failure_ends_the_run_as_internal_and_the_next_run_works(monkeypatch):
    def broken(*args):
        raise RuntimeError("a bug in the core")

    with monkeypatch.context() as patch:
        patch.setattr("golem.core.world.move", broken)
        report = run(PROGRAMS["solve"])
    assert (report["status"], report["reason"], report["error"]) == (
        "failed", "internal", "internal error")
    assert run(PROGRAMS["solve"])["status"] == "solved"


def test_the_level_is_never_resumed_after_it_ends():
    # after the solving move, the program would loop for ever: it must not be resumed
    report = run('move("E") move("E") while true do end')
    assert report["status"] == "solved"


@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_every_program_gives_a_byte_identical_report_twice(name):
    assert json.dumps(run(PROGRAMS[name])) == json.dumps(run(PROGRAMS[name]))


def test_a_huge_error_text_is_cut_to_500_characters():
    # code review #2: the error text had no cap, so one program could put megabytes in its report
    report = run("error(string.rep('x', 5 * 1024 * 1024))")
    assert (report["status"], report["reason"]) == ("failed", "error")
    assert report["error"].startswith("program:1: xxx")
    assert len(report["error"]) == 500


def test_a_huge_syntax_error_is_cut_to_500_characters():
    # an unfinished string literal: Lua quotes the whole literal in its message
    report = run("x = '" + "y" * (1024 * 1024) + "\nz = 1")
    assert report["error"].startswith("program:1: unfinished string")
    assert len(report["error"]) <= 500


# --- frames (v2.4): the map before the first move and after every move ------------------------

SOLUTIONS = REPO / "tests" / "fixtures" / "solutions" / "training" / "tier1"


def recorded(name: str) -> str:
    lines = (SOLUTIONS / f"{name}.txt").read_text(encoding="utf-8").splitlines()
    return "".join(line.strip().replace(" ", "") for line in lines if not line.startswith(";"))


def framed(source: str, level_id: str = T1) -> tuple[dict, list[dict]]:
    level = load_level(level_id, LEVELS)
    return run_with_frames(level, budget_for(level_id, load_budgets(LEVELS)), source, SETTINGS)


@pytest.mark.parametrize("name", ["t1-01", "t1-02", "t1-03"])
def test_the_frames_of_a_recorded_solution_are_the_cores_replay(name):
    level_id = f"training/tier1/{name}"
    moves = recorded(name)
    budget = budget_for(level_id, load_budgets(LEVELS))
    _, states = replay(load_level(level_id, LEVELS), moves, budget)
    report, frames = framed(moves_program(moves), level_id)
    assert report["status"] == "solved"
    assert [f["map"] for f in frames] == [render(world) for world in states]
    assert [f["step"] for f in frames] == list(range(len(moves) + 1))
    assert [f["dir"] for f in frames] == [None, *moves]
    assert frames[0] == {"step": 0, "dir": None, "moved": None, "map": render(states[0])}


def test_a_bump_is_a_frame_with_the_same_map_and_a_counted_step():
    _, frames = framed('move("N") move("N") give_up("stop")')
    assert [(f["step"], f["dir"], f["moved"]) for f in frames] == [
        (0, None, None), (1, "N", True), (2, "N", False)]
    assert frames[1]["map"] == frames[2]["map"] != frames[0]["map"]


def test_look_here_and_boxes_left_add_no_frame():
    _, frames = framed('look("N") here() boxes_left() move("E") look("E") give_up("x")')
    assert [f["dir"] for f in frames] == [None, "E"]


def test_a_program_that_never_runs_has_only_the_first_frame():
    report, frames = framed("x = = 1")
    assert report["reason"] == "error"
    assert len(frames) == 1 and frames[0]["step"] == 0


@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_the_framed_report_equals_the_plain_one_and_both_repeat_exactly(name):
    report, frames = framed(PROGRAMS[name])
    assert report == run(PROGRAMS[name])
    assert json.dumps([report, frames]) == json.dumps(list(framed(PROGRAMS[name])))

