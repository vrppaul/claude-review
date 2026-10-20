"""E2E: a reader asks for a story and waits for it, in a real browser.

Story in the header asks before the first story is written, in a dialog
that holds the keyboard and gives it back. A reader who turned stories on
reads the review as its story before there is one: what they wait on is
drawn in its place, and changes under them as they stop the story, ask for
it again, or the agent tells it. Each change takes away the control that
held the keyboard, and the keyboard goes to what is drawn in its place. A
story told while they read the files is offered under the switch, and
takes the keyboard from nothing. Where the keyboard lands is only true in a
browser.
"""

from pathlib import Path

import pytest
from httpx import AsyncClient
from playwright.async_api import Page, ViewportSize, expect
from pydantic import BaseModel, ConfigDict

from tests.e2e.browsers_loop import in_the_browsers_loop
from tests.e2e.page_reads import FOCUSED_TEST_ID
from tests.helpers import (
    EVENTS_ROUTE,
    GLANCE_AT_EVENTS,
    STORY_CANCEL_ROUTE,
    STORY_ROUTE,
    ReviewServers,
    RunningReview,
    committed_repository,
    repository_opening,
    write_files,
)
from tests.stories import as_the_agent_writes, step, story_of

CHANGED_FILE = "told.py"
COMMITTED_FILES = {CHANGED_FILE: "keep one\nfirst two\nkeep three\n"}
# The change under review, and the story an agent tells of it: its one changed line
THE_CHANGE = {CHANGED_FILE: "keep one\nchanged two\nkeep three\n"}
A_STORY = story_of(step(CHANGED_FILE, 2, 2))

# A window as wide as a laptop's
WIDE: ViewportSize = {"width": 1440, "height": 900}
# How long the note of a story's arrival stands before it puts itself away, in milliseconds, as the page has it
# (`PassingNote.svelte`): the page's clock is run on by as much, and no test waits it out
NOTE_STANDS_FOR_MS = 4_000


class Answered(BaseModel):
    """A way the question asked before stories are turned on is answered from the keyboard, and what is read after."""

    model_config = ConfigDict(frozen=True)

    how: str
    keys: tuple[str, ...]
    then_on_screen: str


# The question opens with the keyboard on the way to turn stories on; the way to put it off comes next
ANSWERS_BY_KEY = [
    Answered(how="stories turned on", keys=("Enter",), then_on_screen="story-view"),
    Answered(how="not now", keys=("Shift+Tab", "Enter"), then_on_screen="diff-view"),
    Answered(how="Escape", keys=("Escape",), then_on_screen="diff-view"),
]
# What Tab puts the keyboard on, press by press, from the way to turn stories on, the last answer: nothing of the
# page while the keyboard is on the browser's own controls, the other answer, and the way on again
ROUND_THE_QUESTION = [None, "stories-not-now", "turn-on-stories"]
# A corner of the window, which the question stands in the middle of: a press there is a press outside it
BESIDE_THE_QUESTION = (5, 5)


@pytest.fixture
def changed_repo(tmp_path: Path) -> Path:
    """A repository with a change a story can be told of."""
    repo = committed_repository(tmp_path / "repo", COMMITTED_FILES)
    write_files(repo, THE_CHANGE)
    return repo


@in_the_browsers_loop
async def review(changed_repo: Path, servers: ReviewServers) -> RunningReview:
    """A review of the change, which no agent has told a story of."""
    return await servers.start(await repository_opening(changed_repo))


async def _an_agent_attaches(review: RunningReview) -> None:
    """An agent looks for what the reader handed over, and takes it: the review counts it attached from then on."""
    async with AsyncClient(base_url=review.url) as agent:
        await agent.post(EVENTS_ROUTE, params=GLANCE_AT_EVENTS)


async def _the_agent_tells_the_story(review: RunningReview) -> None:
    async with AsyncClient(base_url=review.url) as agent:
        await agent.put(STORY_ROUTE, json=as_the_agent_writes(A_STORY))


async def _open(page: Page, review: RunningReview) -> None:
    """Open the review: a reader new to it reads it by its files."""
    await page.goto(review.url)
    await page.get_by_test_id("diff-view").wait_for()


async def _open_with_stories_on(page: Page, review: RunningReview) -> None:
    """Open the review and turn stories on behind the gear: the agent is asked for a story, and the files stay."""
    await _open(page, review)
    await page.get_by_test_id("settings-toggle").click()
    await page.get_by_test_id("stories").check()
    await page.keyboard.press("Escape")


