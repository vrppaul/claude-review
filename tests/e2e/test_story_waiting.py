"""E2E: what stands where a story will be while the reader waits for one, in a real browser.

A reader who turned stories on reads the review as its story before there
is one: what they wait on is drawn in its place, and changes under them as
they stop the story, ask for it again, or the agent tells it. Each change
takes away the control that held the keyboard, and the keyboard goes to
what is drawn in its place. Where it lands, and where the words stand in
their area, are only true in a browser.
"""

from pathlib import Path

import pytest
from httpx import AsyncClient
from playwright.async_api import Page, ViewportSize, expect
from pydantic import BaseModel, ConfigDict

from tests.e2e.browsers_loop import in_the_browsers_loop
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

# A window as wide as a laptop's, and one as narrow as a phone's held upright
WIDE: ViewportSize = {"width": 1440, "height": 900}
NARROW: ViewportSize = {"width": 420, "height": 900}
# Where the middle of an element is on screen, in pixels from the left and from the top of the window
MIDDLE_OF = """(element) => {
    const box = element.getBoundingClientRect();
    return { across: box.left + box.width / 2, down: box.top + box.height / 2 };
}"""
# How near two middles stand that are the same: where an edge stands is not a whole number
LESS_THAN_A_PIXEL = 1


class Middle(BaseModel):
    """Where the middle of an element is on screen."""

    model_config = ConfigDict(frozen=True)

    across: float
    down: float


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


async def _wait_for_a_story(page: Page, review: RunningReview) -> None:
    """Open the review, turn stories on behind the gear, and read the review as its story: there is none yet."""
    await page.goto(review.url)
    await page.get_by_test_id("diff-view").wait_for()
    await page.get_by_test_id("settings-toggle").click()
    await page.get_by_test_id("stories").check()
    await page.keyboard.press("Escape")
    await page.get_by_test_id("read-as-story").click()
    await page.get_by_test_id("story-waiting").wait_for()


async def _middle_of(page: Page, test_id: str) -> Middle:
    return Middle.model_validate(await page.get_by_test_id(test_id).evaluate(MIDDLE_OF))


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


async def test_asking_again_with_no_agent_attached_puts_the_keyboard_on_the_words_that_say_so(
    review: RunningReview, page: Page
) -> None:
    """The one button drawn then takes no press: the words hold the keyboard, where the next key starts from."""
    await _wait_for_a_story(page, review)
    async with AsyncClient(base_url=review.url) as another_page:
        await another_page.post(STORY_CANCEL_ROUTE)

    await page.get_by_test_id("write-story-again").press("Enter")

    await expect(page.get_by_test_id("no-agent-to-tell-it")).to_be_focused()


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

    async with AsyncClient(base_url=review.url) as agent:
        await agent.put(STORY_ROUTE, json=as_the_agent_writes(A_STORY))

    await expect(page.get_by_test_id("part-head").first).to_be_focused()


@pytest.mark.parametrize("window", [WIDE, NARROW], ids=["a wide window", "a narrow window"])
async def test_what_the_reader_waits_on_stands_in_the_middle_of_the_storys_area(
    review: RunningReview, page: Page, window: ViewportSize
) -> None:
    await page.set_viewport_size(window)
    await _wait_for_a_story(page, review)

    waited_on = await _middle_of(page, "story-waiting")
    area = await _middle_of(page, "story-view")

    assert abs(waited_on.across - area.across) < LESS_THAN_A_PIXEL
    assert abs(waited_on.down - area.down) < LESS_THAN_A_PIXEL
