"""Functional requirement tests for anchors: what a thread hangs on.

A thread is written about lines, not about numbers. Work moves the lines,
so the review has to find them again after every round, and say plainly
when they are gone.
"""

import re

import pytest
from hypothesis import given, strategies as strategy

from claude_review.domain.exceptions import AnchorLinesNotShownError, AnchorTooLongError, UnknownAnchorFileError
from claude_review.domain.models import MAX_QUOTE_LINES, DiffFile, DiffHunk, FileStatus, LineSide
from claude_review.services.anchor_service import AnchorService
from tests.helpers import added_line, context_line, diff_file, line_anchor, removed_line

FILE = "a.py"
RUN = "def run():"
RETURN = "    return 1"
# A line that stands in many places in a file
CLOSING_BRACE = "}"
# Few kinds of line, so the same run stands in several places, as braces and blank lines do
LINE_KINDS = [CLOSING_BRACE, RUN, RETURN]
# Long enough for runs to repeat and to move, short enough to read when a case fails
LONGEST_FILE = 30
# The longest run a generated thread quotes
LONGEST_QUOTE = 4


def _braces_at(brace_lines: tuple[int, ...], line_count: int) -> list[DiffFile]:
    """A file of numbered lines, with a closing brace standing on some of them."""
    return [
        diff_file(
            FILE,
            [
                context_line(
                    line_number, line_number, CLOSING_BRACE if line_number in brace_lines else f"line {line_number}"
                )
                for line_number in range(1, line_count + 1)
            ],
        )
    ]


# A line was added above `run`, so everything below it moved down by one
MOVED_DOWN = [
    diff_file(
        FILE,
        [
            context_line(1, 1, "import os"),
            added_line(2, "import sys"),
            context_line(2, 3, RUN),
            context_line(3, 4, RETURN),
        ],
    )
]


# Lines 4 to 8 of the old file were removed between two that stayed
REMOVED_RUN = [
    diff_file(
        FILE,
        [
            context_line(3, 3, "before"),
            *(removed_line(number, f"removed {number}") for number in range(4, 9)),
            context_line(9, 4, "after"),
        ],
    )
]


def test_an_excerpt_is_what_the_anchor_is_on_and_two_lines_either_side() -> None:
    excerpt = AnchorService.of_diff(_braces_at((), line_count=11)).excerpt(line_anchor(FILE, 5, 6))

    assert excerpt == ["line 3", "line 4", "line 5", "line 6", "line 7", "line 8"]


def test_an_excerpt_of_removed_lines_reads_the_file_as_it_was() -> None:
    excerpt = AnchorService.of_diff(REMOVED_RUN).excerpt(line_anchor(FILE, 6, side=LineSide.OLD))

    assert excerpt == ["removed 4", "removed 5", "removed 6", "removed 7", "removed 8"]


def test_an_excerpt_of_a_file_the_review_does_not_hold_is_empty() -> None:
    assert AnchorService.of_diff(MOVED_DOWN).excerpt(line_anchor("gone.py", 1)) == []


def test_a_thread_follows_its_line_when_the_line_moves() -> None:
    followed = AnchorService.of_diff(MOVED_DOWN).follow(line_anchor(FILE, 2, quote=[RUN]))

    assert (followed.start_line, followed.end_line, followed.outdated) == (3, 3, False)


def test_a_range_moves_as_one() -> None:
    followed = AnchorService.of_diff(MOVED_DOWN).follow(line_anchor(FILE, 2, 3, quote=[RUN, RETURN]))

    assert (followed.start_line, followed.end_line) == (3, 4)


def test_a_thread_whose_lines_are_gone_says_so_and_stays_put() -> None:
    gone = AnchorService.of_diff(MOVED_DOWN).follow(line_anchor(FILE, 2, quote=["def walk():"]))

    assert gone.outdated is True
    assert (gone.start_line, gone.end_line) == (2, 2)
    assert gone.quote == ["def walk():"]


def test_a_thread_whose_file_left_the_diff_is_outdated() -> None:
    gone = AnchorService.of_diff([]).follow(line_anchor(FILE, 2, quote=[RUN]))

    assert gone.outdated is True


def test_a_thread_that_never_kept_its_lines_is_left_where_it_is() -> None:
    kept = AnchorService.of_diff(MOVED_DOWN).follow(line_anchor(FILE, 2))

    assert (kept.start_line, kept.outdated) == (2, False)


def test_lines_that_come_back_take_the_outdated_mark_off() -> None:
    outdated = line_anchor(FILE, 7, quote=[RUN], outdated=True)

    followed = AnchorService.of_diff(MOVED_DOWN).follow(outdated)

    assert (followed.start_line, followed.outdated) == (3, False)


def test_a_thread_on_a_removed_line_is_looked_for_among_removed_lines() -> None:
    files = [diff_file(FILE, [context_line(1, 1, "import os"), removed_line(2, RUN), added_line(2, RUN)])]

    followed = AnchorService.of_diff(files).follow(line_anchor(FILE, 5, side=LineSide.OLD, quote=[RUN]))

    assert (followed.side, followed.start_line, followed.outdated) == (LineSide.OLD, 2, False)


