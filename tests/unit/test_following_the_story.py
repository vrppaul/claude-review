"""Following the story told onto each later take of the change, as the review holds it.

A story is always followed from the story as it was told, by the review's
own story part: it says which take it is of, whether the code moved on under
it, in which round, and how much it left out when it was told; and a story
told while the diff is taken again is followed once it is held. How the
takes themselves are taken, one at a time and each in its round, is said in
`tests/integration/test_taking_the_diff.py`.
"""

import asyncio
from typing import override

from claude_review.domain.interfaces import GitError
from claude_review.domain.models import FIRST_ROUND, FIRST_TAKE, DiffFile
from claude_review.domain.story import CodeMovedOn, LeftOutChanged
from claude_review.services.review.review_content import ReviewContent, TakesCompared
from tests.stories import (
    FIRST_REWRITTEN,
    NO_TAKES,
    NOTHING_LEFT_OUT,
    ONE_MORE_LEFT_OUT,
    SECOND_ROUND,
    THE_FIRST_LINE,
    TOLD_OF,
    TakesComparedByTheirLines,
    changed_file,
    hunk,
    step,
    story_of,
    review_story,
    take_of,
    told_then_followed,
    tree_of,
)

# The round a story's fourth take is taken in, each take after the first in a round of its own
FOURTH_ROUND = SECOND_ROUND + 2
# A file added whole and long, and a story with a step to every other line of it: long in the telling, so it is
# surely still being told when a test that started it follows the story onto a later take, of one line more
LONG_FILE = "src/long.py"
LINES_OF_THE_LONG_FILE = 4000
LONG_FILE_ADDED = [changed_file(LONG_FILE, hunk(0, 1, "+" * LINES_OF_THE_LONG_FILE))]
ONE_LINE_MORE_OF_IT = [changed_file(LONG_FILE, hunk(0, 1, "+" * (LINES_OF_THE_LONG_FILE + 1)))]
A_LONG_STORY = story_of(*[step(LONG_FILE, line, line) for line in range(1, LINES_OF_THE_LONG_FILE, 2)])


class TakesGitWillNotCompare(TakesCompared):
    """Takes whose trees git refuses to read, as when the review's object store was taken away under it."""

    @override
    async def changed_between(self, earlier: str, later: str) -> list[DiffFile]:
        refusal = "fatal: bad object"
        raise GitError(refusal)


async def test_a_story_followed_onto_a_later_take_is_of_that_take_and_still_of_the_round_that_told_it() -> None:
    held = (await told_then_followed(TOLD_OF, ONE_MORE_LEFT_OUT)).held

    assert held is not None
    assert (held.take, held.round) == (FIRST_TAKE + 1, FIRST_ROUND)


async def test_a_story_more_is_left_out_of_says_the_round_it_moved_on_in_and_what_was_left_out_then_and_now() -> None:
    held = (await told_then_followed(TOLD_OF, ONE_MORE_LEFT_OUT)).held

    assert held is not None
    assert held.moved_on == CodeMovedOn(round=SECOND_ROUND, left_out=LeftOutChanged(when_told=1, now=2))


async def test_a_story_that_moved_on_leaving_out_as_much_as_when_it_was_told_says_nothing_of_what_is_left_out() -> None:
    """The counts are said only where the round changed them: "1 → 1" would say nothing."""
    held = (await told_then_followed(TOLD_OF, FIRST_REWRITTEN)).held

    assert held is not None
    assert held.moved_on == CodeMovedOn(round=SECOND_ROUND, left_out=None)


async def test_a_story_the_code_stays_moved_on_under_says_the_round_it_first_moved_on_in() -> None:
    """Taken again in a later round with nothing more changed under it, it moved on when it first did."""
    held = (await told_then_followed(TOLD_OF, FIRST_REWRITTEN, FIRST_REWRITTEN)).held

    assert held is not None
    assert held.moved_on is not None
    assert held.moved_on.round == SECOND_ROUND


async def test_a_story_current_again_then_moved_on_again_says_the_round_it_moved_on_in_the_second_time() -> None:
    held = (await told_then_followed(TOLD_OF, FIRST_REWRITTEN, TOLD_OF, FIRST_REWRITTEN)).held

    assert held is not None
    assert held.moved_on is not None
    assert held.moved_on.round == FOURTH_ROUND


async def test_a_story_less_is_left_out_of_with_no_step_changed_is_current() -> None:
    held = (await told_then_followed(TOLD_OF, NOTHING_LEFT_OUT)).held

    assert held is not None
    assert held.moved_on is None


async def test_a_story_whose_code_was_put_back_as_it_was_told_is_current_again() -> None:
    """Followed from the story as it was told, never from the take before."""
    held = (await told_then_followed(TOLD_OF, FIRST_REWRITTEN, TOLD_OF)).held

    assert held is not None
    assert held.moved_on is None
    assert [told_step.now.changed_since_told for told_step in held.story.chapters[0].steps] == [False]


async def test_a_story_told_while_the_diff_is_taken_again_is_followed_onto_the_new_take_once_it_is_held() -> None:
    """The take waits for the telling under way: followed before it, the story told would stay on the take before.

    Followed from the very take it was told of: one line added below every
    step leaves each on the lines it was told on.
    """
    told_of, now = take_of(LONG_FILE_ADDED, FIRST_TAKE), take_of(ONE_LINE_MORE_OF_IT, FIRST_TAKE + 1)
    takes = TakesComparedByTheirLines(
        {tree_of(FIRST_TAKE): LONG_FILE_ADDED, tree_of(FIRST_TAKE + 1): ONE_LINE_MORE_OF_IT}
    )
    story = review_story(takes)
    telling = asyncio.create_task(story.tell(A_LONG_STORY, told_of, round_number=FIRST_ROUND))
    # A turn of the loop, in which the telling begins
    await asyncio.sleep(0)

    await story.follow(now, round_number=SECOND_ROUND)
    await telling

    assert story.held is not None
    assert story.held.take == FIRST_TAKE + 1
    assert [told_step.now.lines for told_step in story.held.story.chapters[0].steps] == [
        told_step.lines for told_step in A_LONG_STORY.chapters[0].steps
    ]


async def test_a_story_told_of_a_take_git_never_wrote_down_is_followed_onto_no_code() -> None:
    """What changed since it was told cannot be said: no step is drawn on code guessed at."""
    story = review_story(NO_TAKES)
    await story.tell(THE_FIRST_LINE, ReviewContent.opening_on(TOLD_OF), round_number=FIRST_ROUND)

    await story.follow(take_of(TOLD_OF, FIRST_TAKE + 1), round_number=SECOND_ROUND)

    assert story.held is not None
    assert [told_step.now for told_step in story.held.story.chapters[0].steps] == [None]


async def test_a_story_whose_takes_git_will_not_compare_is_followed_onto_no_code() -> None:
    story = review_story(TakesGitWillNotCompare())
    await story.tell(THE_FIRST_LINE, take_of(TOLD_OF, FIRST_TAKE), round_number=FIRST_ROUND)

    await story.follow(take_of(TOLD_OF, FIRST_TAKE + 1), round_number=SECOND_ROUND)

    assert story.held is not None
    assert [told_step.now for told_step in story.held.story.chapters[0].steps] == [None]


async def test_a_take_with_no_story_told_holds_none() -> None:
    story = review_story(NO_TAKES)

    await story.follow(take_of(ONE_MORE_LEFT_OUT, FIRST_TAKE + 1), round_number=SECOND_ROUND)

    assert story.held is None
