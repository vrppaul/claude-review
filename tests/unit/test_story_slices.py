"""Functional requirement tests for a step as rows of the change: the one rule for which rows a step's lines are.

A story speaks of lines, and the change is rows. A step is every row at its
lines on the side its file is told by, so the lines the change removed come
with the place they were removed from — and what no step tells is found by
the same rule, so nothing the change did can fall between the two.
"""

import pytest
from hypothesis import given, strategies as strategy

from claude_review.domain.models import DiffFile, FileStatus, LineType
from claude_review.domain.story import StepLines
from claude_review.services.story_slices import HunkRows, ToldFile
from tests.stories import changed_file, hunk, rows_of

FILE = "a.py"
# Lines 12 and 13 replace one line; further down, two lines are removed above the line now numbered 15
REPLACED = changed_file(FILE, hunk(10, 10, "  -++ -- "))
# A line added, a line removed and a line added, with lines the change kept around each
THREE_CHANGES = changed_file(FILE, hunk(10, 10, " + - + "))
# Two changes far apart, which git shows as two hunks
TWO_HUNKS = changed_file(FILE, hunk(10, 10, " + "), hunk(40, 41, " - "))

# What a generated file is made of: rows by their signs, few enough to read when a case fails
SIGNS = " +-"
MOST_ROWS = 8
MOST_HUNKS = 3
# How many lines the change kept, and does not show, between two generated hunks
GAP = 5
# The furthest line a generated step reaches: past the end of any generated file
FURTHEST_LINE = 60


def lines(first: int, last: int) -> StepLines:
    return StepLines(first=first, last=last)


def shown(file: DiffFile, first: int, last: int) -> list[str]:
    """What a step of these lines shows of a file, row by row."""
    reading = ToldFile(file)
    return rows_of(reading.piece(reading.rows_at(lines(first, last))))


def left_out(file: DiffFile, *steps: StepLines) -> DiffFile:
    """What steps of these lines leave out of a file, as it is shown."""
    reading = ToldFile(file)
    return reading.piece(reading.left_out([run for step in steps for run in reading.rows_at(step)]))


def rows_in(runs: list[HunkRows]) -> list[tuple[int, int]]:
    """Every row of these runs, by its hunk and its place among the hunk's rows."""
    return [(run.hunk, row) for run in runs for row in range(run.start, run.stop)]


def test_a_step_is_every_row_at_its_lines_and_a_removed_line_comes_with_the_place_it_was_removed_from() -> None:
    assert shown(REPLACED, 12, 13) == ["-12/", "+/12", "+/13"]


def test_lines_removed_above_a_line_are_told_with_that_line() -> None:
    assert shown(REPLACED, 15, 15) == ["-14/", "-15/", " 16/15"]


def test_a_step_of_a_line_the_change_kept_shows_it_and_holds_no_change() -> None:
    reading = ToldFile(REPLACED)

    assert shown(REPLACED, 14, 14) == [" 13/14"]
    assert reading.changed_lines(reading.rows_at(lines(14, 14))) == 0


def test_lines_removed_at_the_end_of_a_file_go_with_the_last_line_before_them() -> None:
    cut_short = changed_file(FILE, hunk(5, 5, "  --"))

    assert shown(cut_short, 6, 6) == [" 6/6", "-7/", "-8/"]
    assert shown(cut_short, 5, 5) == [" 5/5"]


@pytest.mark.parametrize("status", [FileStatus.DELETED, FileStatus.MODIFIED])
def test_a_file_the_change_left_no_line_of_is_told_by_the_lines_it_had(status: FileStatus) -> None:
    """Deleted, or emptied and still there: either way its new side has no line to number a step by."""
    gone = changed_file(FILE, hunk(1, 0, "---"), status=status)

    assert shown(gone, 2, 3) == ["-2/", "-3/"]


def test_a_step_that_runs_over_two_hunks_shows_each_as_a_hunk_of_its_own() -> None:
    reading = ToldFile(TWO_HUNKS)

    piece = reading.piece(reading.rows_at(lines(11, 41)))

    assert [[line.content for line in part.lines] for part in piece.hunks] == [["+/11", " 11/12"], [" 40/41"]]


def test_a_piece_cut_from_inside_a_hunk_starts_where_its_rows_do_on_each_side() -> None:
    mixed = changed_file(FILE, hunk(10, 10, "+ -+"))
    reading = ToldFile(mixed)

    [cut] = reading.piece(reading.rows_at(lines(12, 12))).hunks

    assert rows_of(reading.piece(reading.rows_at(lines(12, 12)))) == ["-11/", "+/12"]
    assert (cut.old_start, cut.new_start) == (11, 12)


