"""What the reader handed over for the agent and then took back, and what the review wants of the agent unsaid.

A request the reader stops before any agent took it should cost the agent
nothing, not even the reading of it. So what waits in the inbox can be
taken back, and whoever takes it back is told whether it was still there:
once an agent has it, taking it back is too late, and the agent must be
told another way.

A story the review wants waits in no queue: its owner keeps it, and a wait
is handed it once nothing the reader said is left.
"""

import asyncio
from collections import deque
from collections.abc import AsyncIterator, Coroutine
from contextvars import Context
from typing import override

import pytest

from claude_review.domain.models import AgentEvent, PanelCancel, StoryCancelled, StoryRequested
from claude_review.services.review.agent_inbox import AgentInbox, Silence, StandingRequest
from claude_review.services.review.review_lifetime import EndReason, ReviewLifetime
from tests.helpers import RecordingPage

# How long a wait is given where the test expects it to find nothing
A_MOMENT_SECONDS = 0.01

HANDED_IN_FIRST = PanelCancel(message_id="panel-1")
HANDED_IN_LAST = PanelCancel(message_id="panel-2")
# A story the review wants, as a wait is handed it
WANTED = StoryRequested(stale=None)
# Long enough for the test to make the story wanted while a wait sleeps
A_WHILE_SECONDS = 5.0


class StoryWanted(StandingRequest):
    """A story the review wants once the test says so, handed to the first wait that claims it."""

    def __init__(self) -> None:
        self._due = asyncio.Event()
        self._wanted: deque[StoryRequested] = deque()

    @property
    @override
    def due(self) -> asyncio.Event:
        return self._due

    def fall_due(self) -> None:
        self._wanted.append(WANTED)
        self._due.set()

    @override
    def claim(self) -> AgentEvent | None:
        claimed = list(self._wanted)
        self._wanted.clear()
        self._due.clear()
        return next(iter(claimed), None)


# More tasks than a wait starts that sleeps until its time is up: its two watches, and a sleep or two. A
# wait that never sleeps starts one for every turn of the loop, thousands in the moment it is given
MORE_THAN_A_SLEEPING_WAIT_STARTS = 10


class TasksStarted:
    """Counts the tasks an event loop starts, standing in for what makes them."""

    def __init__(self) -> None:
        self.count = 0

    def start[ResultT](
        self, loop: asyncio.AbstractEventLoop, work: Coroutine[None, None, ResultT], **given: Context | None
    ) -> asyncio.Task[ResultT]:
        self.count += 1
        return asyncio.Task(work, loop=loop, **given)


@pytest.fixture
async def tasks_started() -> AsyncIterator[TasksStarted]:
    """A count of the tasks the test's loop starts, from here to the end of the test."""
    started = TasksStarted()
    loop = asyncio.get_running_loop()
    loop.set_task_factory(started.start)
    yield started
    loop.set_task_factory(None)


def _inbox() -> AgentInbox:
    """An inbox of a review that wants nothing of the agent unsaid."""
    return _inbox_beside(StoryWanted())


def _inbox_beside(standing: StoryWanted) -> AgentInbox:
    """An inbox of a review whose wanting a story the test says."""
    return AgentInbox(ReviewLifetime(RecordingPage()), standing=standing)


async def _taken_from(inbox: AgentInbox) -> AgentEvent | Silence:
    """What an agent's wait takes from the inbox, giving up after a moment, its caller staying to the end."""
    return await inbox.take(within=A_MOMENT_SECONDS, caller_left=asyncio.Event().wait())


async def test_what_was_handed_in_and_taken_back_reaches_no_wait() -> None:
    inbox = _inbox()
    inbox.hand_in(StoryCancelled())

    inbox.withdraw(StoryCancelled())

    assert await _taken_from(inbox) == Silence.TIMED_OUT


async def test_taking_back_what_still_waits_says_it_was_there() -> None:
    inbox = _inbox()
    inbox.hand_in(StoryCancelled())

    assert inbox.withdraw(StoryCancelled()) is True


async def test_what_a_wait_already_took_cannot_be_taken_back() -> None:
    """Whoever asks is told so, and tells the agent another way."""
    inbox = _inbox()
    inbox.hand_in(StoryCancelled())
    await _taken_from(inbox)

    assert inbox.withdraw(StoryCancelled()) is False


async def test_what_was_never_handed_in_cannot_be_taken_back() -> None:
    assert _inbox().withdraw(StoryCancelled()) is False


async def test_taking_one_thing_back_leaves_everything_else_in_the_order_it_was_handed_in() -> None:
    inbox = _inbox()
    inbox.hand_in(HANDED_IN_FIRST)
    inbox.hand_in(StoryCancelled())
    inbox.hand_in(HANDED_IN_LAST)

    inbox.withdraw(StoryCancelled())

    assert [await _taken_from(inbox), await _taken_from(inbox)] == [HANDED_IN_FIRST, HANDED_IN_LAST]


async def test_only_what_is_named_is_taken_back() -> None:
    inbox = _inbox()
    inbox.hand_in(StoryCancelled())

    inbox.withdraw(HANDED_IN_FIRST)

    assert await _taken_from(inbox) == StoryCancelled()


async def test_a_wait_sleeps_until_its_time_is_up_once_what_was_handed_in_is_taken_back(
    tasks_started: TasksStarted,
) -> None:
    """Nothing is left to wake for. A wait that went on waking would start one sleep after another, without end."""
    inbox = _inbox()
    inbox.hand_in(StoryCancelled())
    inbox.withdraw(StoryCancelled())

    await _taken_from(inbox)

    assert tasks_started.count < MORE_THAN_A_SLEEPING_WAIT_STARTS


async def test_what_the_reader_said_is_handed_out_before_a_story_the_review_wants() -> None:
    """A round sent after the story was wanted is answered first: the story is then told of the code it leaves."""
    wanted = StoryWanted()
    inbox = _inbox_beside(wanted)
    wanted.fall_due()
    inbox.hand_in(HANDED_IN_FIRST)

    assert [await _taken_from(inbox), await _taken_from(inbox)] == [HANDED_IN_FIRST, WANTED]


async def test_a_waiting_agent_is_handed_a_story_the_moment_the_review_wants_one() -> None:
    wanted = StoryWanted()
    inbox = _inbox_beside(wanted)
    waiting = asyncio.ensure_future(inbox.take(within=A_WHILE_SECONDS, caller_left=asyncio.Event().wait()))
    # A turn of the loop, in which the wait goes to sleep
    await asyncio.sleep(0)

    wanted.fall_due()

    assert await asyncio.wait_for(waiting, timeout=A_WHILE_SECONDS) == WANTED


async def test_a_story_wanted_is_handed_to_one_wait_alone() -> None:
    wanted = StoryWanted()
    inbox = _inbox_beside(wanted)
    wanted.fall_due()

    assert [await _taken_from(inbox), await _taken_from(inbox)] == [WANTED, Silence.TIMED_OUT]


async def test_a_review_that_ended_hands_no_agent_a_story_it_wanted() -> None:
    """Nothing the reader said is left, and the review a story would be told of is over."""
    wanted = StoryWanted()
    lifetime = ReviewLifetime(RecordingPage())
    inbox = AgentInbox(lifetime, standing=wanted)
    wanted.fall_due()

    lifetime.end(EndReason.FINISHED)

    assert await _taken_from(inbox) == Silence.CLOSED
