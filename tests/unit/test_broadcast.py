"""What every page open on the review is told: the same words, as things stood when they were told."""

import asyncio
import json

import pytest

from claude_review.domain.models import AgentWork
from claude_review.domain.page_events import FileShown, WorkReported
from claude_review.presentation.broadcast import BrowserBroadcast

# What the agent says it is doing, and what it goes on to do next
READING = "reading the handler"
REWRITING = "rewriting the handler"
REPORTED_AT = 1
# How many pushes a page here may fall behind by
BACKLOG = 2
SHOWN = FileShown(file="a.py")


def test_a_push_says_what_was_true_when_it_was_pushed() -> None:
    """Every page open is told the same, and nothing changed afterwards reaches one still to be sent it."""
    broadcast = BrowserBroadcast(backlog=BACKLOG)
    first_tab = broadcast.listen(first=[])
    second_tab = broadcast.listen(first=[])
    work = AgentWork(message_id=None, text=READING, files=[], steps=[], at=REPORTED_AT)

    broadcast.tell(WorkReported(work=work))
    work.text = REWRITING

    told = [json.loads(tab.get_nowait()) for tab in (first_tab, second_tab)]
    assert [said["work"]["text"] for said in told] == [READING, READING]


def test_a_page_opening_is_told_first_what_it_must_know() -> None:
    broadcast = BrowserBroadcast(backlog=BACKLOG)
    work = AgentWork(message_id=None, text=READING, files=[], steps=[], at=REPORTED_AT)

    opened = broadcast.listen(first=[WorkReported(work=work)])

    assert json.loads(opened.get_nowait()) == {"type": "progress", "work": work.model_dump(mode="json")}


def test_a_page_that_falls_too_far_behind_is_let_go() -> None:
    """Held, it would grow without end; let go, it reconnects and reads the review afresh."""
    broadcast = BrowserBroadcast(backlog=BACKLOG)
    stuck = broadcast.listen(first=[])

    for _ in range(BACKLOG + 1):
        broadcast.tell(SHOWN)

    with pytest.raises(asyncio.QueueShutDown):
        stuck.get_nowait()


def test_a_page_let_go_is_told_nothing_more() -> None:
    broadcast = BrowserBroadcast(backlog=BACKLOG)
    stuck = broadcast.listen(first=[])
    keeping_up = broadcast.listen(first=[])

    for _ in range(BACKLOG + 1):
        broadcast.tell(SHOWN)
        keeping_up.get_nowait()
    broadcast.tell(SHOWN)

    assert stuck.qsize() == 0
    assert json.loads(keeping_up.get_nowait()) == {"type": "show", "file": "a.py"}
