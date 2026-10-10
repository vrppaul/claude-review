"""What every page open on the review is told, and how a page that dropped its socket catches up.

Every page is told the same words, as things stood when they were told,
each push numbered across the run of the review. A page coming back says
the last number it had and is handed what it missed — or told plainly that
it cannot be, when the review no longer keeps it all.
"""

import asyncio

import pytest
from hypothesis import given, strategies as strategy

from claude_review.domain.models import AgentWork
from claude_review.domain.page_events import FileShown, WorkReported
from claude_review.presentation.broadcast import JOURNAL_DEPTH, BrowserBroadcast
from claude_review.presentation.event_pushes import push_of
from claude_review.presentation.wire.pushes import ShowPush
from claude_review.presentation.wire.session import Delivery, Resume, Welcome
from tests.helpers import message_said

# What the agent says it is doing, and what it goes on to do next
READING = "reading the handler"
REWRITING = "rewriting the handler"
REPORTED_AT = 1
# How many pushes a page here may fall behind by, and how many the review keeps for one coming back
BACKLOG = 4
KEPT = BACKLOG * JOURNAL_DEPTH
# How many pushes leave a page that reads nothing let go
LET_GO_AFTER = BACKLOG + 1
SHOWN_FILE = "a.py"
SHOWN = FileShown(file=SHOWN_FILE)
# A few pushes, fewer than a page may fall behind by
FEW = 3
# A run of the review other than the one listening
ANOTHER_RUN = "another-run"
# How far past what is kept the tests tell, to cover pages gone a long while
TOLD_AT_MOST = KEPT * 3


def _welcome(outbox: asyncio.Queue[str]) -> Welcome:
    message = message_said(outbox.get_nowait())
    assert isinstance(message, Welcome)
    return message


def _deliveries(outbox: asyncio.Queue[str]) -> list[Delivery]:
    """Everything delivered and not yet read."""
    delivered: list[Delivery] = []
    while not outbox.empty():
        message = message_said(outbox.get_nowait())
        assert isinstance(message, Delivery)
        delivered.append(message)
    return delivered


def _instance(broadcast: BrowserBroadcast) -> str:
    """Which run of the review a page would say it was reading."""
    outbox = broadcast.listen(resume=None)
    broadcast.stop_listening(outbox)
    return _welcome(outbox).instance


def _told_times(broadcast: BrowserBroadcast, count: int) -> None:
    for _ in range(count):
        broadcast.tell(SHOWN)


def test_a_push_says_what_was_true_when_it_was_pushed() -> None:
    """Every page open is told the same, and nothing changed afterwards reaches one still to be sent it."""
    broadcast = BrowserBroadcast(backlog=BACKLOG)
    tabs = [broadcast.listen(resume=None), broadcast.listen(resume=None)]
    work = AgentWork(message_id=None, text=READING, files=[], steps=[], at=REPORTED_AT)
    as_told = push_of(WorkReported(work=work.model_copy()))

    broadcast.tell(WorkReported(work=work))
    work.text = REWRITING

    for tab in tabs:
        _welcome(tab)
        assert [delivery.push for delivery in _deliveries(tab)] == [as_told]


def test_a_page_opening_is_welcomed_with_how_far_the_telling_has_got() -> None:
    broadcast = BrowserBroadcast(backlog=BACKLOG)
    _told_times(broadcast, FEW)

    opened = broadcast.listen(resume=None)

    welcome = _welcome(opened)
    assert (welcome.sequence, welcome.resumed) == (FEW, False)
    assert _deliveries(opened) == []


def test_every_push_is_numbered_in_the_order_it_was_told() -> None:
    broadcast = BrowserBroadcast(backlog=BACKLOG)
    outbox = broadcast.listen(resume=None)
    _welcome(outbox)

    _told_times(broadcast, FEW)

    delivered = _deliveries(outbox)
    assert [delivery.sequence for delivery in delivered] == list(range(1, FEW + 1))
    assert [delivery.push for delivery in delivered] == [ShowPush(file=SHOWN_FILE)] * FEW


