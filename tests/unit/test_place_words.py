"""How the review names a place: in plain words where text is read, in Markdown where it writes Markdown."""

import pytest

from claude_review.domain.models import LineAnchor, LineSide
from claude_review.services.place_words import place_in_markdown, place_in_words
from tests.helpers import line_anchor

FILE = "a.py"


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
