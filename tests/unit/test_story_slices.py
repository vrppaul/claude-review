"""Functional requirement tests for a step as rows of the change: the one rule for which rows a step's lines are.

A story speaks of lines, and the change is rows. A step is every row at its
lines on the side its file is told by, so the lines the change removed come
with the place they were removed from — and what no step tells is found by
the same rule, so nothing the change did can fall between the two.
"""

import pytest
from hypothesis import given, strategies as strategy

from claude_review.domain.models import DiffFile, DiffHunk, DiffLine, FileStatus, Unshown
from claude_review.domain.story import StepLines
from claude_review.services.story_slices import PlacedFile, RowRun
from tests.stories import ROWS, changed_file, changed_in, hunk, lines_of, rows_of, signs_of

FILE = "a.py"
# Lines 12 and 13 replace one line; further down, two lines are removed above the line now numbered 15
REPLACED = changed_file(FILE, hunk(10, 10, "  -++ -- "))
# A line added, a line removed and a line added, with lines the change kept around each
THREE_CHANGES = changed_file(FILE, hunk(10, 10, " + - + "))
# Two changes far apart, which git shows as two hunks
TWO_HUNKS = changed_file(FILE, hunk(10, 10, " + "), hunk(40, 41, " - "))

# What a generated file is made of: rows by their signs, few enough to read when a case fails
SIGNS = " +-"
# The signs of the rows that are lines of the file as it now stands
SIGNS_OF_LINES_THAT_STAND = " +"
MOST_ROWS = 8
MOST_HUNKS = 3
# How many lines the change kept, and does not show, between two generated hunks
GAP = 5
# The furthest line a generated step reaches: past the end of any generated file
FURTHEST_LINE = 60


def lines(first: int, last: int) -> StepLines:
    return StepLines(first=first, last=last)


def piece_at(file: DiffFile, first: int, last: int) -> DiffFile:
    """What a step of these lines shows of a file, as it is shown."""
    reading = PlacedFile(file)
    return reading.piece([reading.rows_at(lines(first, last))])


def shown(file: DiffFile, first: int, last: int) -> list[str]:
    """What a step of these lines shows of a file, row by row."""
    return rows_of(piece_at(file, first, last))


def told_by(file: DiffFile, steps: list[StepLines]) -> list[RowRun]:
    """The rows steps of these lines are, each step's as a run."""
    reading = PlacedFile(file)
    return [reading.rows_at(step) for step in steps]


def left_out(file: DiffFile, *steps: StepLines) -> DiffFile:
    """What steps of these lines leave out of a file, as it is shown."""
    reading = PlacedFile(file)
    return reading.piece(reading.left_out(told_by(file, list(steps))))


def rows_in(runs: list[RowRun]) -> list[int]:
    """Every row of these runs, by where it stands among the file's rows."""
    return [row for run in runs for row in range(run.start, run.stop)]


def lines_in(file: DiffFile, runs: list[RowRun]) -> list[DiffLine]:
    """The rows of a file these runs are, read off the file itself."""
    return [line for run in runs for line in lines_of(file)[run.start : run.stop]]


def lines_shown_by(part: DiffHunk) -> StepLines:
    """The lines of the file as it now stands that a hunk shows, from its first to its last."""
    shown_lines = sum(ROWS[sign].new_lines for sign in signs_of(part.lines))
    return lines(part.new_start, part.new_start + shown_lines - 1)


def test_a_step_is_every_row_at_its_lines_and_a_removed_line_comes_with_the_place_it_was_removed_from() -> None:
    assert shown(REPLACED, 12, 13) == ["-12/", "+/12", "+/13"]


def test_lines_removed_above_a_line_are_told_with_that_line() -> None:
    assert shown(REPLACED, 15, 15) == ["-14/", "-15/", " 16/15"]


def test_a_step_of_a_line_the_change_kept_shows_it_and_holds_no_change() -> None:
    reading = PlacedFile(REPLACED)

    assert shown(REPLACED, 14, 14) == [" 13/14"]
    assert reading.changed_lines([reading.rows_at(lines(14, 14))]) == 0