def test_quoting_reads_the_lines_off_the_diff() -> None:
    quoted = AnchorService.of_diff(MOVED_DOWN).quote(line_anchor(FILE, 3, 4))

    assert quoted.quote == [RUN, RETURN]


def test_lines_more_than_a_quote_keeps_are_refused() -> None:
    """A thread the review cannot keep its quote of could never be sent in a round."""
    longest = MAX_QUOTE_LINES + 1
    every_line_shown = _braces_at((), longest)

    with pytest.raises(AnchorTooLongError, match=str(MAX_QUOTE_LINES)):
        AnchorService.of_diff(every_line_shown).quote(line_anchor(FILE, 1, longest))


def test_quoting_a_file_the_review_does_not_hold_names_what_it_does_hold() -> None:
    with pytest.raises(UnknownAnchorFileError, match=re.escape("elsewhere.py is not in this review. It has: a.py")):
        AnchorService.of_diff(MOVED_DOWN).quote(line_anchor("elsewhere.py", 1))


def test_quoting_lines_the_diff_does_not_show_names_them() -> None:
    with pytest.raises(AnchorLinesNotShownError, match=re.escape("a.py does not show new lines 5-6")):
        AnchorService.of_diff(MOVED_DOWN).quote(line_anchor(FILE, 4, 6))


def test_quoting_a_removed_line_the_diff_does_not_show_says_removed() -> None:
    with pytest.raises(AnchorLinesNotShownError, match=re.escape("a.py does not show removed line 9")):
        AnchorService.of_diff(MOVED_DOWN).quote(line_anchor(FILE, 9, side=LineSide.OLD))


def test_a_short_quote_found_in_several_places_follows_the_nearest() -> None:
    """A closing brace stands everywhere; the one that moved least is the one meant."""
    files = _braces_at((3, 10), line_count=11)

    followed = AnchorService.of_diff(files).follow(line_anchor(FILE, 9, quote=[CLOSING_BRACE]))

    assert followed.start_line == 10


def test_a_range_is_followed_only_where_its_lines_stand_together() -> None:
    """Two hunks sit side by side in the diff, not in the file: the end of one
    and the start of the next are forty lines apart."""
    hunks = [
        DiffHunk(
            header="@@ -9,2 +9,2 @@",
            old_start=9,
            new_start=9,
            lines=[context_line(9, 9, "a"), context_line(10, 10, "end")],
        ),
        DiffHunk(
            header="@@ -50,2 +50,2 @@",
            old_start=50,
            new_start=50,
            lines=[context_line(50, 50, "start"), context_line(51, 51, "b")],
        ),
    ]
    files = [DiffFile(path=FILE, status=FileStatus.MODIFIED, hunks=hunks)]

    followed = AnchorService.of_diff(files).follow(line_anchor(FILE, 1, 2, quote=["end", "start"]))

    assert followed.outdated
    assert (followed.start_line, followed.end_line) == (1, 2)


def test_a_range_with_one_line_rewritten_is_outdated() -> None:
    files = [diff_file(FILE, [context_line(1, 1, RUN), added_line(2, "    return 2")])]

    followed = AnchorService.of_diff(files).follow(line_anchor(FILE, 1, 2, quote=[RUN, RETURN]))

    assert followed.outdated


def test_a_quote_as_near_to_two_places_follows_the_earlier() -> None:
    """Nothing tells the two apart, so the choice is at least the same every time."""
    files = _braces_at((3, 7), line_count=9)

    followed = AnchorService.of_diff(files).follow(line_anchor(FILE, 5, quote=[CLOSING_BRACE]))

    assert followed.start_line == 3


def _file_of(contents: list[str]) -> list[DiffFile]:
    """A file of these lines, none of them changed."""
    return [diff_file(FILE, [context_line(number, number, content) for number, content in enumerate(contents, 1)])]


@given(
    contents=strategy.lists(strategy.sampled_from(LINE_KINDS), min_size=1, max_size=LONGEST_FILE),
    quote=strategy.lists(strategy.sampled_from(LINE_KINDS), min_size=1, max_size=LONGEST_QUOTE),
    claimed_start=strategy.integers(min_value=1, max_value=LONGEST_FILE),
)
def test_following_again_leaves_a_thread_where_following_put_it(
    contents: list[str], quote: list[str], claimed_start: int
) -> None:
    """A page that lost track of a retake follows its threads again: nothing may move twice."""
    anchors = AnchorService.of_diff(_file_of(contents))
    claimed = line_anchor(FILE, claimed_start, claimed_start + len(quote) - 1, quote=quote)

    followed = anchors.follow(claimed)

    assert anchors.follow(followed) == followed


@given(
    contents=strategy.lists(strategy.sampled_from(LINE_KINDS), min_size=1, max_size=LONGEST_FILE), data=strategy.data()
)
def test_a_thread_on_lines_that_did_not_move_stays_on_them(contents: list[str], data: strategy.DataObject) -> None:
    start = data.draw(strategy.integers(min_value=1, max_value=len(contents)))
    end = data.draw(strategy.integers(min_value=start, max_value=min(len(contents), start + LONGEST_QUOTE - 1)))
    on_its_lines = line_anchor(FILE, start, end, quote=contents[start - 1 : end])

    followed = AnchorService.of_diff(_file_of(contents)).follow(on_its_lines)

    assert followed == on_its_lines
