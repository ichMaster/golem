"""``golem-local run`` (v2.3, a contract): the phase DoD end to end, in-process, over the fixture
programs; refusals exit 1; usage errors exit 2; a second run prints byte-identical output."""

import json
from pathlib import Path

import pytest

from golem.local import main

REPO = Path(__file__).resolve().parent.parent
LEVELS = REPO / "levels"
PROGRAMS = REPO / "tests" / "fixtures" / "programs"
HIDDEN_FIXTURE = REPO / "tests" / "fixtures" / "hidden" / "tier1" / "h-01.txt"
T1 = "training/tier1/t1-01"


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    """No .env from the repository and no settings from the shell reach these runs."""
    monkeypatch.chdir(tmp_path)
    for name in ("GOLEM_LEVELS_DIR", "LUA_MAX_MEMORY", "HOOK_EVERY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("GOLEM_LEVELS_DIR", str(LEVELS))


def local(capsys, *argv: str) -> tuple[int, str, str]:
    code = main(list(argv))
    out, err = capsys.readouterr()
    return code, out, err


def report_of(capsys, level: str, program: str) -> dict:
    code, out, err = local(capsys, "run", level, str(PROGRAMS / program))
    assert (code, err) == (0, "")
    assert out.endswith("\n") and out.count("\n") == 1
    return json.loads(out)


# --- the phase DoD ------------------------------------------------------------------------------


@pytest.mark.parametrize("level", ["t1-01", "t1-02", "t1-03"])
def test_the_hand_written_solver_passes_tier_one(capsys, level):
    report = report_of(capsys, f"training/tier1/{level}", "t1_solver.lua")
    assert (report["status"], report["reason"], report["error"]) == ("solved", None, None)


def test_an_infinite_loop_is_lost_on_instructions_and_the_runner_survives(capsys):
    report = report_of(capsys, T1, "infinite_loop.lua")
    assert (report["status"], report["reason"]) == ("lost", "instructions")
    assert report_of(capsys, T1, "give_up.lua")["status"] == "failed"


@pytest.mark.parametrize(
    ("program", "line"), [("syntax_error.lua", 3), ("runtime_error.lua", 4)])
def test_syntax_and_runtime_errors_are_reported_with_their_line(capsys, program, line):
    report = report_of(capsys, T1, program)
    assert (report["status"], report["reason"]) == ("failed", "error")
    assert report["error"].startswith(f"program:{line}: ")


def test_give_up_appears_in_the_report(capsys):
    report = report_of(capsys, T1, "give_up.lua")
    assert (report["status"], report["reason"], report["error"]) == ("failed", "give_up", "x")


def test_a_programs_own_budget_message_is_failed_on_error(capsys):
    report = report_of(capsys, T1, "own_budget_error.lua")
    assert (report["status"], report["reason"]) == ("failed", "error")
    assert report["error"] == "program:2: instruction budget exhausted"


@pytest.mark.parametrize("program", sorted(p.name for p in PROGRAMS.glob("*.lua")))
def test_every_fixture_program_prints_byte_identical_output_twice(capsys, program):
    first = local(capsys, "run", T1, str(PROGRAMS / program))
    second = local(capsys, "run", T1, str(PROGRAMS / program))
    assert first == second
    assert first[0] == 0


def test_the_report_has_the_short_reports_keys_in_order(capsys):
    report = report_of(capsys, T1, "t1_solver.lua")
    assert list(report) == ["level", "status", "reason", "steps", "instructions", "error"]


# --- refusals and usage ------------------------------------------------------------------------


def refusal(capsys, *argv: str) -> dict:
    code, out, err = local(capsys, *argv)
    assert code == 1
    assert "Traceback" not in err
    body = json.loads(out)
    assert set(body) == {"error", "detail"}
    return body


def test_hidden_and_unknown_levels_are_refused_alike(capsys, monkeypatch, tmp_path):
    root = tmp_path / "levels"
    (root / "hidden" / "tier1").mkdir(parents=True)
    (root / "hidden" / "tier1" / "h-01.txt").write_text(
        HIDDEN_FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    (root / "training").symlink_to(LEVELS / "training")
    (root / "budgets.toml").write_text((LEVELS / "budgets.toml").read_text(), encoding="utf-8")
    monkeypatch.setenv("GOLEM_LEVELS_DIR", str(root))
    program = str(PROGRAMS / "give_up.lua")
    replies = [refusal(capsys, "run", level, program)
               for level in ("hidden/tier1/h-01", "hidden/tier1/missing", "training/tier1/missing",
                             "../levels/training/tier1/t1-01")]
    assert all(reply == {"error": "unknown_level", "detail": "unknown level"} for reply in replies)


def test_a_missing_or_non_utf8_program_is_refused(capsys, tmp_path):
    assert refusal(capsys, "run", T1, str(tmp_path / "nope.lua"))["error"] == "bad_program"
    binary = tmp_path / "binary.lua"
    binary.write_bytes(b"\xff\xfe\x00 not text")
    assert "not UTF-8" in refusal(capsys, "run", T1, str(binary))["detail"]


def test_a_bad_setting_is_refused(capsys, monkeypatch):
    monkeypatch.setenv("HOOK_EVERY", "0")
    assert refusal(capsys, "run", T1, str(PROGRAMS / "give_up.lua"))["error"] == "bad_setting"


@pytest.mark.parametrize("argv", [[], ["run"], ["run", T1], ["walk", T1, "x.lua"]])
def test_a_usage_error_exits_2(capsys, argv):
    with pytest.raises(SystemExit) as stop:
        main(argv)
    assert stop.value.code == 2
    assert "Traceback" not in capsys.readouterr().err


def test_dot_env_in_the_working_directory_is_read_without_changing_the_environment(
        capsys, monkeypatch, tmp_path):
    import os

    monkeypatch.delenv("GOLEM_LEVELS_DIR")
    (tmp_path / ".env").write_text(f"GOLEM_LEVELS_DIR={LEVELS}\n", encoding="utf-8")
    assert report_of(capsys, T1, "give_up.lua")["status"] == "failed"
    assert "GOLEM_LEVELS_DIR" not in os.environ
