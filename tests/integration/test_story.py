"""A story told of a review's change: taken whole or refused whole, kept by the review, and read by its page.

The agent sends the story it wrote in one piece. The review tells it of the
change it holds, and from then on answers a page with the story as told —
each step with the piece of the change it shows — until the agent tells
another, which takes its place whole. Each time the diff is taken again,
the story follows it, and says where its code changed.

The reader may ask for one. The request waits for an agent as everything
handed over does, the reader may stop it before or after one takes it, and
the review says how the asking stands to every page, open then or later,
until a story is told.
"""

import asyncio
from collections.abc import AsyncIterator, Iterator
from http import HTTPStatus
from pathlib import Path
from typing import override

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from pydantic import TypeAdapter
from starlette.testclient import WebSocketTestSession

from claude_review.domain.interfaces import PageChannel
from claude_review.domain.kept_review import KeptReview
from claude_review.domain.models import FIRST_ROUND, FIRST_TAKE, ReaderSettings
from claude_review.domain.page_events import DiffRetaken, PageEvent
from claude_review.domain.story import Step, Story, StoryHeld
from claude_review.hosting.workspace import ReaderFiles, ReviewWorkspace
from claude_review.presentation.schemas.agent import EventResponse, StoryCancelEvent, StoryRequestEvent, TimeoutEvent
from claude_review.presentation.schemas.content import DiffResponse, ReviewResponse, StoryAsking
from claude_review.presentation.schemas.pushes import StoryAskingPush, StoryPush
from claude_review.presentation.schemas.refusal import Refusal
from claude_review.presentation.schemas.story import (
    CodeMovedOn,
    LeftOutOfFile,
    LineSpan,
    StoryResponse,
    StoryTakenResponse,
)
from claude_review.repositories.git_repository import GitRepository
from claude_review.repositories.image_store import DirectoryImageStore
from claude_review.repositories.json_record_store import JsonRecordStore
from claude_review.repositories.system_clock import SystemClock
from claude_review.services.image_service import REVIEW_IMAGE_QUOTA, ImageService
from claude_review.services.reader_record_service import ReaderRecordService
from claude_review.services.review.content_sources import content_source
from claude_review.services.review.review import Review
from claude_review.services.review.review_lifetime import EndReason
from claude_review.services.review.review_record import ReviewRecord
from claude_review.services.review_opening import ReviewOpening
from tests.helpers import (
    DIFF_ROUTE,
    EVENTS_ROUTE,
    GLANCE_AT_EVENTS,
    REVIEW_ROUTE,
    STORY_REQUEST_ROUTE,
    WAIT_FOR_EVENT,
    FixedClock,
    ReviewFactory,
    files_opening_of,
    http_client,
    next_push,
    one_line_file,
    open_session,
    page_client,
    repository_opening,
    review_facts,
    until_an_agent_waits,
    write_files,
)
from tests.stories import as_the_agent_writes, chapter_of, planted, rows_of, step, story_of, story_of_chapters

STORY_ROUTE = "/api/story"
SUBMIT_ROUTE = "/api/submit"
RETAKE_ROUTE = "/api/retake"
SETTINGS_ROUTE = "/api/settings"
# The base a page asks for to read only what changed since the first round began
SINCE_THE_FIRST_ROUND = "round:1"

# What the repository under review has changed since its commit: a line added to a file, and a file added
EDITED_FILE = "initial.txt"
ADDED_FILE = "src/added.py"
THE_CHANGE = {EDITED_FILE: "initial content\nand a line since\n", ADDED_FILE: "def added() -> None:\n    return None\n"}
# The edited file as a round's work leaves it: the line the story told, said another way
REWORDED_SINCE = "initial content\nand a line reworded since\n"
# The added file as a round's work leaves it: two lines put above it, and its last line rewritten
REWRITTEN_UNDER_TWO_LINES = "import os\nimport sys\ndef added() -> None:\n    return 1\n"
# A file a round's work adds, which no step of a story told before it tells: more is left out
FILE_ADDED_SINCE = {"src/since.py": "def since() -> None:\n    return None\n"}
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
# The same two steps, each in a chapter of its own
A_CHAPTER_TO_EACH = story_of_chapters(chapter_of("the-line", THE_LINE_ADDED), chapter_of("the-file", THE_FILE_ADDED))