@given(told=strategy.integers(min_value=0, max_value=TOLD_AT_MOST), data=strategy.data())
def test_a_page_coming_back_is_handed_exactly_what_it_missed(told: int, data: strategy.DataObject) -> None:
    missed = data.draw(strategy.integers(min_value=0, max_value=min(told, KEPT)))
    broadcast = BrowserBroadcast(backlog=BACKLOG)
    instance = _instance(broadcast)
    _told_times(broadcast, told)

    back = broadcast.listen(resume=Resume(instance=instance, after=told - missed))

    assert _welcome(back).resumed
    assert [delivery.sequence for delivery in _deliveries(back)] == list(range(told - missed + 1, told + 1))


@given(told=strategy.integers(min_value=KEPT + 1, max_value=TOLD_AT_MOST), data=strategy.data())
def test_a_page_that_missed_more_than_is_kept_is_told_it_was_not_handed_it(
    told: int, data: strategy.DataObject
) -> None:
    after = data.draw(strategy.integers(min_value=0, max_value=told - KEPT - 1))
    broadcast = BrowserBroadcast(backlog=BACKLOG)
    instance = _instance(broadcast)
    _told_times(broadcast, told)

    back = broadcast.listen(resume=Resume(instance=instance, after=after))

    welcome = _welcome(back)
    assert (welcome.sequence, welcome.resumed) == (told, False)
    assert _deliveries(back) == []


@pytest.mark.parametrize(
    "resume",
    [Resume(instance=ANOTHER_RUN, after=0), None],
    ids=["another run of the review", "a page that never had one"],
)
def test_a_page_from_another_run_is_not_resumed(resume: Resume | None) -> None:
    """A review restarted on the same port numbers its pushes afresh: the old numbers mean nothing."""
    broadcast = BrowserBroadcast(backlog=BACKLOG)
    _told_times(broadcast, FEW)

    back = broadcast.listen(resume=resume)

    assert not _welcome(back).resumed
    assert _deliveries(back) == []


def test_a_page_claiming_more_than_was_told_is_not_resumed() -> None:
    broadcast = BrowserBroadcast(backlog=BACKLOG)
    instance = _instance(broadcast)
    _told_times(broadcast, FEW)

    back = broadcast.listen(resume=Resume(instance=instance, after=FEW + 1))

    assert not _welcome(back).resumed


def test_a_page_that_falls_too_far_behind_is_let_go() -> None:
    """Held, its backlog would grow without end."""
    broadcast = BrowserBroadcast(backlog=BACKLOG)
    stuck = broadcast.listen(resume=None)

    _told_times(broadcast, LET_GO_AFTER)

    with pytest.raises(asyncio.QueueShutDown):
        stuck.get_nowait()


def test_a_page_let_go_is_told_nothing_more() -> None:
    broadcast = BrowserBroadcast(backlog=BACKLOG)
    stuck = broadcast.listen(resume=None)
    keeping_up = broadcast.listen(resume=None)
    _welcome(keeping_up)

    for _ in range(BACKLOG + 1):
        broadcast.tell(SHOWN)
        _deliveries(keeping_up)
    broadcast.tell(SHOWN)

    assert stuck.qsize() == 0
    assert [delivery.push for delivery in _deliveries(keeping_up)] == [ShowPush(file=SHOWN_FILE)]


def test_a_page_let_go_for_falling_behind_is_handed_what_it_missed_when_it_comes_back() -> None:
    broadcast = BrowserBroadcast(backlog=BACKLOG)
    stuck = broadcast.listen(resume=None)
    last_seen = _welcome(stuck)

    _told_times(broadcast, LET_GO_AFTER)
    back = broadcast.listen(resume=Resume(instance=last_seen.instance, after=last_seen.sequence))

    assert _welcome(back).resumed
    assert len(_deliveries(back)) == LET_GO_AFTER


def test_a_page_handed_a_backlog_of_what_it_missed_still_has_room_for_what_comes_next() -> None:
    broadcast = BrowserBroadcast(backlog=BACKLOG)
    instance = _instance(broadcast)
    _told_times(broadcast, BACKLOG)
    back = broadcast.listen(resume=Resume(instance=instance, after=0))

    broadcast.tell(SHOWN)

    _welcome(back)
    assert len(_deliveries(back)) == BACKLOG + 1
