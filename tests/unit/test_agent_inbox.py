"""What the reader handed over for the agent and then took back: it reaches no agent, while nobody has taken it.

A request the reader stops before any agent took it should cost the agent
nothing, not even the reading of it. So what waits in the inbox can be
taken back, and whoever takes it back is told whether it was still there:
once an agent has it, taking it back is too late, and the agent must be
told another way.
"""

import asyncio

from claude_review.domain.models import AgentEvent, PanelCancel, StoryCancelled, StoryRequested
from claude_review.services.review.agent_inbox import AgentInbox, Silence
from claude_review.services.review.review_lifetime import ReviewLifetime
from tests.helpers import RecordingPage

# How long a wait is given where the test expects it to find nothing
A_MOMENT_SECONDS = 0.01

HANDED_IN_FIRST = PanelCancel(message_id="panel-1")
HANDED_IN_LAST = PanelCancel(message_id="panel-2")


def _inbox() -> AgentInbox:
    return AgentInbox(ReviewLifetime(RecordingPage()))


async def _taken_from(inbox: AgentInbox) -> AgentEvent | Silence:
    """What an agent's wait takes from the inbox, giving up after a moment, its caller staying to the end."""
    return await inbox.take(within=A_MOMENT_SECONDS, caller_left=asyncio.Event().wait())


async def test_what_was_handed_in_and_taken_back_reaches_no_wait() -> None:
    inbox = _inbox()
    inbox.hand_in(StoryRequested())

    inbox.withdraw(StoryRequested())

    assert await _taken_from(inbox) == Silence.TIMED_OUT


async def test_taking_back_what_still_waits_says_it_was_there() -> None:
    inbox = _inbox()
    inbox.hand_in(StoryRequested())

    assert inbox.withdraw(StoryRequested()) is True


async def test_what_a_wait_already_took_cannot_be_taken_back() -> None:
    """Whoever asks is told so, and tells the agent another way."""
    inbox = _inbox()
    inbox.hand_in(StoryRequested())
    await _taken_from(inbox)

    assert inbox.withdraw(StoryRequested()) is False


async def test_what_was_never_handed_in_cannot_be_taken_back() -> None:
    assert _inbox().withdraw(StoryRequested()) is False


async def test_taking_one_thing_back_leaves_everything_else_in_the_order_it_was_handed_in() -> None:
    inbox = _inbox()
    inbox.hand_in(HANDED_IN_FIRST)
    inbox.hand_in(StoryRequested())
    inbox.hand_in(HANDED_IN_LAST)

    inbox.withdraw(StoryRequested())

    assert [await _taken_from(inbox), await _taken_from(inbox)] == [HANDED_IN_FIRST, HANDED_IN_LAST]


async def test_only_what_is_named_is_taken_back() -> None:
    inbox = _inbox()
    inbox.hand_in(StoryRequested())

    inbox.withdraw(StoryCancelled())

    assert await _taken_from(inbox) == StoryRequested()