# Where the reader stops the story asked for
STORY_CANCEL_ROUTE = "/api/story/cancel"
# Reads what an agent's wait is answered with, as the agent's own command reads it
EVENTS = TypeAdapter[EventResponse](EventResponse)
# When the reader asks for a story, when an agent takes the request, and when the reader asks again
ASKED_AT = 1_791_000_000_000
TAKEN_AT = ASKED_AT + 4_000
ASKED_AGAIN_AT = TAKEN_AT + 60_000
# How the asking stands once the reader has asked, once an agent has taken the request, and once the reader
# has stopped it, after an agent took the request or before any did
ASKED = StoryAsking(asked_at=ASKED_AT, taken_at=None, stopped=False)
TAKEN = StoryAsking(asked_at=ASKED_AT, taken_at=TAKEN_AT, stopped=False)
STOPPED_ONCE_TAKEN = StoryAsking(asked_at=ASKED_AT, taken_at=TAKEN_AT, stopped=True)
STOPPED_UNTAKEN = StoryAsking(asked_at=ASKED_AT, taken_at=None, stopped=True)
# What the pages are told, in order, as each of those happens
ASKED_TAKEN_STOPPED = [ASKED, TAKEN, STOPPED_ONCE_TAKEN]
ASKED_STOPPED = [ASKED, STOPPED_UNTAKEN]


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


async def take_again_after(agent: AsyncClient, repository: Path, work: dict[str, str]) -> None:
    """Send a round, do its work, leaving these files saying this, and take the diff again."""
    await agent.post(SUBMIT_ROUTE, json={"threads": [], "body": "Another word for it, please.", "end": False})
    write_files(repository, work)
    await agent.post(RETAKE_ROUTE)


async def take_again_after_a_round(agent: AsyncClient, repository: Path) -> None:
    """Send a round, do its work on the file the story told, rewording the line its step tells, and take the diff
    again."""
    await take_again_after(agent, repository, {EDITED_FILE: REWORDED_SINCE})


async def test_a_story_told_of_the_change_is_taken_and_summed_up_in_a_line(agent: AsyncClient) -> None:
    taken = await tell(agent, WHOLE_STORY)

    assert taken == StoryTakenResponse(round=FIRST_ROUND, chapters=1, steps=2, left_out=[])


async def test_what_no_step_tells_is_said_to_the_agent_file_by_file(agent: AsyncClient) -> None:
    """So the agent knows what its story leaves the reader to find alone, without asking for the story back."""
    taken = await tell(agent, story_of(THE_LINE_ADDED))

    assert taken.left_out == [LeftOutOfFile(file=ADDED_FILE, changed_lines=2)]


async def test_a_review_nobody_told_a_story_of_or_asked_one_from_holds_neither(agent: AsyncClient) -> None:
    facts = ReviewResponse.model_validate_json((await agent.get(REVIEW_ROUTE)).content)

    assert (await held_by(agent), facts.story_asking) == (StoryResponse(held=None), None)


