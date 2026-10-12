"""The story a review holds: the last one the agent told of its change, with the round and the take it was told of.

A story is told of the change as it stood. The round's work may move the
code under it afterwards, and the story is still what was told: so it is
kept whole with the round it was told in, and replaced whole by the next
telling, never patched. Its pieces are cut out of one take of the change,
so it says which: beside a later take they are no longer the code under
review, and only the take's number can tell whoever reads both.
"""

import asyncio

from pydantic import BaseModel, ConfigDict, Field

from claude_review.domain.models import FIRST_ROUND
from claude_review.domain.story import Step, Story, ToldStory
from claude_review.services.review.review_content import FIRST_TAKE, ReviewContent
from claude_review.services.story_telling import tell


class StoryHeld(BaseModel):
    """A story as the review holds it: as it was told, the round it was told in, and the take it was told of."""

    model_config = ConfigDict(frozen=True)

    story: ToldStory
    round: int = Field(ge=FIRST_ROUND)
    # The take of the change its pieces were cut out of
    take: int = Field(ge=FIRST_TAKE)


class ReviewStory:
    """The story told of the review's change, if one was: the last told, in place of any before it."""

    def __init__(self) -> None:
        self._held: StoryHeld | None = None
        # Stories that arrive together are told one after another, as they
        # arrived: told side by side, a long one sent first would finish last
        # and take the place of the one sent after it
        self._telling = asyncio.Lock()

    @property
    def held(self) -> StoryHeld | None:
        """The story held, or None while nobody has told one."""
        return self._held

    async def tell(self, story: Story[Step], change: ReviewContent, *, round_number: int) -> StoryHeld:
        """Tell a story of a take of the change and hold it, in place of any told before, with the round it arrived in.

        Told off the event loop: a story of a large change takes seconds to
        place on it, and the server has every page's socket and the agent's
        wait to keep answering meanwhile.

        Raises:
            StoryRefusedError: if anything is wrong with the story, carrying all of it; the story held stays.
        """
        async with self._telling:
            told = await asyncio.to_thread(tell, story, change.files)
            self._held = StoryHeld(story=told, round=round_number, take=change.take)
            return self._held
