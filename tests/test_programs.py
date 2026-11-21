"""The programs folder (v2.4): the catalog lists and reads programs by name only, and every example
program in programs/ runs to a report on every tier-one level. Real lupa."""

import json
from pathlib import Path

import pytest

from golem.core.levels import budget_for, load_budgets, load_level
from golem.interp.config import InterpSettings
from golem.interp.run import run_with_frames
from golem.server.programs import (
    BadProgram,
    UnknownProgram,
    describe,
    list_programs,
    read_program,
)

REPO = Path(__file__).resolve().parent.parent
LEVELS = REPO / "levels"
PROGRAMS = REPO / "programs"
TIER1 = ["training/tier1/t1-01", "training/tier1/t1-02", "training/tier1/t1-03"]
EXAMPLES = sorted(p.name for p in PROGRAMS.glob("*.lua"))


# --- the catalog ---------------------------------------------------------------------------------


def make_folder(tmp_path: Path) -> Path:
    folder = tmp_path / "programs"
    folder.mkdir()
    (folder / "b.lua").write_text("-- Second program.\nmove('E')\n", encoding="utf-8")
    (folder / "a_1.lua").write_text("-- First   program  \ngive_up('x')\n", encoding="utf-8")
    (folder / "no-comment.lua").write_text("move('N')\n", encoding="utf-8")
    (folder / "Upper.lua").write_text("-- not listed\n", encoding="utf-8")
    (folder / "notes.txt").write_text("not a program\n", encoding="utf-8")
    (folder / ".hidden.lua").write_text("-- not listed\n", encoding="utf-8")
    (folder / "sub").mkdir()
    (folder / "sub" / "inner.lua").write_text("-- not listed\n", encoding="utf-8")
    return folder


def test_the_listing_is_sorted_and_holds_only_valid_names(tmp_path):
    folder = make_folder(tmp_path)
    listing = list_programs(folder)
    assert [p["name"] for p in listing] == ["a_1.lua", "b.lua", "no-comment.lua"]
    assert [p["description"] for p in listing] == ["First   program", "Second program.", ""]
    assert listing[1]["size"] == (folder / "b.lua").stat().st_size


def test_a_missing_folder_or_none_lists_nothing(tmp_path):
    assert list_programs(tmp_path / "missing") == []
    assert list_programs(None) == []


@pytest.mark.parametrize(
    "name", ["../x.lua", "/etc/x.lua", "x.txt", "Upper.lua", "", "sub/inner.lua", ".hidden.lua",
             "missing.lua", "a" * 61 + ".lua", None, 7])
def test_read_program_refuses_anything_but_a_program_name(tmp_path, name):
    folder = make_folder(tmp_path)
    (tmp_path / "x.lua").write_text("-- outside\n", encoding="utf-8")
    with pytest.raises(UnknownProgram):
        read_program(folder, name)


def test_a_symlink_out_of_the_folder_is_neither_listed_nor_read(tmp_path):
    folder = make_folder(tmp_path)
    outside = tmp_path / "secret.lua"
    outside.write_text("-- outside the folder\n", encoding="utf-8")
    (folder / "link.lua").symlink_to(outside)
    assert "link.lua" not in [p["name"] for p in list_programs(folder)]
    with pytest.raises(UnknownProgram):
        read_program(folder, "link.lua")


def test_a_bom_is_dropped_and_bytes_that_are_not_utf8_are_refused(tmp_path):
    folder = make_folder(tmp_path)
    (folder / "bom.lua").write_bytes(b"\xef\xbb\xbf-- With a BOM.\nmove('E')\n")
    (folder / "binary.lua").write_bytes(b"\xff\xfe\x00 not text")
    assert read_program(folder, "bom.lua").startswith("-- With a BOM.")
    with pytest.raises(BadProgram):
        read_program(folder, "binary.lua")
    listed = {p["name"]: p["description"] for p in list_programs(folder)}
    assert listed["bom.lua"] == "With a BOM." and listed["binary.lua"] == ""


def test_a_description_is_the_first_comment_line_cut_to_120_characters():
    assert describe("--[[ block\n") == "[[ block"
    assert describe("-- " + "x" * 300) == "x" * 120
    assert describe("\n-- second line") == ""


# --- the example programs ----------------------------------------------------------------------


def framed(name: str, level_id: str) -> tuple[dict, list[dict]]:
    level = load_level(level_id, LEVELS)
    source = read_program(PROGRAMS, name)
    return run_with_frames(level, budget_for(level_id, load_budgets(LEVELS)), source,
                           InterpSettings())[:2]


def test_the_examples_are_listed_with_descriptions():
    listing = list_programs(PROGRAMS)
    assert [p["name"] for p in listing] == EXAMPLES
    assert set(EXAMPLES) >= {"t1_solver.lua", "explorer.lua", "lost_on_steps.lua",
                             "lost_on_deadlock.lua", "endless_loop.lua", "gives_up.lua",
                             "runtime_error.lua"}
    assert all(p["description"] for p in listing)


@pytest.mark.parametrize("level_id", TIER1)
@pytest.mark.parametrize("name", EXAMPLES)
def test_every_example_ends_in_a_report_and_repeats_exactly(name, level_id):
    report, frames = framed(name, level_id)
    assert report["status"] in ("solved", "lost", "failed") and report["reason"] != "internal"
    assert frames[0]["step"] == 0 and len(frames) == 1 + sum(1 for f in frames if f["dir"])
    assert json.dumps([report, frames]) == json.dumps(list(framed(name, level_id)))


@pytest.mark.parametrize("level_id", TIER1)
def test_the_solver_solves_every_tier_one_level(level_id):
    assert framed("t1_solver.lua", level_id)[0]["status"] == "solved"


@pytest.mark.parametrize(
    ("name", "status", "reason"),
    [
        ("lost_on_steps.lua", "lost", "steps"),
        ("lost_on_deadlock.lua", "lost", "deadlock"),
        ("endless_loop.lua", "lost", "instructions"),
        ("gives_up.lua", "failed", "give_up"),
        ("explorer.lua", "failed", "give_up"),
        ("runtime_error.lua", "failed", "error"),
        ("explore.lua", "failed", "give_up"),
        ("finish.lua", "failed", "give_up"),
    ],
)
def test_each_demonstration_ends_as_its_name_says_on_t1_01(name, status, reason):
    report, _ = framed(name, TIER1[0])
    assert (report["status"], report["reason"]) == (status, reason)
    if name == "runtime_error.lua":
        assert report["error"].startswith("program:6: ")
    if name == "explorer.lua":
        assert report["error"] == "?#####?/#     #/# @$ .#/#     #/?#####?"


FIXTURES = REPO / "tests" / "fixtures" / "programs"


@pytest.mark.parametrize("name", ["explore.lua", "finish.lua"])
def test_the_pages_swap_examples_are_the_swap_fixtures(name):
    # v2.5: the page offers the same pair that golem-local --swap and the tests use, byte for byte
    assert (PROGRAMS / name).read_bytes() == (FIXTURES / name).read_bytes()


def test_the_pair_solves_t1_01_when_the_second_is_swapped_in():
    level = load_level(TIER1[0], LEVELS)
    report, _, _ = run_with_frames(
        level, budget_for(TIER1[0], load_budgets(LEVELS)), read_program(PROGRAMS, "explore.lua"),
        InterpSettings(), second=read_program(PROGRAMS, "finish.lua"))
    assert (report["status"], report["versions"]) == ("solved", [1, 2])
