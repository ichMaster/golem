"""The level parser: the character table, comments, ragged rows and every validation error."""

import dataclasses

import pytest

from golem.core.level import Level, LevelError, parse_level


def parse(text: str) -> Level:
    return parse_level(text, "test/tier1/t")


def error_of(text: str) -> LevelError:
    with pytest.raises(LevelError) as caught:
        parse(text)
    return caught.value


# --- valid levels -----------------------------------------------------------------------------


def test_a_simple_level():
    level = parse("#####\n#@$.#\n#####\n")
    assert level.id == "test/tier1/t"
    assert (level.width, level.height) == (5, 3)
    assert level.robot == (1, 1)
    assert level.boxes == frozenset({(1, 2)})
    assert level.goals == frozenset({(1, 3)})
    assert (0, 0) in level.walls and (2, 4) in level.walls
    assert len(level.walls) == 12


def test_every_cell_character():
    level = parse(
        "########\n"
        "#+ -_$*#\n"
        "#$.    #\n"
        "########\n"
    )
    assert level.robot == (1, 1)  # '+' is the robot on a goal
    assert level.boxes == frozenset({(1, 5), (1, 6), (2, 1)})  # '$' twice and '*'
    assert level.goals == frozenset({(1, 1), (1, 6), (2, 2)})  # '+', '*' and '.'
    for floor in [(1, 2), (1, 3), (1, 4), (2, 3)]:  # ' ', '-', '_', ' '
        assert floor not in level.walls | level.boxes | level.goals


def test_the_level_is_immutable():
    level = parse("#####\n#@$.#\n#####\n")
    with pytest.raises(dataclasses.FrozenInstanceError):
        level.robot = (1, 2)  # type: ignore[misc]
    assert isinstance(level.walls, frozenset)


def test_comments_are_skipped_and_rows_count_map_lines_only():
    level = parse("; a title\n#####\n; between rows\n#@$.#\n#####\n")
    assert level.height == 3
    assert level.robot == (1, 1)


def test_ragged_rows():
    level = parse(
        "####\n"
        "#@$.###\n"
        "#     #\n"
        "#######\n"
    )
    assert (level.width, level.height) == (7, 4)
    assert level.robot == (1, 1)


def test_outside_spaces_are_not_part_of_the_map():
    level = parse(
        "  ####\n"
        "###  #\n"
        "#@$. #\n"
        "######\n"
    )
    assert level.robot == (2, 1)


def test_crlf_line_ends():
    assert parse("#####\r\n#@$.#\r\n#####\r\n") == parse("#####\n#@$.#\n#####\n")


def test_leading_and_trailing_blank_lines_are_ignored():
    level = parse("\n\n#####\n#@$.#\n#####\n\n  \n")
    assert level.height == 3
    assert level.robot == (1, 1)


# --- errors, each with its line and column ------------------------------------------------------


def test_an_error_names_the_level_line_and_column():
    error = error_of("######\n#@$x.#\n######\n")
    assert (error.level_id, error.line, error.column) == ("test/tier1/t", 2, 4)
    assert str(error) == "test/tier1/t:2:4: unknown character 'x'"


def test_line_numbers_count_comment_lines():
    error = error_of("; title\n######\n; note\n#@$x.#\n######\n")
    assert (error.line, error.column) == (4, 4)


def test_line_numbers_count_leading_blank_lines():
    error = error_of("\n\n######\n#@$x.#\n######\n")
    assert (error.line, error.column) == (4, 4)


def test_a_tab_is_an_unknown_character():
    error = error_of("######\n#@$\t.#\n######\n")
    assert (error.line, error.column) == (2, 4)


def test_no_robot():
    error = error_of("; title\n#####\n# $.#\n#####\n")
    assert (error.line, error.column) == (2, 1)
    assert "no robot" in error.message


def test_two_robots_names_the_second():
    error = error_of("######\n#@$.@#\n######\n")
    assert (error.line, error.column) == (2, 5)
    assert "second robot" in error.message


def test_no_boxes():
    error = error_of("#####\n#@  #\n#####\n")
    assert (error.line, error.column) == (1, 1)
    assert "no box" in error.message


def test_more_boxes_than_goals():
    error = error_of("######\n#@$$.#\n######\n")
    assert (error.line, error.column) == (1, 1)
    assert "2 boxes but 1 goals" in error.message


def test_more_goals_than_boxes():
    error = error_of("######\n#@$..#\n######\n")
    assert (error.line, error.column) == (1, 1)
    assert "1 boxes but 2 goals" in error.message


def test_open_map_through_a_gap_in_the_wall():
    error = error_of("#####\n#@$. \n#####\n")
    assert (error.line, error.column) == (2, 5)
    assert "not closed" in error.message


def test_open_map_through_a_short_row():
    error = error_of("#####\n#@$.#\n##  \n#####\n")
    assert (error.line, error.column) == (3, 4)
    assert "not closed" in error.message


def test_open_map_through_the_top_edge():
    error = error_of("## ##\n#@$.#\n#####\n")
    assert (error.line, error.column) == (1, 3)


@pytest.mark.parametrize("text", ["", "\n\n", "; only a comment\n", "   \n"])
def test_no_map_lines(text):
    error = error_of(text)
    assert (error.line, error.column) == (1, 1)
    assert "no map lines" in error.message


def test_inside_holds_the_robots_area_and_nothing_outside_the_walls():
    level = parse("  ####\n###  #\n#@$. #\n######\n")
    assert level.inside == frozenset({(1, 3), (1, 4), (2, 1), (2, 2), (2, 3), (2, 4)})
    assert level.robot in level.inside and level.boxes <= level.inside
    assert not level.inside & level.walls
