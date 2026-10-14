"""The story a review holds: the last one the agent told of its change, with the round and the take it was told of.

A story is told of the change as it stood. The round's work may move the
code under it afterwards, and the story is still what was told: so it is
kept whole with the round it was told in, and replaced whole by the next
telling, never patched. Its pieces are cut out of one take of the change,
so it says which: beside a later take they are no longer the code under
review, and only the take's number can tell whoever reads both.

The reader may ask for a story rather than wait to be told one. That
asking is kept here, beside the story that ends it: when it was asked, when
an agent took the request, whether the reader stopped it. A story is asked
for only while none is held and none is awaited, so however many pages
ask, and however often, the review is asked once.
"""

import asyncio

from pydantic import BaseModel, ConfigDict, Field

from claude_review.domain.interfaces import Clock
from claude_review.domain.models import FIRST_ROUND
from claude_review.domain.story import Step, Story, StoryAsking, ToldStory
from claude_review.services.review.review_content import FIRST_TAKE, ReviewContent
from claude_review.services.story_telling import tell


class StoryHeld(BaseModel):
    """A story as the review holds it: as it was told, the round it was told in, and the take it was told of."""

    model_config = ConfigDict(frozen=True)

    story: ToldStory
    round: int = Field(ge=FIRST_ROUND)
    # The take of the change its pieces were cut out of
    take: int = Field(ge=FIRST_TAKE)


class StoryStanding(BaseModel):
    """How a review stands with its story: the one it holds, and the reader's asking for one.

    Never both. Each is None in a review nobody has told a story of, or
    asked one from.
    """

    model_config = ConfigDict(frozen=True)

    held: StoryHeld | None
    asking: StoryAsking | None


class ReviewStory:
    """The story told of the review's change, the last told in place of any before, and the asking for one until then.

    What changes the asking — the reader asks, an agent takes the request,
    the reader stops it — answers with the asking as it then stands, or
    with None where it changed nothing.
    """

    def __init__(self, clock: Clock) -> None:
        self._clock = clock
        self._held: StoryHeld | None = None
        # From the reader's request until a story is told; None while nothing is asked
        self._asking: StoryAsking | None = None
        # Stories that arrive together are told one after another, as they
        # arrived: told side by side, a long one sent first would finish last
        # and take the place of the one sent after it
        self._telling = asyncio.Lock()

    @property
    def standing(self) -> StoryStanding:
        """The story held and the asking for one, as they stand together now."""
        return StoryStanding(held=self._held, asking=self._asking)

    def ask(self) -> StoryAsking | None:
        """Begin the reader's asking for a story, now, unless a story is held or one is still awaited.

        Asked again after the reader stopped it, the asking begins anew.
        """
        if self._held is not None or self._awaited is not None:
            return None
        self._asking = StoryAsking(asked_at=self._clock.now(), taken_at=None, stopped=False)
        return self._asking

    def taken(self) -> StoryAsking | None:
        """Note that an agent took the request for the story awaited, now."""
        awaited = self._awaited
        if awaited is None or awaited.taken_at is not None:
            return None
        self._asking = awaited.taken(self._clock.now())
        return self._asking

    def stop(self) -> StoryAsking | None:
        """Note that the reader stopped the story awaited: one told after all is still taken."""
        awaited = self._awaited
        if awaited is None:
            return None
        self._asking = awaited.stopped_by_the_reader()
        return self._asking

    async def tell(self, story: Story[Step], change: ReviewContent, *, round_number: int) -> StoryHeld:
        """Tell a story of a take of the change and hold it, in place of any told before, with the round it arrived in.

        Told off the event loop: a story of a large change takes seconds to
        place on it, and the server has every page's socket and the agent's
        wait to keep answering meanwhile. Held, it ends the asking for one,
        stopped or not.

        Raises:
            StoryRefusedError: if anything is wrong with the story, carrying all of it; the story held stays,
                and so does the asking.
        """
        async with self._telling:
            told = await asyncio.to_thread(tell, story, change.files)
            self._held = StoryHeld(story=told, round=round_number, take=change.take)
            self._asking = None
            return self._held

    @property
    def _awaited(self) -> StoryAsking | None:
        """The asking the reader still waits on: None where they asked for nothing, or stopped it."""
        if self._asking is None or self._asking.stopped:
            return None
        return self._asking
