"""The ids the agent's threads take beside the ones the page holds, and what the review says of those it cannot."""

import pytest
from structlog.typing import EventDict

from claude_review.services.review.reader_threads import ReaderThreads


def test_threads_the_review_cannot_take_are_said_once_while_every_hello_carries_them(logged: list[EventDict]) -> None:
    """A hello comes as often as once a second while the reader types: what was left out is said as it changes."""
    threads = ReaderThreads()

    threads.hold([], [], unnamed_count=1)
    threads.hold([], [], unnamed_count=1)

    assert [entry["event"] for entry in logged] == ["threads_left_out"]


@pytest.mark.parametrize(
    "held_id", ["raised-²", "raised-٣", "raised-"], ids=["superscript", "arabic-indic", "no-number"]
)
def test_an_id_this_review_never_hands_out_does_not_move_its_numbering(held_id: str) -> None:
    """The review numbers its own in plain digits; anything else is a page's id, however it reads."""
    threads = ReaderThreads()
    threads.hold([], [held_id], unnamed_count=0)

    assert threads.raise_id() == "raised-1"