def test_the_lines_a_step_changed_are_counted_row_by_row() -> None:
    """One line replaced by two and two lines removed: five rows the change added or removed, and no row it kept."""
    reading = PlacedFile(REPLACED)

    assert reading.changed_lines([reading.rows_at(lines(12, 13)), reading.rows_at(lines(15, 15))]) == 5


@pytest.mark.parametrize(("first", "last"), [(30, 39), (1, 9), (15, 12)])
def test_lines_the_change_shows_no_row_at_are_no_rows_and_hold_no_change(first: int, last: int) -> None:
    """Below everything the change shows, above it, or lines that run backwards: a step of them shows nothing."""
    reading = PlacedFile(REPLACED)

    assert piece_at(REPLACED, first, last).hunks == []
    assert reading.changed_lines([reading.rows_at(lines(first, last))]) == 0


def test_lines_removed_at_the_end_of_a_file_go_with_the_last_line_before_them() -> None:
    cut_short = changed_file(FILE, hunk(5, 5, "  --"))

    assert shown(cut_short, 6, 6) == [" 6/6", "-7/", "-8/"]
    assert shown(cut_short, 5, 5) == [" 5/5"]


def test_lines_removed_at_the_end_of_a_hunk_go_with_the_last_line_of_that_hunk_however_near_the_next() -> None:
    """A removed line is told where it was removed from, which no line of another hunk can say."""
    apart = changed_file(FILE, hunk(10, 10, " -"), hunk(40, 39, " + "))

    assert shown(apart, 10, 10) == [" 10/10", "-11/"]
    assert shown(apart, 39, 39) == [" 40/39"]


def test_lines_removed_in_a_hunk_that_shows_no_line_of_the_file_are_told_at_the_line_that_followed_them() -> None:
    apart = changed_file(FILE, hunk(10, 10, "--"), hunk(40, 38, " + "))

    assert shown(apart, 10, 10) == ["-10/", "-11/"]
    assert shown(apart, 38, 38) == [" 40/38"]


@pytest.mark.parametrize("status", [FileStatus.DELETED, FileStatus.MODIFIED])
def test_a_file_the_change_left_no_line_of_is_told_by_the_lines_it_had(status: FileStatus) -> None:
    """Deleted, or emptied and still there: either way its new side has no line to number a step by."""
    gone = changed_file(FILE, hunk(1, 1, "---"), status=status)

    assert shown(gone, 2, 3) == ["-2/", "-3/"]


def test_a_step_that_runs_over_two_hunks_shows_each_as_a_hunk_of_its_own() -> None:
    piece = piece_at(TWO_HUNKS, 11, 41)

    assert [[line.content for line in part.lines] for part in piece.hunks] == [["+/11", " 11/12"], [" 40/41"]]


def test_a_piece_cut_from_inside_a_hunk_starts_where_its_rows_do_on_each_side() -> None:
    mixed = changed_file(FILE, hunk(10, 10, "+ -+"))

    [cut] = piece_at(mixed, 12, 12).hunks

    assert [line.content for line in cut.lines] == ["-11/", "+/12"]
    assert (cut.old_start, cut.new_start) == (11, 12)


def test_a_side_with_no_row_in_a_piece_starts_where_its_first_line_would_be() -> None:
    mixed = changed_file(FILE, hunk(10, 10, "+ -+"))

    [cut] = piece_at(mixed, 10, 10).hunks

    assert [line.content for line in cut.lines] == ["+/10"]
    assert (cut.old_start, cut.new_start) == (10, 10)


def test_a_piece_of_lines_added_at_the_end_of_a_hunk_starts_past_the_last_line_the_hunk_shows_of_the_file_as_it_was() -> (
    None
):
    grown = changed_file(FILE, hunk(10, 10, " ++"))

    [cut] = piece_at(grown, 12, 12).hunks

    assert [line.content for line in cut.lines] == ["+/12"]
    assert (cut.old_start, cut.new_start) == (11, 12)


