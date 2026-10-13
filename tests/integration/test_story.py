"""A story told of a review's change: taken whole or refused whole, kept by the review, and read by its page.

The agent sends the story it wrote in one piece. The review tells it of the
change it holds, and from then on answers a page with the story as told —
each step with the piece of the change it shows — until the agent tells
another, which takes its place whole.
"""

import asyncio
from collections.abc import AsyncIterator
from http import HTTPStatus
from pathlib import Path

import pytest
from httpx import AsyncClient

from claude_review.domain.models import FIRST_ROUND
from claude_review.domain.story import Step, Story
from claude_review.presentation.wire.content import DiffResponse, ReviewResponse
from claude_review.presentation.wire.pushes import StoryPush
from claude_review.presentation.wire.refusal import Refusal
from claude_review.presentation.wire.story import LeftOutOfFile, StoryResponse, StoryTakenResponse
from claude_review.services.review.review import Review
from claude_review.services.review.review_content import FIRST_TAKE
from claude_review.services.review_opening import ReviewOpening
from tests.helpers import (
    DIFF_ROUTE,
    REVIEW_ROUTE,
    ReviewFactory,
    http_client,
    next_push,
    open_session,
    page_client,
    repository_opening,
    write_files,
)
from tests.stories import as_the_agent_writes, planted, rows_of, step, story_of

STORY_ROUTE = "/api/story"
SUBMIT_ROUTE = "/api/submit"
RETAKE_ROUTE = "/api/retake"
# The base a page asks for to read only what changed since the first round began
SINCE_THE_FIRST_ROUND = "round:1"

# What the repository under review has changed since its commit: a line added to a file, and a file added
EDITED_FILE = "initial.txt"
ADDED_FILE = "src/added.py"
THE_CHANGE = {EDITED_FILE: "initial content\nand a line since\n", ADDED_FILE: "def added() -> None:\n    return None\n"}
# The edited file as a round's work leaves it: the line the story told, said another way
REWORDED_SINCE = "initial content\nand a line reworded since\n"
# A file added whole and long, and a story with a step to every other line of it: long in the telling, so it is
# surely still being told when a test that started it looks at the review again, or sends another story after it
LONG_FILE = "src/long.py"
LINES_OF_THE_LONG_FILE = 4000
STEPS_OF_THE_LONG_STORY = [step(LONG_FILE, line, line) for line in range(1, LINES_OF_THE_LONG_FILE, 2)]
A_LONG_STORY = story_of(*STEPS_OF_THE_LONG_STORY)
# Steps that tell each of the two, and a story that tells the whole change
THE_LINE_ADDED = step(EDITED_FILE, 2, 2)
THE_FILE_ADDED = step(ADDED_FILE, 1, 2)
WHOLE_STORY = story_of(THE_LINE_ADDED, THE_FILE_ADDED)


@pytest.fixture
async def agent(reviews: ReviewFactory, tmp_git_repo: Path) -> AsyncIterator[AsyncClient]:
    """An agent's way into a review of a repository's changes."""
    write_files(tmp_git_repo, THE_CHANGE)
    async with http_client(reviews.app(await repository_opening(tmp_git_repo))) as calling:
        yield calling


async def tell(agent: AsyncClient, story: Story[Step]) -> StoryTakenResponse:
    """Tell the review a story, and read what it made of it."""
    answered = await agent.put(STORY_ROUTE, json=as_the_agent_writes(story))
    return StoryTakenResponse.model_validate_json(answered.content)


async def held_by(agent: AsyncClient) -> StoryResponse:
    """The story the review holds, as its page reads it."""
    return StoryResponse.model_validate_json((await agent.get(STORY_ROUTE)).content)


async def own_diff(agent: AsyncClient) -> DiffResponse:
    """The review's own diff, as its page reads it."""
    return DiffResponse.model_validate_json((await agent.get(DIFF_ROUTE)).content)


async def diff_against(agent: AsyncClient, base: str) -> DiffResponse:
    """The diff against another base, as a page that chose one reads it."""
    return DiffResponse.model_validate_json((await agent.get(DIFF_ROUTE, params={"base": base})).content)


async def take_again_after_a_round(agent: AsyncClient, repository: Path) -> None:
    """Send a round, do its work on the file the story told, and take the diff again."""
    await agent.post(SUBMIT_ROUTE, json={"threads": [], "body": "Another word for it, please.", "end": False})
    write_files(repository, {EDITED_FILE: REWORDED_SINCE})
    await agent.post(RETAKE_ROUTE)


async def test_a_story_told_of_the_change_is_taken_and_summed_up_in_a_line(agent: AsyncClient) -> None:
    taken = await tell(agent, WHOLE_STORY)

    assert taken == StoryTakenResponse(round=FIRST_ROUND, chapters=1, steps=2, left_out=[])


