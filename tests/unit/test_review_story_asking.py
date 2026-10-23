"""The asking for a story, as the review's `ReviewStory` keeps it: its one owner, asked by the reader or by itself.

A story is asked for while no story held is current: none is held, or a
round moved the code on under the one held. The reader asks, or has every
review's story written as it opens; a story so asked for is asked for again
after each retake that leaves it stale, until the reader stops it. One the
agent told unasked is not asked for again. An agent's wait
claims the asking once, and is told what went stale of the story held, as
it then stands. A review of no change asks for none, and refuses both the
reader's asking and a story told of it.
"""

import asyncio

from claude_review.domain.models import FIRST_TAKE, LineSpan, StaleStep, StoryRequested, StoryWentStale
from claude_review.domain.story import StoryAsking
from claude_review.services.review.review_content import ReviewContent
from tests.stories import (
    ASKED_AT,
    FIRST_REWRITTEN,
    NO_TAKES,
    NOTHING_LEFT_OUT,
    ONLY_CHAPTER,
    SECOND_ROUND,
    NOT_AS_IT_OPENS,
    STORIED,
    THE_FIRST_LINE,
    TOLD_OF,
    TakesComparedByTheirLines,
    review_story,
    story_of_no_change,
    take_of,
    told_then_followed,
    tree_of,
    WRITTEN_AS_IT_OPENS,
)

# The asking begun at the moment the review's clock says
ASKED = StoryAsking(asked_at=ASKED_AT, taken_at=None, stopped=False)


def test_a_review_whose_reader_has_stories_written_as_each_review_opens_asks_for_one_as_it_opens() -> None:
    assert review_story(NO_TAKES).open(writes_as_it_opens=WRITTEN_AS_IT_OPENS) == ASKED


def test_a_review_whose_reader_waits_to_ask_for_a_story_asks_for_none_as_it_opens() -> None:
    """Asked first, or written at a press on Story: either way the story waits for the reader."""
    assert review_story(NO_TAKES).open(writes_as_it_opens=NOT_AS_IT_OPENS) is None


def test_a_review_of_no_change_asks_for_no_story_as_it_opens_whatever_the_reader_chose() -> None:
    """Files read once, or a conversation: there is nothing to tell a story of."""
    assert story_of_no_change().open(writes_as_it_opens=WRITTEN_AS_IT_OPENS) is None


def test_a_story_asked_for_is_due_for_an_agent_until_one_claims_it() -> None:
    story = review_story(NO_TAKES)
    story.ask()
    due_while_asked = story.due.is_set()

    story.claim()

    assert (due_while_asked, story.due.is_set()) == (True, False)


def test_a_story_the_reader_stopped_before_any_agent_claimed_it_is_due_for_none() -> None:
    story = review_story(NO_TAKES)
    story.ask()

    story.stop()

    assert (story.due.is_set(), story.claim()) == (False, None)


def test_an_agent_claiming_the_story_asked_for_is_handed_it_and_it_is_noted_taken() -> None:
    """Asked where none was told: nothing went stale."""
    story = review_story(NO_TAKES)
    story.ask()

    assert story.claim() == StoryRequested(stale=None)
    assert story.asking == StoryAsking(asked_at=ASKED_AT, taken_at=ASKED_AT, stopped=False)


def test_a_story_is_claimed_where_none_is_asked_for_by_no_agent() -> None:
    story = review_story(NO_TAKES)

    assert story.claim() is None
    assert story.asking is None


def test_a_story_asked_for_is_claimed_by_one_agent_only() -> None:
    story = review_story(NO_TAKES)
    story.ask()
    story.claim()

    assert story.claim() is None


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

    assert (story.asking, story.due.is_set()) == (None, False)


async def test_a_story_the_reader_asked_for_is_asked_for_again_once_a_retake_leaves_it_stale() -> None:
    """They asked for this review's story: told of the code before the round, it is told again of the code after."""
    story = review_story(TakesComparedByTheirLines({tree_of(FIRST_TAKE): TOLD_OF, tree_of(2): FIRST_REWRITTEN}))
    story.ask()
    await story.tell(THE_FIRST_LINE, take_of(TOLD_OF, FIRST_TAKE), round_number=SECOND_ROUND)

    assert await story.follow(take_of(FIRST_REWRITTEN, 2), round_number=SECOND_ROUND) == ASKED


