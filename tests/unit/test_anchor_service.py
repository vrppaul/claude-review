"""Functional requirement tests for anchors: what a thread hangs on.

A thread is written about lines, not about numbers. Work moves the lines,
so the review has to find them again after every round, say plainly when
they are gone, and name the place the same way everywhere it is told.
"""

import re

import pytest

from claude_review.domain.exceptions import AnchorLinesNotShownError, UnknownAnchorFileError
from claude_review.domain.models import DiffFile, DiffHunk, DiffLine, FileStatus, LineAnchor, LineSide, LineType
from claude_review.services.anchor_service import AnchorService

RUN = "def run():"
RETURN = "    return 1"


def _file(path: str, lines: list[DiffLine]) -> DiffFile:
    return DiffFile(
        path=path,
        status=FileStatus.MODIFIED,
        hunks=[DiffHunk(header="@@ -1 +1 @@", old_start=1, new_start=1, lines=lines)],
    )


def _context(old_no: int, new_no: int, content: str) -> DiffLine:
    return DiffLine(type=LineType.CONTEXT, old_no=old_no, new_no=new_no, content=content)


def _added(new_no: int, content: str) -> DiffLine:
    return DiffLine(type=LineType.ADD, new_no=new_no, content=content)


def _removed(old_no: int, content: str) -> DiffLine:
    return DiffLine(type=LineType.DELETE, old_no=old_no, content=content)


def _anchor(quote: list[str], start: int, end: int, side: LineSide = LineSide.NEW) -> LineAnchor:
    return LineAnchor(file="a.py", side=side, start_line=start, end_line=end, quote=quote)


# A line was added above `run`, so everything below it moved down by one
MOVED_DOWN = [
    _file(
        "a.py",
        [
            _context(1, 1, "import os"),
            _added(2, "import sys"),
            _context(2, 3, RUN),
            _context(3, 4, RETURN),
        ],
    )
]


def test_a_thread_follows_its_line_when_the_line_moves() -> None:
    followed = AnchorService(MOVED_DOWN).follow(_anchor([RUN], 2, 2))

    assert (followed.start_line, followed.end_line, followed.outdated) == (3, 3, False)


def test_a_range_moves_as_one() -> None:
    followed = AnchorService(MOVED_DOWN).follow(_anchor([RUN, RETURN], 2, 3))

    assert (followed.start_line, followed.end_line) == (3, 4)


def test_a_thread_whose_lines_are_gone_says_so_and_stays_put() -> None:
    gone = AnchorService(MOVED_DOWN).follow(_anchor(["def walk():"], 2, 2))

    assert gone.outdated is True
    assert (gone.start_line, gone.end_line) == (2, 2)
    assert gone.quote == ["def walk():"]


def test_a_thread_whose_file_left_the_diff_is_outdated() -> None:
    gone = AnchorService([]).follow(_anchor([RUN], 2, 2))

    assert gone.outdated is True


def test_a_thread_that_never_kept_its_lines_is_left_where_it_is() -> None:
    kept = AnchorService(MOVED_DOWN).follow(_anchor([], 2, 2))

    assert (kept.start_line, kept.outdated) == (2, False)


def test_lines_that_come_back_take_the_outdated_mark_off() -> None:
    outdated = _anchor([RUN], 7, 7).model_copy(update={"outdated": True})

    followed = AnchorService(MOVED_DOWN).follow(outdated)

    assert (followed.start_line, followed.outdated) == (3, False)


def test_a_thread_on_a_removed_line_is_looked_for_among_removed_lines() -> None:
    files = [_file("a.py", [_context(1, 1, "import os"), _removed(2, RUN), _added(2, RUN)])]

    followed = AnchorService(files).follow(_anchor([RUN], 5, 5, side=LineSide.OLD))

    assert (followed.side, followed.start_line, followed.outdated) == (LineSide.OLD, 2, False)


def test_quoting_reads_the_lines_off_the_diff() -> None:
    quoted = AnchorService(MOVED_DOWN).quote(_anchor([], 3, 4))

    assert quoted.quote == [RUN, RETURN]


def test_quoting_a_file_the_review_does_not_hold_names_what_it_does_hold() -> None:
    with pytest.raises(UnknownAnchorFileError, match=re.escape("elsewhere.py is not in this review. It has: a.py")):
        AnchorService(MOVED_DOWN).quote(LineAnchor(file="elsewhere.py", side=LineSide.NEW, start_line=1, end_line=1))


def test_quoting_lines_the_diff_does_not_show_names_them() -> None:
    with pytest.raises(AnchorLinesNotShownError, match=re.escape("a.py does not show new lines 5-6")):
        AnchorService(MOVED_DOWN).quote(_anchor([], 4, 6))


def test_quoting_a_removed_line_the_diff_does_not_show_says_removed() -> None:
    with pytest.raises(AnchorLinesNotShownError, match=re.escape("a.py does not show removed line 9")):
        AnchorService(MOVED_DOWN).quote(_anchor([], 9, 9, side=LineSide.OLD))


@pytest.mark.parametrize(
    ("anchor", "said"),
    [
        (_anchor([], 42, 42), "`a.py`:42"),
        (_anchor([], 42, 47), "`a.py`:42-47"),
        (_anchor([], 42, 42, side=LineSide.OLD), "`a.py`:42 (removed)"),
    ],
)
def test_a_place_is_named_the_way_the_review_names_it(anchor: LineAnchor, said: str) -> None:
    assert AnchorService([]).where(anchor) == said


def test_a_short_quote_found_in_several_places_follows_the_nearest() -> None:
    """A closing brace stands everywhere; the one that moved least is the one meant."""
    files = [_file("a.py", [_context(n, n, "}" if n in (3, 10) else f"line {n}") for n in range(1, 12)])]

    followed = AnchorService(files).follow(_anchor(["}"], 9, 9))

    assert followed.start_line == 10
