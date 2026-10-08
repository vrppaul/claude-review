"""Functional requirement tests for anchors: what a thread hangs on.

A thread is written about lines, not about numbers. Work moves the lines,
so the review has to find them again after every round, say plainly when
they are gone, and name the place the same way everywhere it is told.
"""

import re

import pytest

from claude_review.domain.exceptions import AnchorLinesNotShownError, UnknownAnchorFileError
from claude_review.domain.models import DiffFile, DiffHunk, FileStatus, LineAnchor, LineSide
from claude_review.services.anchor_service import AnchorService
from tests.helpers import added_line, context_line, diff_file, line_anchor, removed_line

FILE = "a.py"
RUN = "def run():"
RETURN = "    return 1"
# A line that stands in many places in a file
CLOSING_BRACE = "}"


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


def test_a_thread_follows_its_line_when_the_line_moves() -> None:
    followed = AnchorService(MOVED_DOWN).follow(line_anchor(FILE, 2, quote=[RUN]))

    assert (followed.start_line, followed.end_line, followed.outdated) == (3, 3, False)


def test_a_range_moves_as_one() -> None:
    followed = AnchorService(MOVED_DOWN).follow(line_anchor(FILE, 2, 3, quote=[RUN, RETURN]))

    assert (followed.start_line, followed.end_line) == (3, 4)


def test_a_thread_whose_lines_are_gone_says_so_and_stays_put() -> None:
    gone = AnchorService(MOVED_DOWN).follow(line_anchor(FILE, 2, quote=["def walk():"]))

    assert gone.outdated is True
    assert (gone.start_line, gone.end_line) == (2, 2)
    assert gone.quote == ["def walk():"]


def test_a_thread_whose_file_left_the_diff_is_outdated() -> None:
    gone = AnchorService([]).follow(line_anchor(FILE, 2, quote=[RUN]))

    assert gone.outdated is True


def test_a_thread_that_never_kept_its_lines_is_left_where_it_is() -> None:
    kept = AnchorService(MOVED_DOWN).follow(line_anchor(FILE, 2))

    assert (kept.start_line, kept.outdated) == (2, False)


def test_lines_that_come_back_take_the_outdated_mark_off() -> None:
    outdated = line_anchor(FILE, 7, quote=[RUN], outdated=True)

    followed = AnchorService(MOVED_DOWN).follow(outdated)

    assert (followed.start_line, followed.outdated) == (3, False)


def test_a_thread_on_a_removed_line_is_looked_for_among_removed_lines() -> None:
    files = [diff_file(FILE, [context_line(1, 1, "import os"), removed_line(2, RUN), added_line(2, RUN)])]

    followed = AnchorService(files).follow(line_anchor(FILE, 5, side=LineSide.OLD, quote=[RUN]))

    assert (followed.side, followed.start_line, followed.outdated) == (LineSide.OLD, 2, False)


def test_quoting_reads_the_lines_off_the_diff() -> None:
    quoted = AnchorService(MOVED_DOWN).quote(line_anchor(FILE, 3, 4))

    assert quoted.quote == [RUN, RETURN]


def test_quoting_a_file_the_review_does_not_hold_names_what_it_does_hold() -> None:
    with pytest.raises(UnknownAnchorFileError, match=re.escape("elsewhere.py is not in this review. It has: a.py")):
        AnchorService(MOVED_DOWN).quote(line_anchor("elsewhere.py", 1))


def test_quoting_lines_the_diff_does_not_show_names_them() -> None:
    with pytest.raises(AnchorLinesNotShownError, match=re.escape("a.py does not show new lines 5-6")):
        AnchorService(MOVED_DOWN).quote(line_anchor(FILE, 4, 6))


def test_quoting_a_removed_line_the_diff_does_not_show_says_removed() -> None:
    with pytest.raises(AnchorLinesNotShownError, match=re.escape("a.py does not show removed line 9")):
        AnchorService(MOVED_DOWN).quote(line_anchor(FILE, 9, side=LineSide.OLD))


@pytest.mark.parametrize(
    ("anchor", "said"),
    [
        (line_anchor(FILE, 42), "`a.py`:42"),
        (line_anchor(FILE, 42, 47), "`a.py`:42-47"),
        (line_anchor(FILE, 42, side=LineSide.OLD), "`a.py`:42 (removed)"),
    ],
)
def test_a_place_is_named_the_way_the_review_names_it(anchor: LineAnchor, said: str) -> None:
    assert anchor.where() == said


def test_a_short_quote_found_in_several_places_follows_the_nearest() -> None:
    """A closing brace stands everywhere; the one that moved least is the one meant."""
    files = _braces_at((3, 10), line_count=11)

    followed = AnchorService(files).follow(line_anchor(FILE, 9, quote=[CLOSING_BRACE]))

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

    followed = AnchorService(files).follow(line_anchor(FILE, 1, 2, quote=["end", "start"]))

    assert followed.outdated
    assert (followed.start_line, followed.end_line) == (1, 2)


def test_a_range_with_one_line_rewritten_is_outdated() -> None:
    files = [diff_file(FILE, [context_line(1, 1, RUN), added_line(2, "    return 2")])]

    followed = AnchorService(files).follow(line_anchor(FILE, 1, 2, quote=[RUN, RETURN]))

    assert followed.outdated


def test_a_quote_as_near_to_two_places_follows_the_earlier() -> None:
    """Nothing tells the two apart, so the choice is at least the same every time."""
    files = _braces_at((3, 7), line_count=9)

    followed = AnchorService(files).follow(line_anchor(FILE, 5, quote=[CLOSING_BRACE]))

    assert followed.start_line == 3
