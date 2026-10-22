"""E2E: the reader asks about the story's own words, in a real browser.

A block of the agent's words — a line of the overview — offers "Ask about
this" while it is pointed at or holds the keyboard; what is asked hangs
under the block as a thread hangs under a line. Where the keyboard goes when
what hung under the block goes is held in a browser.
"""

from pathlib import Path

import pytest
from httpx import AsyncClient
from playwright.async_api import Locator, Page, ViewportSize, expect

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
# What it decided, two things, so the overview folds the list to the first one's words until the reader opens it
DECISION = "The second line is changed where it stands, not removed and written again."
SECOND_DECISION = "The first and the third line stay as they were."
# What it left for later: one thing, whose words fit the line its list would fold to in a window of a laptop's width
LEFT_FOR_LATER = "A test that reads the second line back after each round."
A_STORY = planted(
    planted(
        planted(story_of(step(TOLD_FILE, 2, 2)), ("overview", "doubt"), DOUBT),
        ("overview", "decisions"),
        [{"text": DECISION, "chapter": None}, {"text": SECOND_DECISION, "chapter": None}],
    ),
    ("overview", "later"),
    [{"text": LEFT_FOR_LATER, "chapter": None}],
)
# A window as narrow as a phone's, whose story has no room for the words of that one thing on a line
A_PHONE: ViewportSize = {"width": 420, "height": 800}
# The same change told again, with nothing to doubt
TOLD_AGAIN = story_of(step(TOLD_FILE, 2, 2))


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


async def test_a_thread_on_the_story_deleted_gives_the_keyboard_back_to_what_offered_its_block(
    review: RunningReview, page: Page
) -> None:
    doubt = await _read_as_story(page, review)
    await _ask_about(page, doubt, "Was it needed?")

    await doubt.get_by_test_id("turn-menu").click()
    await page.get_by_test_id("delete-turn").click()
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


async def test_a_thread_on_the_story_picked_in_the_finish_pane_while_the_files_are_read_takes_the_keyboard(
    review: RunningReview, page: Page
) -> None:
    doubt = await _read_as_story(page, review)
    await _ask_about(page, doubt, "Was it needed?")
    await page.click('[data-testid="read-as-files"]')
    await page.click('[data-testid="quick-submit"]')

    await page.click('[data-testid="finish-comment"]')

    await expect(doubt.locator('[data-testid="comment-thread"]:focus')).to_contain_text("Was it needed?")


async def _open_the_decisions(page: Page) -> Locator:
    """Open what the overview decided, and hand back the first thing it decided."""
    decided = page.get_by_test_id("overview-list").first
    await decided.get_by_test_id("overview-list-toggle").click()
    return decided.get_by_test_id("overview-item").first


async def test_the_next_key_after_a_list_of_the_overview_is_opened_from_the_keyboard_goes_into_that_list(
    review: RunningReview, page: Page
) -> None:
    await _read_as_story(page, review)
    decided = page.get_by_test_id("overview-list").first
    await decided.get_by_test_id("overview-list-toggle").focus()
    await page.keyboard.press("Enter")

    await page.keyboard.press("Tab")

    await expect(decided.get_by_test_id("overview-item").first.get_by_test_id("ask-about-this")).to_be_focused()


async def test_a_list_of_one_thing_whose_words_fit_its_line_offers_the_question_with_nothing_to_open(
    review: RunningReview, page: Page
) -> None:
    await _read_as_story(page, review)
    left_for_later = page.get_by_test_id("overview-list").last.get_by_test_id("overview-item")
    await left_for_later.hover()

    await left_for_later.get_by_test_id("ask-about-this").click()

    await expect(left_for_later.get_by_test_id("comment-input")).to_be_visible()


async def test_a_list_of_one_thing_folds_to_its_line_once_the_window_is_too_narrow_for_its_words(
    review: RunningReview, page: Page
) -> None:
    await _read_as_story(page, review)
    left_for_later = page.get_by_test_id("overview-list").last
    await expect(left_for_later.get_by_test_id("overview-item")).to_be_visible()

    await page.set_viewport_size(A_PHONE)

    await expect(left_for_later.get_by_test_id("overview-list-toggle")).to_have_attribute("aria-expanded", "false")
    await expect(left_for_later.get_by_test_id("overview-item")).to_have_count(0)


async def test_a_thread_on_a_thing_the_overview_lists_is_in_sight_once_the_page_is_loaded_again_and_the_next_thread_key_reaches_it(
    review: RunningReview, page: Page
) -> None:
    await _read_as_story(page, review)
    decision = await _open_the_decisions(page)
    await _ask_about(page, decision, "Why in place?")

    await page.reload()

    await expect(decision.get_by_test_id("comment-thread")).to_be_visible()
    await page.get_by_test_id("overview-task").get_by_test_id("block-words").click()
    await page.keyboard.press("n")
    await expect(decision.locator('[data-testid="comment-thread"]:focus')).to_contain_text("Why in place?")


async def test_a_comment_being_written_on_a_thing_the_overview_lists_is_in_sight_once_the_page_is_loaded_again(
    review: RunningReview, page: Page
) -> None:
    await _read_as_story(page, review)
    decision = await _open_the_decisions(page)
    await decision.hover()
    await decision.get_by_test_id("ask-about-this").click()
    await page.fill('[data-testid="comment-input"]', "Why in place?")

    await page.reload()

    await expect(decision.get_by_test_id("comment-input")).to_be_visible()


async def test_a_comment_on_a_thing_the_overview_lists_put_away_leaves_the_list_open_with_the_keyboard_on_what_offered_it(
    review: RunningReview, page: Page
) -> None:
    await _read_as_story(page, review)
    decision = await _open_the_decisions(page)
    await decision.hover()
    await decision.get_by_test_id("ask-about-this").click()

    await page.press('[data-testid="comment-input"]', "Escape")

    await expect(decision.get_by_test_id("ask-about-this")).to_be_focused()


async def test_a_thread_at_the_head_of_the_story_deleted_gives_the_keyboard_to_the_head_of_the_story(
    review: RunningReview, page: Page
) -> None:
    doubt = await _read_as_story(page, review)
    await _ask_about(page, doubt, "Was it needed?")
    await _tell(review, TOLD_AGAIN)
    at_the_head = page.get_by_test_id("unplaced-threads")

    await at_the_head.get_by_test_id("turn-menu").click()
    await page.get_by_test_id("delete-turn").click()
    await page.click('[data-testid="confirm-go-ahead"]')

    await expect(page.get_by_test_id("story-overview").get_by_test_id("part-head")).to_be_focused()