async def test_what_no_step_tells_is_said_to_the_agent_file_by_file(agent: AsyncClient) -> None:
    """So the agent knows what its story leaves the reader to find alone, without asking for the story back."""
    taken = await tell(agent, story_of(THE_LINE_ADDED))

    assert taken.left_out == [LeftOutOfFile(file=ADDED_FILE, changed_lines=2)]


async def test_a_review_nobody_told_a_story_of_holds_none(agent: AsyncClient) -> None:
    assert await held_by(agent) == StoryResponse(held=None)


async def test_a_page_reads_the_story_as_told_each_step_with_the_piece_of_the_change_it_shows(
    agent: AsyncClient,
) -> None:
    await tell(agent, WHOLE_STORY)

    held = (await held_by(agent)).held

    assert held is not None
    assert held.round == FIRST_ROUND
    assert [(told.file, rows_of(told.piece)) for told in held.story.chapters[0].steps] == [
        (EDITED_FILE, ["and a line since"]),
        (ADDED_FILE, ["def added() -> None:", "    return None"]),
    ]


async def test_a_story_told_again_takes_the_place_of_the_one_before_whole(agent: AsyncClient) -> None:
    await tell(agent, WHOLE_STORY)

    await tell(agent, story_of(THE_FILE_ADDED))

    held = (await held_by(agent)).held
    assert held is not None
    assert [told.file for told in held.story.chapters[0].steps] == [ADDED_FILE]
    assert [left.piece.path for left in held.story.left_out] == [EDITED_FILE]


async def test_a_story_with_things_wrong_is_refused_naming_each_where_the_document_has_it(agent: AsyncClient) -> None:
    """Everything at once, each at the field as the agent wrote it: one answer to put the whole story right by.

    Under the request's body, as a field of the wrong shape is named: a
    caller reads one place for a field, whoever refused it.
    """
    untitled = planted(story_of(THE_LINE_ADDED, step(ADDED_FILE, 7, 9)), ("title",), "")

    answered = await agent.put(STORY_ROUTE, json=as_the_agent_writes(untitled))

    assert answered.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    refused = Refusal.model_validate_json(answered.content)
    assert [field.loc for field in refused.detail] == [("body", "title"), ("body", "chapters", 0, "steps", 1, "lines")]


async def test_a_story_refused_takes_the_place_of_none(agent: AsyncClient) -> None:
    await tell(agent, WHOLE_STORY)
    told_first = await held_by(agent)

    await agent.put(STORY_ROUTE, json=as_the_agent_writes(planted(WHOLE_STORY, ("title",), "")))

    assert await held_by(agent) == told_first


async def test_a_document_of_the_wrong_shape_is_refused_as_any_request_is(agent: AsyncClient) -> None:
    misnamed = {**as_the_agent_writes(WHOLE_STORY), "doubts": "Whether it holds."}

    answered = await agent.put(STORY_ROUTE, json=misnamed)

    assert answered.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert [field.loc for field in Refusal.model_validate_json(answered.content).detail] == [("body", "doubts")]


async def test_a_review_of_no_change_takes_no_story(client: AsyncClient) -> None:
    """Files read once, or a conversation: nobody changed them, so there is no change to tell."""
    answered = await client.put(STORY_ROUTE, json=as_the_agent_writes(WHOLE_STORY))

    assert answered.status_code == HTTPStatus.NOT_FOUND
    assert await held_by(client) == StoryResponse(held=None)


async def test_a_review_of_no_change_says_so_to_whoever_tells_it_a_story(client: AsyncClient) -> None:
    """Told why, the agent stops trying: nothing it could write would be a story of this review."""
    answered = await client.put(STORY_ROUTE, json=as_the_agent_writes(WHOLE_STORY))

    assert "no change" in Refusal.model_validate_json(answered.content).detail


async def test_a_story_stays_as_it_was_told_when_the_diff_is_taken_again_and_says_which_round_told_it(
    agent: AsyncClient, tmp_git_repo: Path
) -> None:
    """The round's work may move the code under a story; what was told is still what was told, and of which round."""
    await tell(agent, WHOLE_STORY)
    told_first = await held_by(agent)

    await take_again_after_a_round(agent, tmp_git_repo)

    assert await held_by(agent) == told_first
    assert (await tell(agent, WHOLE_STORY)).round == FIRST_ROUND + 1


async def test_a_story_is_of_the_take_of_the_change_the_review_holds_as_it_is_told(agent: AsyncClient) -> None:
    """A page draws a story's pieces beside threads that hang on line numbers: both must be of one take."""
    await tell(agent, WHOLE_STORY)

    assert (await held_by(agent)).held.take == (await own_diff(agent)).take


async def test_the_diff_taken_again_is_of_another_take_than_the_story_told_before_it(
    agent: AsyncClient, tmp_git_repo: Path
) -> None:
    """So a page can tell a story of code that has moved on from one of the code it shows."""
    await tell(agent, WHOLE_STORY)

    await take_again_after_a_round(agent, tmp_git_repo)

    assert (await held_by(agent)).held.take != (await own_diff(agent)).take