async def test_a_story_told_unasked_is_not_asked_for_again_once_a_retake_leaves_it_stale() -> None:
    """Nobody asked for it in this review: telling it again would spend tokens nobody chose to spend."""
    story = review_story(TakesComparedByTheirLines({tree_of(FIRST_TAKE): TOLD_OF, tree_of(2): FIRST_REWRITTEN}))
    await story.tell(THE_FIRST_LINE, take_of(TOLD_OF, FIRST_TAKE), round_number=SECOND_ROUND)

    assert await story.follow(take_of(FIRST_REWRITTEN, 2), round_number=SECOND_ROUND) is None


async def test_a_story_the_reader_stopped_is_not_asked_for_again_by_a_retake() -> None:
    """They stopped it to keep the agent's tokens: the round's work does not start it again."""
    story = review_story(TakesComparedByTheirLines({tree_of(FIRST_TAKE): TOLD_OF}))
    story.ask()
    story.stop()

    assert await story.follow(take_of(TOLD_OF, FIRST_TAKE), round_number=SECOND_ROUND) is None


async def test_a_retake_that_leaves_the_story_asked_for_current_asks_for_none() -> None:
    story = review_story(TakesComparedByTheirLines({tree_of(FIRST_TAKE): TOLD_OF, tree_of(2): NOTHING_LEFT_OUT}))
    story.ask()
    await story.tell(THE_FIRST_LINE, take_of(TOLD_OF, FIRST_TAKE), round_number=SECOND_ROUND)

    assert await story.follow(take_of(NOTHING_LEFT_OUT, 2), round_number=SECOND_ROUND) is None


async def test_a_story_that_arrives_during_a_retake_which_leaves_it_stale_is_asked_for_again() -> None:
    """Told of the take before, it ends the asking as it arrives; followed once held, it is found stale, and the
    want is decided after that, so the story the reader sees is asked for again."""
    story = review_story(TakesComparedByTheirLines({tree_of(FIRST_TAKE): TOLD_OF, tree_of(2): FIRST_REWRITTEN}))
    story.open(writes_as_it_opens=WRITTEN_AS_IT_OPENS)
    telling = asyncio.create_task(story.tell(THE_FIRST_LINE, take_of(TOLD_OF, FIRST_TAKE), round_number=SECOND_ROUND))
    # A turn of the loop, in which the telling begins
    await asyncio.sleep(0)

    await story.follow(take_of(FIRST_REWRITTEN, 2), round_number=SECOND_ROUND)
    await telling

    assert (story.asking, story.due.is_set()) == (ASKED, True)


async def test_what_went_stale_is_the_round_the_code_moved_on_in_the_steps_it_changed_and_what_no_step_tells() -> None:
    story = await told_then_followed(TOLD_OF, FIRST_REWRITTEN)

    assert story.went_stale() == StoryWentStale(
        round=SECOND_ROUND,
        steps=[StaleStep(chapter=ONLY_CHAPTER, file=STORIED, lines=LineSpan(first=1, last=1))],
        left_out=1,
    )


async def test_what_went_stale_names_a_step_whose_code_is_no_longer_found_by_its_chapter_and_file_alone() -> None:
    """Its file left the change: no lines of the take are its own, and none is named as if they were."""
    story = await told_then_followed(TOLD_OF, [])

    assert story.went_stale() == StoryWentStale(
        round=SECOND_ROUND, steps=[StaleStep(chapter=ONLY_CHAPTER, file=STORIED, lines=None)], left_out=0
    )


async def test_nothing_went_stale_of_a_story_held_that_is_current() -> None:
    story = await told_then_followed(TOLD_OF, NOTHING_LEFT_OUT)

    assert story.went_stale() is None


def test_nothing_went_stale_where_no_story_is_held() -> None:
    assert review_story(NO_TAKES).went_stale() is None
