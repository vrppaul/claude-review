"""E2E: the reader asks about the story's own words, in a real browser.

A block of the agent's words — a line of the overview — offers "Ask about
this" while it is pointed at, floating over its top edge so that no word
moves; what is asked hangs under the block as a thread hangs under a line.
Where the button stands, and where the keyboard goes when what hung under
the block goes, are only true in a browser.
"""

from pathlib import Path

import pytest
from httpx import AsyncClient
from playwright.async_api import Locator, Page, expect

from claude_review.domain.story import Step, Story
from tests.e2e.browsers_loop import in_the_browsers_loop
from tests.helpers import ReviewServers, RunningReview, committed_repository, repository_opening, write_files
from tests.stories import as_the_agent_writes, planted, step, story_of

STORY_ROUTE = "/api/story"

TOLD_FILE = "told.py"
COMMITTED_FILES = {TOLD_FILE: "keep one\nfirst two\nkeep three\n"}
THE_CHANGE = {TOLD_FILE: "keep one\nchanged two\nkeep three\n"}
# A story of the change whose overview says what to doubt, at more length than one line of a thread holds
DOUBT = (
    "Whether the second line needed changing at all, when nothing that reads it changed with it"
    " and every test of the file passed before the change as it passes after it."
)
A_STORY = planted(story_of(step(TOLD_FILE, 2, 2)), ("overview", "doubt"), DOUBT)
# The same change told again, with nothing to doubt
TOLD_AGAIN = story_of(step(TOLD_FILE, 2, 2))
# Where an element's edges stand on screen, in pixels from the top and the left of the window
TOP_OF = "(element) => element.getBoundingClientRect().top"
BOTTOM_OF = "(element) => element.getBoundingClientRect().bottom"
LEFT_OF = "(element) => element.getBoundingClientRect().left"
# The colour an element is laid on
GROUND_OF = "(element) => getComputedStyle(element).backgroundColor"
# Whether an element, and everything in it, shows its contents whole across, with nothing to scroll sideways
NOTHING_SCROLLS_ACROSS = "(element) => [element, ...element.querySelectorAll('*')].every((inside) => inside.scrollWidth <= inside.clientWidth)"
# How strongly an element is drawn, as its style says it, and the strength of one drawn fully and not at all
OPACITY = "opacity"
FULLY_DRAWN = "1"
NOT_DRAWN = "0"


@pytest.fixture
def changed_repo(tmp_path: Path) -> Path:
    """A repository with a change to tell a story of."""
    repo = committed_repository(tmp_path / "repo", COMMITTED_FILES)
    write_files(repo, THE_CHANGE)
    return repo


async def _tell(review: RunningReview, story: Story[Step]) -> None:
    """Tell the review a story of its change, as the agent does."""
    async with AsyncClient(base_url=review.url) as agent:
        await agent.put(STORY_ROUTE, json=as_the_agent_writes(story))


@in_the_browsers_loop
async def review(changed_repo: Path, servers: ReviewServers) -> RunningReview:
    """A review of the change, which the agent has told a story of."""
    started = await servers.start(await repository_opening(changed_repo))
    await _tell(started, A_STORY)
    return started


async def _read_as_story(page: Page, review: RunningReview) -> Locator:
    """Open the review as its story, and hand back the overview's doubt."""
    await page.goto(review.url)
    await page.wait_for_selector('[data-testid="file-item"]')
    await page.click('[data-testid="read-as-story"]')
    return page.get_by_test_id("overview-doubt")


async def _ask_about(page: Page, block: Locator, words: str) -> None:
    """Ask about a block, and put the words into the review as a thread under it."""
    await block.hover()
    await block.get_by_test_id("ask-about-this").click()
    await page.fill('[data-testid="comment-input"]', words)
    await page.click('[data-testid="save-comment"]')
    await expect(block.get_by_test_id("comment-thread")).to_contain_text(words)


