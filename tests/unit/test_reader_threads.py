"""The ids the agent's threads take beside the ones the page holds."""

import pytest

from claude_review.services.review.reader_threads import ReaderThreads


@pytest.mark.parametrize(
    "held_id", ["raised-²", "raised-٣", "raised-"], ids=["superscript", "arabic-indic", "no-number"]
)
def test_an_id_this_review_never_hands_out_does_not_move_its_numbering(held_id: str) -> None:
    """The review numbers its own in plain digits; anything else is a page's id, however it reads."""
    threads = ReaderThreads()
    threads.hold([], [held_id])

    assert threads.raise_id() == "raised-1"