async def _wait_for_a_story(page: Page, review: RunningReview) -> None:
    """Open the review with stories on, and read it as its story: there is none yet."""
    await _open_with_stories_on(page, review)
    await page.get_by_test_id("read-as-story").click()
    await page.get_by_test_id("story-waiting").wait_for()


async def _ask_to_read_the_story(page: Page, review: RunningReview) -> None:
    """Open the review with stories off, and press Story from the keyboard: the reader is asked first."""
    await _open(page, review)
    await page.get_by_test_id("read-as-story").press("Enter")
    await page.get_by_test_id("story-opt-in").wait_for()


async def test_stopping_the_story_puts_the_keyboard_on_the_way_to_ask_for_it_again(
    review: RunningReview, page: Page
) -> None:
    await _an_agent_attaches(review)
    await _wait_for_a_story(page, review)

    await page.get_by_test_id("stop-writing").press("Enter")

    await expect(page.get_by_test_id("write-story-again")).to_be_focused()


async def test_asking_for_the_story_again_puts_the_keyboard_on_the_way_to_the_files_meanwhile(
    review: RunningReview, page: Page
) -> None:
    await _an_agent_attaches(review)
    await _wait_for_a_story(page, review)
    await page.get_by_test_id("stop-writing").press("Enter")

    await page.get_by_test_id("write-story-again").press("Enter")

    await expect(page.get_by_test_id("read-files-meanwhile")).to_be_focused()


async def test_asking_again_with_no_agent_attached_puts_the_keyboard_on_the_way_to_the_files_meanwhile(
    review: RunningReview, page: Page
) -> None:
    await _wait_for_a_story(page, review)
    async with AsyncClient(base_url=review.url) as another_page:
        await another_page.post(STORY_CANCEL_ROUTE)

    await page.get_by_test_id("write-story-again").press("Enter")

    await expect(page.get_by_test_id("read-files-meanwhile")).to_be_focused()


async def test_reading_the_files_meanwhile_puts_the_keyboard_on_the_files_in_the_header(
    review: RunningReview, page: Page
) -> None:
    await _an_agent_attaches(review)
    await _wait_for_a_story(page, review)

    await page.get_by_test_id("read-files-meanwhile").press("Enter")

    await expect(page.get_by_test_id("diff-view")).to_be_visible()
    await expect(page.get_by_test_id("read-as-files")).to_be_focused()


async def test_a_story_told_under_the_keyboard_puts_the_keyboard_on_its_head(review: RunningReview, page: Page) -> None:
    await _an_agent_attaches(review)
    await _wait_for_a_story(page, review)
    await page.get_by_test_id("read-files-meanwhile").focus()

    await _the_agent_tells_the_story(review)

    await expect(page.get_by_test_id("part-head").first).to_be_focused()


async def test_the_question_before_stories_opens_with_the_keyboard_on_turning_them_on(
    review: RunningReview, page: Page
) -> None:
    await _ask_to_read_the_story(page, review)

    await expect(page.get_by_test_id("turn-on-stories")).to_be_focused()


async def test_the_question_before_stories_holds_the_keyboard_until_it_is_answered(
    review: RunningReview, page: Page
) -> None:
    """Tab goes out to what is the browser's own, to the other answer, and back to the way on: never to the page."""
    await _ask_to_read_the_story(page, review)

    held_the_keyboard = []
    for _ in ROUND_THE_QUESTION:
        await page.keyboard.press("Tab")
        held_the_keyboard.append(await page.evaluate(FOCUSED_TEST_ID))

    assert held_the_keyboard == ROUND_THE_QUESTION


@pytest.mark.parametrize("answered", ANSWERS_BY_KEY, ids=lambda answered: answered.how)
async def test_the_question_before_stories_gives_the_keyboard_back_to_story_however_it_is_answered(
    review: RunningReview, page: Page, answered: Answered
) -> None:
    await _ask_to_read_the_story(page, review)

    for key in answered.keys:
        await page.keyboard.press(key)

    await page.get_by_test_id("story-opt-in").wait_for(state="detached")
    await expect(page.get_by_test_id(answered.then_on_screen)).to_be_visible()
    await expect(page.get_by_test_id("read-as-story")).to_be_focused()