async def test_ask_about_this_floats_over_the_top_edge_of_the_block_pointed_at_and_no_word_moves(
    review: RunningReview, page: Page
) -> None:
    doubt = await _read_as_story(page, review)
    band = doubt.get_by_test_id("askable-band")
    asking = doubt.get_by_test_id("ask-about-this")
    words = doubt.get_by_test_id("block-words")
    words_top, words_left = await words.evaluate(TOP_OF), await words.evaluate(LEFT_OF)
    await expect(asking).to_have_css(OPACITY, NOT_DRAWN)

    await band.hover()

    await expect(asking).to_have_css(OPACITY, FULLY_DRAWN)
    assert await asking.evaluate(TOP_OF) < await band.evaluate(TOP_OF) < await asking.evaluate(BOTTOM_OF)
    assert (await words.evaluate(TOP_OF), await words.evaluate(LEFT_OF)) == (words_top, words_left)


async def test_a_block_with_a_thread_under_it_stays_banded_where_the_reader_neither_points_nor_types(
    review: RunningReview, page: Page
) -> None:
    doubt = await _read_as_story(page, review)
    await _ask_about(page, doubt, "Was it needed?")
    done = page.get_by_test_id("overview-done")

    await page.get_by_test_id("overview-task").get_by_test_id("block-words").click()

    unbanded = await done.get_by_test_id("askable-band").evaluate(GROUND_OF)
    assert await doubt.get_by_test_id("askable-band").evaluate(GROUND_OF) != unbanded


async def test_a_thread_on_the_story_deleted_gives_the_keyboard_back_to_what_offered_its_block(
    review: RunningReview, page: Page
) -> None:
    doubt = await _read_as_story(page, review)
    await _ask_about(page, doubt, "Was it needed?")

    await doubt.get_by_test_id("delete-comment").click()
    await page.click('[data-testid="confirm-go-ahead"]')

    await expect(doubt.get_by_test_id("ask-about-this")).to_be_focused()


async def test_a_comment_on_the_story_put_away_gives_the_keyboard_back_to_what_offered_its_block(
    review: RunningReview, page: Page
) -> None:
    doubt = await _read_as_story(page, review)
    await doubt.hover()
    await doubt.get_by_test_id("ask-about-this").click()

    await page.press('[data-testid="comment-input"]', "Escape")

    await expect(doubt.get_by_test_id("ask-about-this")).to_be_focused()


async def test_the_next_thread_key_in_the_story_puts_the_keyboard_on_a_thread_on_its_words(
    review: RunningReview, page: Page
) -> None:
    doubt = await _read_as_story(page, review)
    await _ask_about(page, doubt, "Was it needed?")
    await page.get_by_test_id("overview-task").get_by_test_id("block-words").click()

    await page.keyboard.press("n")

    await expect(doubt.locator('[data-testid="comment-thread"]:focus')).to_contain_text("Was it needed?")


async def test_a_thread_on_words_a_story_told_again_says_nowhere_stands_at_its_head_with_those_words_whole(
    review: RunningReview, page: Page
) -> None:
    doubt = await _read_as_story(page, review)
    await _ask_about(page, doubt, "Was it needed?")

    await _tell(review, TOLD_AGAIN)

    at_the_head = page.get_by_test_id("threads-off-their-lines")
    await expect(at_the_head).to_contain_text("1 thread on words the story no longer says")
    written_against = at_the_head.get_by_test_id("stale-quote")
    await expect(written_against).to_contain_text(DOUBT)
    assert await written_against.evaluate(NOTHING_SCROLLS_ACROSS)


async def test_a_thread_at_the_head_of_the_story_deleted_gives_the_keyboard_to_the_head_of_the_story(
    review: RunningReview, page: Page
) -> None:
    doubt = await _read_as_story(page, review)
    await _ask_about(page, doubt, "Was it needed?")
    await _tell(review, TOLD_AGAIN)
    at_the_head = page.get_by_test_id("threads-off-their-lines")

    await at_the_head.get_by_test_id("delete-comment").click()
    await page.click('[data-testid="confirm-go-ahead"]')

    await expect(page.get_by_test_id("story-overview").get_by_test_id("part-head")).to_be_focused()