async def test_a_page_reads_the_story_as_told_each_step_with_the_piece_of_the_change_it_shows(
    agent: AsyncClient,
) -> None:
    await tell(agent, WHOLE_STORY)

    held = (await held_by(agent)).held

    assert held is not None
    assert held.round == FIRST_ROUND
    assert [(told.file, rows_of(told.now.piece)) for told in held.story.chapters[0].steps] == [
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


async def test_a_review_of_no_change_takes_no_story(files_client: AsyncClient) -> None:
    """Files read once, or a conversation: nobody changed them, so there is no change to tell."""
    answered = await files_client.put(STORY_ROUTE, json=as_the_agent_writes(WHOLE_STORY))

    assert answered.status_code == HTTPStatus.NOT_FOUND
    assert await held_by(files_client) == StoryResponse(held=None)


async def test_a_review_of_no_change_says_so_to_whoever_tells_it_a_story(files_client: AsyncClient) -> None:
    """Told why, the agent stops trying: nothing it could write would be a story of this review."""
    answered = await files_client.put(STORY_ROUTE, json=as_the_agent_writes(WHOLE_STORY))

    assert "no change" in Refusal.model_validate_json(answered.content).detail


async def test_a_story_follows_the_diff_taken_again_showing_the_code_as_it_now_stands(
    agent: AsyncClient, tmp_git_repo: Path
) -> None:
    """The round's work reworded the line a step tells: the step shows it as it now stands, marked, and the step
    the round left alone shows what it showed."""
    await tell(agent, WHOLE_STORY)

    await take_again_after_a_round(agent, tmp_git_repo)

    [reworded, untouched] = (await held_by(agent)).held.story.chapters[0].steps
    assert (reworded.file, rows_of(reworded.now.piece), reworded.now.changed_since_told) == (
        EDITED_FILE,
        ["and a line reworded since"],
        True,
    )
    assert (untouched.file, rows_of(untouched.now.piece), untouched.now.changed_since_told) == (
        ADDED_FILE,
        ["def added() -> None:", "    return None"],
        False,
    )


async def test_a_step_moves_with_its_code_as_git_says_and_keeps_its_line_said_another_way(
    agent: AsyncClient, tmp_git_repo: Path
) -> None:
    """Two lines put above it and its last line rewritten: it moves down with its code, and the rewritten line is
    still its own."""
    await tell(agent, WHOLE_STORY)

    await take_again_after(agent, tmp_git_repo, {ADDED_FILE: REWRITTEN_UNDER_TWO_LINES})

    [_, rewritten] = (await held_by(agent)).held.story.chapters[0].steps
    assert (rewritten.now.lines, rows_of(rewritten.now.piece), rewritten.now.changed_since_told) == (
        LineSpan(first=3, last=4),
        ["def added() -> None:", "    return 1"],
        True,
    )


async def test_a_story_followed_says_which_round_told_it_and_in_which_the_code_moved_on(
    agent: AsyncClient, tmp_git_repo: Path
) -> None:
    await tell(agent, WHOLE_STORY)

    await take_again_after_a_round(agent, tmp_git_repo)

    held = (await held_by(agent)).held
    # The line the round reworded is still its step's: no more is left out than when the story was told
    assert (held.round, held.moved_on) == (FIRST_ROUND, CodeMovedOn(round=FIRST_ROUND + 1, left_out=None))
    assert (await tell(agent, WHOLE_STORY)).round == FIRST_ROUND + 1


async def test_a_chapter_a_later_round_changed_counts_its_step_and_the_story_keeps_the_round_it_went_stale_in(
    agent: AsyncClient, tmp_git_repo: Path
) -> None:
    """The story went stale in the round that added a file no step tells; the chapter's step changed a round later.

    The review keeps no round a chapter's steps changed in: a chapter that
    said the story's round as its own would say the wrong one.
    """
    await tell(agent, A_CHAPTER_TO_EACH)

    await take_again_after(agent, tmp_git_repo, FILE_ADDED_SINCE)
    await take_again_after(agent, tmp_git_repo, {ADDED_FILE: REWRITTEN_UNDER_TWO_LINES})

    held = (await held_by(agent)).held
    assert held.moved_on.round == FIRST_ROUND + 1
    assert [chapter.changed_steps for chapter in held.story.chapters] == [0, 1]


async def test_a_story_is_of_the_take_of_the_change_the_review_holds_as_it_is_told(agent: AsyncClient) -> None:
    """A page draws a story's pieces beside threads that hang on line numbers: both must be of one take."""
    await tell(agent, WHOLE_STORY)

    assert (await held_by(agent)).held.take == (await own_diff(agent)).take


async def test_a_story_told_before_the_diff_was_taken_again_is_of_the_take_the_diff_is_now(
    agent: AsyncClient, tmp_git_repo: Path
) -> None:
    """Followed onto it before the pages are told to read the diff again, so its pieces are numbered as threads are."""
    await tell(agent, WHOLE_STORY)

    await take_again_after_a_round(agent, tmp_git_repo)

    assert (await held_by(agent)).held.take == (await own_diff(agent)).take


async def test_a_story_told_after_the_diff_was_taken_again_is_of_the_take_the_diff_is_now(
    agent: AsyncClient, tmp_git_repo: Path
) -> None:
    await tell(agent, WHOLE_STORY)
    await take_again_after_a_round(agent, tmp_git_repo)

    await tell(agent, story_of(THE_FILE_ADDED))

    assert (await held_by(agent)).held.take == (await own_diff(agent)).take


async def test_a_review_opened_again_before_it_is_finished_holds_its_story_on_the_code_as_it_now_stands(
    reviews: ReviewFactory, tmp_git_repo: Path
) -> None:
    """Stopped under its reader and opened again on the same change, it is the same review: the story cost tokens once.

    Followed from the story as told, through the trees the review kept, onto
    the code the round's work left, and said to have moved on in the round
    the review had reached, before any page could tell it so.
    """
    write_files(tmp_git_repo, THE_CHANGE)
    opening = await repository_opening(tmp_git_repo)
    async with http_client(reviews.app(opening)) as before:
        await tell(before, WHOLE_STORY)
        await before.post(SUBMIT_ROUTE, json={"threads": [], "body": "Another word for it, please.", "end": False})
    write_files(tmp_git_repo, {EDITED_FILE: REWORDED_SINCE})

    async with http_client(reviews.app(opening)) as again:
        held = (await held_by(again)).held
        facts = ReviewResponse.model_validate_json((await again.get(REVIEW_ROUTE)).content)

    assert rows_of(held.story.chapters[0].steps[0].now.piece) == ["and a line reworded since"]
    assert (held.round, held.moved_on) == (FIRST_ROUND, CodeMovedOn(round=FIRST_ROUND + 1, left_out=None))
    assert (facts.round, facts.story_asking) == (FIRST_ROUND + 1, None)


async def test_a_story_told_as_its_review_is_stopped_under_its_reader_is_held_once_it_is_opened_again(
    reviews: ReviewFactory, opened_on_the_change: ReviewOpening
) -> None:
    """Ctrl+C lets a telling already under way finish: it cost the agent's tokens, and the review is not finished."""
    stopped = reviews.hosted(opened_on_the_change)
    async with http_client(stopped.app):
        stopped.review.lifetime.end(EndReason.STOPPED)
        await stopped.review.tell_story(WHOLE_STORY)

    async with http_client(reviews.app(opened_on_the_change)) as again:
        held = (await held_by(again)).held

    assert held is not None


async def test_a_story_asked_for_in_a_review_is_asked_for_again_once_it_is_opened_again(
    reviews: ReviewFactory, opened_on_the_change: ReviewOpening
) -> None:
    """No agent took it before the review stopped: the review still wants it."""
    async with http_client(reviews.app(opened_on_the_change)) as before:
        await before.post(STORY_REQUEST_ROUTE)

    async with http_client(reviews.app(opened_on_the_change)) as again:
        asking = ReviewResponse.model_validate_json((await again.get(REVIEW_ROUTE)).content).story_asking

    assert asking is not None
    assert (asking.taken_at, asking.stopped) == (None, False)


async def test_a_story_the_reader_stopped_is_not_asked_for_once_its_review_is_opened_again_whatever_they_chose(
    reviews: ReviewFactory, opened_on_the_change: ReviewOpening
) -> None:
    """Every story written as each review opens is a choice for the next review: the stop stands in this one."""
    async with http_client(reviews.app(opened_on_the_change)) as before:
        await before.put(SETTINGS_ROUTE, json={"story_writing": "as_the_review_opens"})
        await before.post(STORY_REQUEST_ROUTE)
        await before.post(STORY_CANCEL_ROUTE)

    async with http_client(reviews.app(opened_on_the_change)) as again:
        asking = ReviewResponse.model_validate_json((await again.get(REVIEW_ROUTE)).content).story_asking

    assert asking is None


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


class PageReadingTheStory(PageChannel):
    """Pages that read the story the review holds the moment they are told anything, as a page told of a push does."""

    def __init__(self) -> None:
        # The review they read it from, once it is made: it is made with them
        self.review: Review | None = None
        # Each kind of event told, with the story held as it was told
        self.read: list[tuple[type[PageEvent], StoryHeld | None]] = []

    @override
    def tell(self, event: PageEvent) -> None:
        self.read.append((type(event), self.review.story_held()))


@pytest.fixture
async def page_reading_the_story(
    workspace: ReviewWorkspace, reader_files: ReaderFiles, tmp_git_repo: Path
) -> PageReadingTheStory:
    """The pages of a review of the repository's change, put together as `host_review` puts one, and opened.

    Put together here, not by `host_review`: the broadcast `host_review` makes
    queues what it tells for each page's socket, and these pages must read
    the story at the moment they are told.
    """
    write_files(tmp_git_repo, THE_CHANGE)
    page = PageReadingTheStory()
    opening, clock = await repository_opening(tmp_git_repo), SystemClock()
    page.review = Review(
        content_source(opening, repository=GitRepository(objects=workspace.objects), clock=clock),
        page=page,
        clock=clock,
        images=ImageService(DirectoryImageStore(workspace.images), REVIEW_IMAGE_QUOTA),
        record=ReviewRecord(
            JsonRecordStore(workspace.record, KeptReview),
            settings=ReaderRecordService(JsonRecordStore(reader_files.settings, ReaderSettings), ReaderSettings),
        ),
    )
    await page.review.open()
    return page


async def test_a_page_told_the_diff_was_taken_again_reads_the_story_already_followed_onto_it(
    page_reading_the_story: PageReadingTheStory, tmp_git_repo: Path
) -> None:
    """Followed before the pages are told: a page that reads the diff, then the story, reads both of one take."""
    review = page_reading_the_story.review
    await review.tell_story(WHOLE_STORY)
    write_files(tmp_git_repo, {EDITED_FILE: REWORDED_SINCE})

    await review.retake()

    [*_, (told, held)] = page_reading_the_story.read
    assert (told, held) == (DiffRetaken, review.story_held())


async def test_where_the_review_stands_says_how_the_readers_asking_for_a_story_stands(review: Review) -> None:
    """Read in one piece with the rest of where it stands, as a page opening reads it."""
    await review.ask_for_story()

    asking = review.standing().story_asking

    assert asking is not None
    assert (asking.taken_at, asking.stopped) == (None, False)


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

    await review.submit(threads=[], body="One more line, please.", ends=False)

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


async def test_a_review_of_no_change_says_it_takes_no_story(files_client: AsyncClient) -> None:
    facts = ReviewResponse.model_validate_json((await files_client.get(REVIEW_ROUTE)).content)

    assert facts.takes_a_story is False


async def test_a_review_of_no_change_is_read_at_the_take_it_was_made_with(files_client: AsyncClient) -> None:
    """Nothing takes it again, so the take its page reads is the first."""
    assert (await own_diff(files_client)).take == FIRST_TAKE


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


@pytest.fixture
def clock() -> FixedClock:
    """The clock of the review a story is asked from, at the moment the reader asks: a test moves it on by hand."""
    return FixedClock(ASKED_AT)


@pytest.fixture
def page_of_the_change(
    reviews: ReviewFactory, opened_on_the_change: ReviewOpening, clock: FixedClock
) -> Iterator[TestClient]:
    """The page of a review of the repository's change, which a test speaks through as the reader and as the agent."""
    with page_client(reviews.app(opened_on_the_change, clock=clock)) as review_page:
        yield review_page


def agent_waits(review: TestClient) -> EventResponse:
    """What an agent's wait is handed next: only a glance, so a review with nothing for it says so at once."""
    return EVENTS.validate_json(review.post(EVENTS_ROUTE, params=GLANCE_AT_EVENTS).content)


def story_read(review: TestClient) -> StoryResponse:
    """The story the review holds, as a page reads it."""
    return StoryResponse.model_validate_json(review.get(STORY_ROUTE).content)


def asking_read(review: TestClient) -> StoryAsking | None:
    """How the reader's asking for a story stands, as a page reads it with the review's facts."""
    return review_facts(review).story_asking


def taken_by_an_agent(review: TestClient, clock: FixedClock) -> None:
    """Have the reader ask for a story, and an agent's wait take the request a few seconds later."""
    review.post(STORY_REQUEST_ROUTE)
    clock.moment = TAKEN_AT
    agent_waits(review)


def next_askings(socket: WebSocketTestSession, how_many: int) -> list[StoryAsking | None]:
    """How the asking stands each of the next few times a page is told, in the order it is told."""
    return [next_push(socket, StoryAskingPush).asking for _ in range(how_many)]


async def test_a_story_the_reader_asks_for_is_handed_to_an_agent_that_waits(agent: AsyncClient) -> None:
    waiting = asyncio.ensure_future(agent.post(EVENTS_ROUTE, params=WAIT_FOR_EVENT))
    await until_an_agent_waits(agent)

    await agent.post(STORY_REQUEST_ROUTE)

    assert EVENTS.validate_json((await waiting).content) == StoryRequestEvent(stale=None)


def test_a_story_stopped_after_an_agent_took_the_request_tells_the_agent_to_stop(
    page_of_the_change: TestClient, clock: FixedClock
) -> None:
    taken_by_an_agent(page_of_the_change, clock)

    page_of_the_change.post(STORY_CANCEL_ROUTE)

    assert agent_waits(page_of_the_change) == StoryCancelEvent()


def test_a_story_stopped_twice_tells_the_agent_once(page_of_the_change: TestClient, clock: FixedClock) -> None:
    taken_by_an_agent(page_of_the_change, clock)

    page_of_the_change.post(STORY_CANCEL_ROUTE)
    page_of_the_change.post(STORY_CANCEL_ROUTE)

    assert [agent_waits(page_of_the_change), agent_waits(page_of_the_change)] == [StoryCancelEvent(), TimeoutEvent()]


def test_stopping_a_story_nobody_asked_for_is_no_refusal_and_tells_no_agent(page_of_the_change: TestClient) -> None:
    answered = page_of_the_change.post(STORY_CANCEL_ROUTE)

    assert answered.status_code == HTTPStatus.NO_CONTENT
    assert agent_waits(page_of_the_change) == TimeoutEvent()


def test_every_page_is_told_when_a_story_was_asked_for_when_an_agent_took_the_request_and_that_it_was_stopped(
    page_of_the_change: TestClient, clock: FixedClock
) -> None:
    """Told as facts, each as it happens: a page waiting for a story draws them, and asks nothing."""
    with open_session(page_of_the_change) as socket:
        taken_by_an_agent(page_of_the_change, clock)
        page_of_the_change.post(STORY_CANCEL_ROUTE)

        told = next_askings(socket, len(ASKED_TAKEN_STOPPED))

    assert told == ASKED_TAKEN_STOPPED


def test_a_story_asked_for_twice_is_told_to_the_pages_once(page_of_the_change: TestClient) -> None:
    with open_session(page_of_the_change) as socket:
        page_of_the_change.post(STORY_REQUEST_ROUTE)
        page_of_the_change.post(STORY_REQUEST_ROUTE)
        page_of_the_change.post(STORY_CANCEL_ROUTE)

        told = next_askings(socket, len(ASKED_STOPPED))

    assert told == ASKED_STOPPED


def test_every_page_is_told_a_story_was_told_and_then_that_it_ended_the_asking(page_of_the_change: TestClient) -> None:
    """The story first: a page that waited never holds, between the two, a story moved on that nobody is asked for."""
    with open_session(page_of_the_change) as socket:
        page_of_the_change.post(STORY_REQUEST_ROUTE)
        next_push(socket, StoryAskingPush)

        page_of_the_change.put(STORY_ROUTE, json=as_the_agent_writes(WHOLE_STORY))

        # An asking told before the story would be passed over here, and none would come after it
        next_push(socket, StoryPush)
        told = next_push(socket, StoryAskingPush)

    assert told.asking is None


def test_a_story_asked_for_again_after_it_was_stopped_is_asked_anew(
    page_of_the_change: TestClient, clock: FixedClock
) -> None:
    taken_by_an_agent(page_of_the_change, clock)
    page_of_the_change.post(STORY_CANCEL_ROUTE)
    clock.moment = ASKED_AGAIN_AT

    page_of_the_change.post(STORY_REQUEST_ROUTE)

    assert asking_read(page_of_the_change) == StoryAsking(asked_at=ASKED_AGAIN_AT, taken_at=None, stopped=False)


def test_a_story_asked_for_again_after_it_was_stopped_reaches_the_agent_after_the_word_to_stop(
    page_of_the_change: TestClient, clock: FixedClock
) -> None:
    """In the order the reader said them: an agent that stops, then starts, ends up writing."""
    taken_by_an_agent(page_of_the_change, clock)
    page_of_the_change.post(STORY_CANCEL_ROUTE)

    page_of_the_change.post(STORY_REQUEST_ROUTE)

    assert [agent_waits(page_of_the_change), agent_waits(page_of_the_change)] == [
        StoryCancelEvent(),
        StoryRequestEvent(stale=None),
    ]


def test_a_story_told_after_the_reader_stopped_it_is_held_all_the_same(
    page_of_the_change: TestClient, clock: FixedClock
) -> None:
    """The agent had written it by then: thrown away, it would have been paid for and never read."""
    taken_by_an_agent(page_of_the_change, clock)
    page_of_the_change.post(STORY_CANCEL_ROUTE)

    page_of_the_change.put(STORY_ROUTE, json=as_the_agent_writes(WHOLE_STORY))

    assert story_read(page_of_the_change).held is not None


def test_a_story_told_before_the_agent_heard_it_was_stopped_leaves_nothing_to_stop(
    page_of_the_change: TestClient, clock: FixedClock
) -> None:
    taken_by_an_agent(page_of_the_change, clock)
    page_of_the_change.post(STORY_CANCEL_ROUTE)

    page_of_the_change.put(STORY_ROUTE, json=as_the_agent_writes(WHOLE_STORY))

    assert agent_waits(page_of_the_change) == TimeoutEvent()


def test_a_story_refused_leaves_the_asking_for_it_as_it_was(page_of_the_change: TestClient, clock: FixedClock) -> None:
    """The agent mends the story and sends it again: the reader is still waiting for it."""
    taken_by_an_agent(page_of_the_change, clock)
    awaited = asking_read(page_of_the_change)

    page_of_the_change.put(STORY_ROUTE, json=as_the_agent_writes(planted(WHOLE_STORY, ("title",), "")))

    assert asking_read(page_of_the_change) == awaited


def test_a_review_of_no_change_refuses_a_story_asked_for(reviews: ReviewFactory) -> None:
    """Asked all the same, it would leave a reader waiting for a story no agent could tell."""
    with page_client(reviews.app(files_opening_of([one_line_file()]))) as page_of_files:
        answered = page_of_files.post(STORY_REQUEST_ROUTE)

    assert answered.status_code == HTTPStatus.NOT_FOUND
    assert "no change" in Refusal.model_validate_json(answered.content).detail
