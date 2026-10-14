"""The asking for a story, as the review's `ReviewStory` keeps it, where there is nothing for it to note.

Through a review neither case happens: a request stands in the agent's
inbox only while its story is awaited and nobody has taken it. The story's
own state says what it does all the same, whoever calls it.
"""

from claude_review.services.review.review_story import ReviewStory
from tests.helpers import FixedClock

# The moment the review's clock says, whenever it is asked
NOW = 1_791_000_000_000


def test_a_request_taken_where_no_story_is_awaited_is_noted_nowhere() -> None:
    story = ReviewStory(FixedClock(NOW))

    assert story.taken() is None
    assert story.standing.asking is None


def test_a_request_taken_a_second_time_is_not_noted_again() -> None:
    story = ReviewStory(FixedClock(NOW))
    story.ask()
    story.taken()

    assert story.taken() is None
