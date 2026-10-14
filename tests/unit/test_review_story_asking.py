"""The asking for a story, as the review's `ReviewStory` keeps it: where there is nothing for it to note, and over a story held.

Through a review a request taken where none is awaited never happens: a
request stands in the agent's inbox only while its story is awaited and
nobody has taken it. The story's own state says what it does all the same,
whoever calls it.

A story is asked for while no story held is current: none is held, or a
round moved the code on under the one held. What went stale of that one is
said to whoever takes the request, as it then stands.
"""

from claude_review.domain.models import LineSpan, StaleStep, StoryWentStale
from claude_review.domain.story import StoryAsking
from claude_review.services.review.review_content import ReviewContent
from claude_review.services.review.review_story import ReviewStory
from tests.helpers import FixedClock
from tests.stories import (
    ASKED_AT,
    FIRST_REWRITTEN,
    NOTHING_LEFT_OUT,
    ONLY_CHAPTER,
    SECOND_ROUND,
    STORIED,
    THE_FIRST_LINE,
    TOLD_OF,
    told_then_followed,
)

# The asking begun at the moment the review's clock says
ASKED = StoryAsking(asked_at=ASKED_AT, taken_at=None, stopped=False)


def test_a_request_taken_where_no_story_is_awaited_is_noted_nowhere() -> None:
    story = ReviewStory(FixedClock(ASKED_AT))

    assert story.taken() is None
    assert story.asking is None


def test_a_request_taken_a_second_time_is_not_noted_again() -> None:
    story = ReviewStory(FixedClock(ASKED_AT))
    story.ask()
    story.taken()

    assert story.taken() is None


async def test_no_story_is_asked_for_over_a_story_held_that_is_current() -> None:
    story = await told_then_followed(TOLD_OF, NOTHING_LEFT_OUT)

    assert story.ask() is None


async def test_a_story_is_asked_for_over_one_a_round_moved_the_code_on_under() -> None:
    story = await told_then_followed(TOLD_OF, FIRST_REWRITTEN)

    assert story.ask() == ASKED


async def test_a_story_asked_for_over_one_that_moved_on_is_asked_once_while_it_is_awaited() -> None:
    story = await told_then_followed(TOLD_OF, FIRST_REWRITTEN)
    story.ask()

    assert story.ask() is None


async def test_a_story_told_again_over_one_that_moved_on_ends_the_asking() -> None:
    story = await told_then_followed(TOLD_OF, FIRST_REWRITTEN)
    story.ask()

    await story.tell(THE_FIRST_LINE, ReviewContent.opening_on(FIRST_REWRITTEN), round_number=SECOND_ROUND)

    assert story.asking is None


async def test_what_went_stale_is_the_round_the_code_moved_on_in_the_steps_it_changed_and_what_no_step_tells() -> None:
    story = await told_then_followed(TOLD_OF, FIRST_REWRITTEN)

    assert story.went_stale() == StoryWentStale(
        round=SECOND_ROUND,
        steps=[StaleStep(chapter=ONLY_CHAPTER, file=STORIED, lines=LineSpan(first=1, last=1))],
        left_out=1,
    )


async def test_nothing_went_stale_of_a_story_held_that_is_current() -> None:
    story = await told_then_followed(TOLD_OF, NOTHING_LEFT_OUT)

    assert story.went_stale() is None


def test_nothing_went_stale_where_no_story_is_held() -> None:
    assert ReviewStory(FixedClock(ASKED_AT)).went_stale() is None