def test_a_piece_is_the_file_it_was_cut_from_in_everything_but_its_rows() -> None:
    """Where it was, what became of it, whether it may be run: said of the file, and so of every piece of it."""
    made_runnable = DiffFile(
        path="new.sh",
        old_path="old.sh",
        status=FileStatus.RENAMED,
        hunks=[hunk(10, 10, " + ")],
        old_mode="100644",
        new_mode="100755",
    )

    piece = piece_at(made_runnable, 11, 11)

    assert piece.model_dump(exclude={"hunks"}) == made_runnable.model_dump(exclude={"hunks"})
    assert rows_of(piece) == ["+/11"]


def test_a_piece_of_a_file_some_of_which_is_not_shown_says_so_as_the_file_does() -> None:
    """A picture that became a link: the link is one line, and what the picture held is not text."""
    became_a_link = DiffFile(
        path="logo",
        status=FileStatus.MODIFIED,
        hunks=[hunk(1, 1, "+")],
        unshown=Unshown.BINARY,
        old_mode="100644",
        new_mode="120000",
    )

    assert piece_at(became_a_link, 1, 1).unshown == Unshown.BINARY


def test_a_piece_carries_no_header_of_the_whole_hunk() -> None:
    headed = hunk(10, 10, " + ").model_copy(update={"header": "@@ -10,2 +10,3 @@ def whole():"})

    piece = piece_at(changed_file(FILE, headed), 11, 11)

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


def test_a_step_that_shows_nothing_hides_no_step_told_before_it() -> None:
    """A step of no rows stands where the step below it starts; told after that step, it leaves it told all the same."""
    one_line_removed = changed_file(FILE, hunk(6, 6, "-"))

    assert left_out(one_line_removed, lines(3, 6), lines(1, 1)).hunks == []


def test_a_file_told_whole_leaves_nothing_out() -> None:
    assert left_out(THREE_CHANGES, lines(10, 15)).hunks == []


def test_a_file_no_step_tells_is_left_out_whole() -> None:
    assert rows_of(left_out(TWO_HUNKS)) == rows_of(TWO_HUNKS)


def test_a_file_the_change_shows_no_line_of_has_none_to_tell() -> None:
    assert not PlacedFile(changed_file("logo.png")).shows_lines
    assert PlacedFile(REPLACED).shows_lines


def numbered_as_git_numbers(signs_of_hunks: list[str]) -> DiffFile:
    """A file whose hunks hold rows of these signs, numbered as git numbers them, with lines kept between the hunks."""
    hunks = []
    old_number = new_number = 1
    for signs in signs_of_hunks:
        old_number += GAP
        new_number += GAP
        hunks.append(hunk(old_number, new_number, signs))
        old_number += sum(ROWS[sign].old_lines for sign in signs)
        new_number += sum(ROWS[sign].new_lines for sign in signs)
    return changed_file(FILE, *hunks)


@strategy.composite
def changed_files(draw: strategy.DrawFn) -> DiffFile:
    """A file of a few hunks, each a few rows of any kind."""
    return numbered_as_git_numbers(
        draw(
            strategy.lists(
                strategy.text(alphabet=SIGNS, min_size=1, max_size=MOST_ROWS), min_size=1, max_size=MOST_HUNKS
            )
        )
    )