async def test_a_press_outside_the_question_is_not_now_and_gives_the_keyboard_back_to_story(
    review: RunningReview, page: Page
) -> None:
    await _ask_to_read_the_story(page, review)

    await page.mouse.click(*BESIDE_THE_QUESTION)

    await page.get_by_test_id("story-opt-in").wait_for(state="detached")
    await expect(page.get_by_test_id("diff-view")).to_be_visible()
    await expect(page.get_by_test_id("read-as-story")).to_be_focused()


async def test_a_story_told_while_a_comment_is_written_leaves_the_keyboard_in_the_comment(
    review: RunningReview, page: Page
) -> None:
    await _an_agent_attaches(review)
    await _open_with_stories_on(page, review)
    await page.get_by_test_id("line-gutter").first.press("Enter")
    await page.get_by_test_id("comment-input").wait_for()
    await page.keyboard.type("Half a thought")

    await _the_agent_tells_the_story(review)
    await page.get_by_test_id("story-ready").wait_for()
    await page.keyboard.type(", and the rest")

    await expect(page.get_by_test_id("comment-input")).to_be_focused()
    await expect(page.get_by_test_id("comment-input")).to_have_value("Half a thought, and the rest")
    await expect(page.get_by_test_id("diff-view")).to_be_visible()


async def test_the_note_of_a_storys_arrival_closed_from_the_keyboard_gives_the_keyboard_to_story_in_the_header(
    review: RunningReview, page: Page
) -> None:
    await _an_agent_attaches(review)
    await _open_with_stories_on(page, review)
    await _the_agent_tells_the_story(review)

    await page.get_by_test_id("story-ready-close").press("Enter")

    await page.get_by_test_id("story-ready").wait_for(state="detached")
    await expect(page.get_by_test_id("read-as-story")).to_be_focused()


async def test_the_note_of_a_storys_arrival_going_by_itself_gives_the_keyboard_it_held_to_story_in_the_header(
    review: RunningReview, page: Page
) -> None:
    await page.clock.install()
    await _an_agent_attaches(review)
    await _open_with_stories_on(page, review)
    await _the_agent_tells_the_story(review)
    await page.get_by_test_id("open-story").focus()

    await page.clock.fast_forward(NOTE_STANDS_FOR_MS)

    await page.get_by_test_id("story-ready").wait_for(state="detached")
    await expect(page.get_by_test_id("read-as-story")).to_be_focused()


async def test_the_note_of_a_storys_arrival_goes_by_itself_for_a_reader_who_asked_for_less_motion(
    review: RunningReview, page: Page
) -> None:
    """Its bar does not run for them, and the note goes all the same: its time is not the bar's."""
    await page.emulate_media(reduced_motion="reduce")
    await page.clock.install()
    await _an_agent_attaches(review)
    await _open_with_stories_on(page, review)
    await _the_agent_tells_the_story(review)
    await page.get_by_test_id("story-ready").wait_for()

    await page.clock.fast_forward(NOTE_STANDS_FOR_MS)

    await page.get_by_test_id("story-ready").wait_for(state="detached")
    await expect(page.get_by_test_id("segment-unread")).to_be_visible()


async def test_what_the_note_of_a_storys_arrival_stood_over_takes_a_press_once_the_note_is_put_away(
    review: RunningReview, page: Page
) -> None:
    """The note stands over the head of the first file: its fold is pressed where the note was."""
    await page.set_viewport_size(WIDE)
    await _an_agent_attaches(review)
    await _open_with_stories_on(page, review)
    await _the_agent_tells_the_story(review)
    await page.get_by_test_id("story-ready").wait_for()

    await page.get_by_test_id("story-ready-close").click()
    await page.get_by_test_id("collapse-file").first.click()

    await page.get_by_test_id("raw-view").first.wait_for(state="detached")
    await expect(page.get_by_test_id("segment-unread")).to_be_visible()


async def test_opening_a_story_from_the_note_of_its_arrival_puts_the_keyboard_on_story_in_the_header(
    review: RunningReview, page: Page
) -> None:
    await _an_agent_attaches(review)
    await _open_with_stories_on(page, review)
    await _the_agent_tells_the_story(review)

    await page.get_by_test_id("open-story").press("Enter")

    await expect(page.get_by_test_id("story-chapter")).to_be_visible()
    await expect(page.get_by_test_id("read-as-story")).to_be_focused()
