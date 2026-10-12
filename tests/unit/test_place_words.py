"""How the review names a place: in plain words where text is read, in Markdown where it writes Markdown."""

import pytest
from hypothesis import given, strategies as strategy

from claude_review.domain.models import LineAnchor, LineSide, LineSpan
from claude_review.services.place_words import line_span, lines_named, place_in_markdown, place_in_words
from tests.helpers import line_anchor

FILE = "a.py"
# The largest number a line is written with: ten digits
LARGEST_LINE_WRITTEN = 9_999_999_999


@pytest.mark.parametrize(
    ("anchor", "in_words", "in_markdown"),
    [
        (line_anchor(FILE, 42), "a.py:42", "`a.py`:42"),
        (line_anchor(FILE, 42, 47), "a.py:42-47", "`a.py`:42-47"),
        (line_anchor(FILE, 42, side=LineSide.OLD), "a.py:42 (removed)", "`a.py`:42 (removed)"),
    ],
)
def test_a_place_is_named_the_same_way_in_words_and_in_markdown(
    anchor: LineAnchor, in_words: str, in_markdown: str
) -> None:
    assert place_in_words(anchor) == in_words
    assert place_in_markdown(anchor) == in_markdown


def test_a_backtick_in_a_path_does_not_end_its_code_early() -> None:
    """Ended early, the rest of the name would spill into the text as Markdown."""
    assert place_in_markdown(line_anchor("odd`name.py", 1)) == "``odd`name.py``:1"


def test_a_path_that_starts_with_a_backtick_is_set_apart_from_its_fence() -> None:
    assert place_in_markdown(line_anchor("`quoted`.py", 1)) == "`` `quoted`.py ``:1"


@pytest.mark.parametrize(("written", "first", "last"), [("42", 42, 42), ("42-47", 42, 47), ("47-42", 47, 42)])
def test_lines_are_read_as_somebody_wrote_them(written: str, first: int, last: int) -> None:
    """One line, or a first and a last: whether a file could have such lines is for whoever asked to say."""
    assert lines_named(written) == LineSpan(first=first, last=last)


@pytest.mark.parametrize("written", ["", "a", "42-", "-42", "42-47-50", " 42", "4 2", "42–47", "+42", "12345678901"])
def test_what_names_no_lines_is_not_read_as_some(written: str) -> None:
    with pytest.raises(ValueError, match="42-47"):
        lines_named(written)


@given(
    first=strategy.integers(min_value=0, max_value=LARGEST_LINE_WRITTEN),
    last=strategy.integers(min_value=0, max_value=LARGEST_LINE_WRITTEN),
)
def test_lines_written_are_read_back_as_the_lines_they_were(first: int, last: int) -> None:
    assert lines_named(line_span(first, last)) == LineSpan(first=first, last=last)
