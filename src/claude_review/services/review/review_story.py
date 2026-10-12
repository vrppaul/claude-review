"""The story a review holds: the last one the agent told of its change, and the round it was told in.

A story is told of the change as it stood. The round's work may move the
code under it afterwards, and the story is still what was told: so it is
kept whole with the round it was told in, and replaced whole by the next
telling, never patched.
"""

import asyncio

from pydantic import BaseModel, ConfigDict, Field

from claude_review.domain.models import FIRST_ROUND, DiffFile
from claude_review.domain.story import Step, Story, ToldStory
from claude_review.services.story_telling import tell


class StoryHeld(BaseModel):
    """A story as the review holds it: as it was told, and the round it was told in."""

    model_config = ConfigDict(frozen=True)

    story: ToldStory
    round: int = Field(ge=FIRST_ROUND)


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

    async def tell(self, story: Story[Step], change: list[DiffFile], *, round_number: int) -> StoryHeld:
        """Tell a story of a change and hold it, in place of any told before, with the round it arrived in.

        Told off the event loop: a story of a large change takes seconds to
        place on it, and the server has every page's socket and the agent's
        wait to keep answering meanwhile.

        Raises:
            StoryRefusedError: if anything is wrong with the story, carrying all of it; the story held stays.
        """
        async with self._telling:
            told = await asyncio.to_thread(tell, story, change)
            self._held = StoryHeld(story=told, round=round_number)
            return self._held
