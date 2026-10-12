"""A story told of a review's change: taken whole or refused whole, kept by the review, and read by its page.

The agent sends the story it wrote in one piece. The review tells it of the
change it holds, and from then on answers a page with the story as told —
each step with the piece of the change it shows — until the agent tells
another, which takes its place whole.
"""

from collections.abc import AsyncIterator
from http import HTTPStatus
from pathlib import Path

import pytest
from httpx import AsyncClient

from claude_review.domain.models import FIRST_ROUND
from claude_review.domain.story import Step, Story
from claude_review.presentation.wire.content import ReviewResponse
from claude_review.presentation.wire.refusal import Refusal
from claude_review.presentation.wire.story import LeftOutOfFile, StoryResponse, StoryTakenResponse
from tests.helpers import REVIEW_ROUTE, ReviewFactory, http_client, repository_opening, write_files
from tests.stories import as_the_agent_writes, planted, rows_of, step, story_of

STORY_ROUTE = "/api/story"
SUBMIT_ROUTE = "/api/submit"
RETAKE_ROUTE = "/api/retake"

# What the repository under review has changed since its commit: a line added to a file, and a file added
EDITED_FILE = "initial.txt"
ADDED_FILE = "src/added.py"
THE_CHANGE = {EDITED_FILE: "initial content\nand a line since\n", ADDED_FILE: "def added() -> None:\n    return None\n"}
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
    agent: AsyncClient,
) -> None:
    """The round's work may move the code under a story; what was told is still what was told, and of which round."""
    await tell(agent, WHOLE_STORY)
    told_first = await held_by(agent)

    await agent.post(SUBMIT_ROUTE, json={"threads": [], "body": "One more line, please.", "end": False})
    await agent.post(RETAKE_ROUTE)

    assert await held_by(agent) == told_first
    assert (await tell(agent, WHOLE_STORY)).round == FIRST_ROUND + 1


async def test_telling_a_story_says_the_agent_is_there(agent: AsyncClient) -> None:
    before = ReviewResponse.model_validate_json((await agent.get(REVIEW_ROUTE)).content)

    await tell(agent, WHOLE_STORY)

    after = ReviewResponse.model_validate_json((await agent.get(REVIEW_ROUTE)).content)
    assert (before.answerer_attached, after.answerer_attached) == (False, True)