async def test_a_story_told_after_the_diff_was_taken_again_is_of_the_take_the_diff_is_now(
    agent: AsyncClient, tmp_git_repo: Path
) -> None:
    await tell(agent, WHOLE_STORY)
    await take_again_after_a_round(agent, tmp_git_repo)

    await tell(agent, story_of(THE_FILE_ADDED))

    assert (await held_by(agent)).held.take == (await own_diff(agent)).take


async def test_a_diff_read_against_a_narrower_base_says_the_take_of_the_reviews_own(
    agent: AsyncClient, tmp_git_repo: Path
) -> None:
    """Whatever a page reads its files against, the take it learns is the one a story must be of."""
    await take_again_after_a_round(agent, tmp_git_repo)

    narrowed = await diff_against(agent, SINCE_THE_FIRST_ROUND)

    assert narrowed.base.narrowed is True
    assert narrowed.take == (await own_diff(agent)).take


@pytest.fixture
async def review(reviews: ReviewFactory, tmp_git_repo: Path) -> AsyncIterator[Review]:
    """A review of a repository's changes, opened as a server opens one, for a test that calls it itself."""
    write_files(tmp_git_repo, {**THE_CHANGE, LONG_FILE: "line\n" * LINES_OF_THE_LONG_FILE})
    hosted = reviews.hosted(await repository_opening(tmp_git_repo))
    async with http_client(hosted.app):
        yield hosted.review


async def test_the_review_goes_on_answering_while_a_story_is_told(review: Review) -> None:
    """Told on the event loop, a long story kept every page and agent waiting until it was placed."""
    telling = asyncio.ensure_future(review.tell_story(A_LONG_STORY))

    await asyncio.sleep(0)
    await asyncio.sleep(0)
    await asyncio.sleep(0)

    # Turns of the loop, as any socket the server holds is answered in, and the story is still being told
    assert not telling.done()
    assert len((await telling).story.chapters[0].steps) == len(STEPS_OF_THE_LONG_STORY)


async def test_of_two_stories_told_at_once_the_one_sent_last_is_the_one_held(review: Review) -> None:
    """A long story sent first is still being told when a short one arrives: the short one is the last word."""
    sent_first = asyncio.ensure_future(review.tell_story(A_LONG_STORY))
    sent_last = asyncio.ensure_future(review.tell_story(story_of(THE_LINE_ADDED)))

    await asyncio.gather(sent_first, sent_last)

    assert review.story_held() == sent_last.result()


async def test_a_story_is_held_with_the_round_it_arrived_in_though_a_round_begins_while_it_is_told(
    review: Review,
) -> None:
    """It was told of the change as that round had it."""
    telling = asyncio.ensure_future(review.tell_story(A_LONG_STORY))
    await asyncio.sleep(0)

    review.submit(threads=[], body="One more line, please.", ends=False)

    assert (await telling).round == FIRST_ROUND


async def test_telling_a_story_says_the_agent_is_there(agent: AsyncClient) -> None:
    before = ReviewResponse.model_validate_json((await agent.get(REVIEW_ROUTE)).content)

    await tell(agent, WHOLE_STORY)

    after = ReviewResponse.model_validate_json((await agent.get(REVIEW_ROUTE)).content)
    assert (before.answerer_attached, after.answerer_attached) == (False, True)


async def test_a_review_of_a_change_says_it_takes_a_story(agent: AsyncClient) -> None:
    """Said by the review, so its page offers a story where one can be told and asks nothing of what kind it is."""
    facts = ReviewResponse.model_validate_json((await agent.get(REVIEW_ROUTE)).content)

    assert facts.takes_a_story is True


async def test_a_review_of_no_change_says_it_takes_no_story(client: AsyncClient) -> None:
    facts = ReviewResponse.model_validate_json((await client.get(REVIEW_ROUTE)).content)

    assert facts.takes_a_story is False


async def test_a_review_of_no_change_is_read_at_the_take_it_was_made_with(client: AsyncClient) -> None:
    """Nothing takes it again, so the take its page reads is the first."""
    assert (await own_diff(client)).take == FIRST_TAKE


@pytest.fixture
async def opened_on_the_change(tmp_git_repo: Path) -> ReviewOpening:
    """What a review of the repository's change opens on, for a test that opens its page itself."""
    write_files(tmp_git_repo, THE_CHANGE)
    return await repository_opening(tmp_git_repo)


def test_a_page_open_on_the_review_is_told_when_a_story_is_told(
    reviews: ReviewFactory, opened_on_the_change: ReviewOpening
) -> None:
    """A page does not ask again and again whether a story has come: it is told, and reads the story then."""
    with page_client(reviews.app(opened_on_the_change)) as review_page, open_session(review_page) as socket:
        review_page.put(STORY_ROUTE, json=as_the_agent_writes(WHOLE_STORY))

        # That it arrives is the whole of it: the push says nothing more, and none arriving fails the test
        next_push(socket, StoryPush)