def test_a_side_with_no_row_in_a_piece_starts_where_its_first_line_would_be() -> None:
    mixed = changed_file(FILE, hunk(10, 10, "+ -+"))
    reading = ToldFile(mixed)

    [cut] = reading.piece(reading.rows_at(lines(10, 10))).hunks

    assert [line.content for line in cut.lines] == ["+/10"]
    assert (cut.old_start, cut.new_start) == (10, 10)


def test_a_piece_is_still_the_file_it_was_cut_from_and_carries_no_header_of_the_whole_hunk() -> None:
    headed = hunk(10, 10, " + ").model_copy(update={"header": "@@ -10,2 +10,3 @@ def whole():"})
    moved = DiffFile(path="new.py", old_path="old.py", status=FileStatus.RENAMED, hunks=[headed])
    reading = ToldFile(moved)

    piece = reading.piece(reading.rows_at(lines(11, 11)))

    assert (piece.path, piece.old_path, piece.status) == ("new.py", "old.py", FileStatus.RENAMED)
    assert [part.header for part in piece.hunks] == [""]


def test_what_no_step_tells_is_left_out_as_the_runs_of_rows_that_hold_a_change() -> None:
    left = left_out(THREE_CHANGES, lines(13, 13))

    assert [[line.content for line in part.lines] for part in left.hunks] == [
        [" 10/10", "+/11", " 11/12"],
        ["+/14", " 14/15"],
    ]


def test_rows_the_change_only_kept_are_nobodys_when_no_change_stands_among_them() -> None:
    left = left_out(THREE_CHANGES, lines(11, 11), lines(14, 15))

    assert [[line.content for line in part.lines] for part in left.hunks] == [[" 11/12", "-12/", " 13/13"]]


def test_a_file_told_whole_leaves_nothing_out() -> None:
    assert left_out(THREE_CHANGES, lines(10, 15)).hunks == []


def test_a_file_no_step_tells_is_left_out_whole() -> None:
    assert rows_of(left_out(TWO_HUNKS)) == rows_of(TWO_HUNKS)


def test_a_file_the_change_shows_no_line_of_has_none_to_tell() -> None:
    assert not ToldFile(changed_file("logo.png")).shows_lines
    assert ToldFile(REPLACED).shows_lines


@strategy.composite
def changed_files(draw: strategy.DrawFn) -> DiffFile:
    """A file of a few hunks, each a few rows of any kind, numbered as git numbers them, with lines kept between."""
    hunks = []
    old_number = new_number = 1
    for signs in draw(
        strategy.lists(strategy.text(alphabet=SIGNS, min_size=1, max_size=MOST_ROWS), min_size=1, max_size=MOST_HUNKS)
    ):
        old_number += GAP
        new_number += GAP
        hunks.append(hunk(old_number, new_number, signs))
        old_number += sum(1 for sign in signs if sign != "+")
        new_number += sum(1 for sign in signs if sign != "-")
    return changed_file(FILE, *hunks)


@strategy.composite
def steps_apart(draw: strategy.DrawFn) -> list[StepLines]:
    """Steps of one file that share no line, as a story's must."""
    edges = sorted(
        draw(strategy.lists(strategy.integers(min_value=1, max_value=FURTHEST_LINE), unique=True, max_size=8))
    )
    return [lines(first, following - 1) for first, following in zip(edges[::2], edges[1::2], strict=False)]


@given(file=changed_files(), steps=steps_apart())
def test_every_row_the_change_added_or_removed_is_told_by_one_step_or_left_out_and_never_both(
    file: DiffFile, steps: list[StepLines]
) -> None:
    reading = ToldFile(file)
    told = [run for step in steps for run in reading.rows_at(step)]
    left = reading.left_out(told)
    changed = {
        (part, row)
        for part, shown_hunk in enumerate(file.hunks)
        for row, line in enumerate(shown_hunk.lines)
        if line.kind != LineType.CONTEXT
    }

    assert len(set(rows_in(told)) | set(rows_in(left))) == len(rows_in(told)) + len(rows_in(left))
    assert changed <= set(rows_in(told)) | set(rows_in(left))
    assert all(reading.changed_lines([run]) > 0 for run in left)


@given(file=changed_files(), steps=steps_apart())
def test_every_hunk_of_a_piece_starts_at_the_numbers_its_first_rows_have(
    file: DiffFile, steps: list[StepLines]
) -> None:
    reading = ToldFile(file)

    for step in steps:
        for part in reading.piece(reading.rows_at(step)).hunks:
            old_numbers = [line.old_number for line in part.lines if line.old_number is not None]
            new_numbers = [line.new_number for line in part.lines if line.new_number is not None]
            assert not old_numbers or part.old_start == old_numbers[0]
            assert not new_numbers or part.new_start == new_numbers[0]
