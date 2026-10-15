"""The story a review holds, as a page is told it: on a take of the change, and whether the code moved on under it.

The wire's twin of the review's own story held
(`services/review/review_story.py`), in a module of its own: it is made
from that, and an agent's command, which reads the story's document from
`wire/story.py`, must not load the review's work (pyproject's import
contracts).
"""

from typing import Self

from claude_review.presentation.wire.base import WireModel
from claude_review.presentation.wire.story import CodeMovedOn, ToldStory
from claude_review.services.review import review_story


class StoryHeld(WireModel):
    """A story as the review holds it: on a take of the change, with the round it was told in."""

    story: ToldStory
    round: int
    # The take of the change its pieces were cut out of: their lines are
    # numbered as the threads' are only while the diff a page read says the
    # same take
    take: int
    # Set while the code under it moved on after it was told; None while it is current
    moved_on: CodeMovedOn | None

    @classmethod
    def as_held(cls, held: review_story.StoryHeld) -> Self:
        """The story held, each of its chapters saying whether a round changed code its steps show, and in which."""
        moved_on = None if held.moved_on is None else CodeMovedOn.of(held.moved_on)
        return cls(
            story=ToldStory.on_take(held.story, moved_on=moved_on), round=held.round, take=held.take, moved_on=moved_on
        )


class StoryResponse(WireModel):
    """Response for GET /api/story — the story the review holds, or none while nobody has told one."""

    held: StoryHeld | None