@strategy.composite
def hunks_that_show_a_line(draw: strategy.DrawFn) -> str:
    """The signs of a hunk made around a line of the file as it now stands, with rows of any kind either side of it."""
    either_side = strategy.text(alphabet=SIGNS, max_size=MOST_ROWS // 2)
    return draw(either_side) + draw(strategy.sampled_from(SIGNS_OF_LINES_THAT_STAND)) + draw(either_side)


@strategy.composite
def files_whose_hunks_each_show_a_line(draw: strategy.DrawFn) -> DiffFile:
    """A file of a few hunks, each showing at least one line of the file as it now stands."""
    return numbered_as_git_numbers(draw(strategy.lists(hunks_that_show_a_line(), min_size=1, max_size=MOST_HUNKS)))


@strategy.composite
def steps_apart(draw: strategy.DrawFn) -> list[StepLines]:
    """Steps of one file that share no line, as a story's must."""
    edges = sorted(
        draw(strategy.lists(strategy.integers(min_value=1, max_value=FURTHEST_LINE), unique=True, max_size=8))
    )
    return [lines(first, following - 1) for first, following in zip(edges[::2], edges[1::2], strict=False)]


@strategy.composite
def steps_one_after_another(draw: strategy.DrawFn) -> list[StepLines]:
    """Two steps of one file, the second starting at the line after the first one's last."""
    first, middle, last = sorted(
        draw(strategy.lists(strategy.integers(min_value=1, max_value=FURTHEST_LINE), min_size=3, max_size=3))
    )
    return [lines(first, middle), lines(middle + 1, last + 1)]


@given(file=changed_files(), steps=steps_apart())
def test_no_row_is_told_by_two_steps_or_both_told_and_left_out(file: DiffFile, steps: list[StepLines]) -> None:
    told = told_by(file, steps)
    rows = [*rows_in(told), *rows_in(PlacedFile(file).left_out(told))]

    assert len(set(rows)) == len(rows)


@given(file=changed_files(), steps=steps_apart())
def test_every_row_the_change_added_or_removed_is_told_or_left_out(file: DiffFile, steps: list[StepLines]) -> None:
    """No row is counted twice, so counting them all means each is somewhere."""
    told = told_by(file, steps)
    left = PlacedFile(file).left_out(told)

    assert changed_in(lines_in(file, told)) + changed_in(lines_in(file, left)) == changed_in(lines_of(file))


@given(file=changed_files(), steps=steps_apart())
def test_the_rows_a_step_changed_are_counted_as_the_file_itself_shows_them(
    file: DiffFile, steps: list[StepLines]
) -> None:
    reading = PlacedFile(file)
    told = told_by(file, steps)

    assert [reading.changed_lines([run]) for run in told] == [changed_in(lines_in(file, [run])) for run in told]


@given(file=changed_files(), steps=steps_apart())
def test_every_run_of_rows_left_out_holds_a_change(file: DiffFile, steps: list[StepLines]) -> None:
    left = PlacedFile(file).left_out(told_by(file, steps))

    assert all(changed_in(lines_in(file, [run])) > 0 for run in left)


@given(file=changed_files(), steps=steps_apart(), data=strategy.data())
def test_steps_leave_out_the_same_rows_in_whatever_order_the_story_tells_them(
    file: DiffFile, steps: list[StepLines], data: strategy.DataObject
) -> None:
    """A story tells its steps in the order they are best read, which is seldom the order of the file's lines."""
    reading = PlacedFile(file)
    as_told = data.draw(strategy.permutations(steps))

    assert reading.left_out(told_by(file, as_told)) == reading.left_out(told_by(file, steps))


@given(file=changed_files(), steps=steps_apart())
def test_every_hunk_of_a_piece_numbers_its_rows_from_where_it_starts_as_the_file_numbers_them(
    file: DiffFile, steps: list[StepLines]
) -> None:
    """Written again from its own starts and signs, a piece's hunk is the very rows it was cut from."""
    reading = PlacedFile(file)
    pieces = [part for step in steps for part in reading.piece([reading.rows_at(step)]).hunks]

    assert pieces == [hunk(part.old_start, part.new_start, signs_of(part.lines)) for part in pieces]


@given(file=changed_files(), steps=steps_one_after_another())
def test_two_steps_one_after_another_tell_together_what_one_step_of_all_their_lines_tells(
    file: DiffFile, steps: list[StepLines]
) -> None:
    """No row falls between two steps that follow one another, and none is told by both."""
    [upper, lower] = steps
    whole = lines(upper.first, lower.last)

    assert rows_in(told_by(file, steps)) == rows_in(told_by(file, [whole]))


@given(file=files_whose_hunks_each_show_a_line())
def test_the_lines_a_hunk_shows_tell_that_hunk_whole_and_no_row_of_another(file: DiffFile) -> None:
    """A removed line is told with a line of its own hunk: where it was removed from, which no other hunk can say."""
    pieces = [piece_at(file, shown_lines.first, shown_lines.last) for shown_lines in map(lines_shown_by, file.hunks)]

    assert [rows_of(piece) for piece in pieces] == [[line.content for line in part.lines] for part in file.hunks]
