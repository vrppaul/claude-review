"""The story a review holds: the last one the agent told of its change, and the round it was told in.

A story is told of the change as it stood. The round's work may move the
code under it afterwards, and the story is still what was told: so it is
kept whole with the round it was told in, and replaced whole by the next
telling, never patched.
"""

from pydantic import BaseModel, ConfigDict, Field

from claude_review.domain.models import FIRST_ROUND
from claude_review.domain.story import ToldStory


class StoryHeld(BaseModel):
    """A story as the review holds it: as it was told, and the round it was told in."""

    model_config = ConfigDict(frozen=True)

    story: ToldStory
    round: int = Field(ge=FIRST_ROUND)


class ReviewStory:
    """The story told of the review's change, if one was: the last told, in place of any before it."""

    def __init__(self) -> None:
        self._held: StoryHeld | None = None

    @property
    def held(self) -> StoryHeld | None:
        """The story held, or None while nobody has told one."""
        return self._held

    def keep(self, story: ToldStory, *, round_number: int) -> StoryHeld:
        """Hold a story just told, in place of any told before, and say how it is held."""
        self._held = StoryHeld(story=story, round=round_number)
        return self._held
