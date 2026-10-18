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
from tests.e2e.folds import CHEVRON, CHEVRON_AT_THE_END, POINTING_DOWN, POINTING_UP, TURN
from tests.e2e.laid_out import SHOWN_WHOLE_ACROSS
from tests.e2e.painted import light, on_a_probe, painted
from tests.e2e.thread_card import CARD_INSET, EDGES, MOST_UNDER_ITS_LINE, TAIL_DRAWN
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
# What it decided, which the overview lists one fold away, under "More about this change"
DECISION = "The second line is changed where it stands, not removed and written again."
A_STORY = planted(
    planted(story_of(step(TOLD_FILE, 2, 2)), ("overview", "doubt"), DOUBT),
    ("overview", "decisions"),
    [{"text": DECISION}],
)
# The same change told again, with nothing to doubt
TOLD_AGAIN = story_of(step(TOLD_FILE, 2, 2))
# Where an element's edges stand on screen, in pixels from the top and the left of the window
TOP_OF = "(element) => element.getBoundingClientRect().top"
BOTTOM_OF = "(element) => element.getBoundingClientRect().bottom"
LEFT_OF = "(element) => element.getBoundingClientRect().left"
# Widths the story is read at, in pixels: a wide screen, and a phone's; and a window tall enough for its overview
READING_WIDTHS = [1440, 420]
TALL_ENOUGH = 900
# Whether an element stands clear of every line of words drawn in another, by the boxes of those lines
OVER_NONE_OF_ITS_WORDS = """(words, over) => {
    const lines = document.createRange();
    lines.selectNodeContents(words);
    const box = over.getBoundingClientRect();
    return [...lines.getClientRects()].every(
        (line) => line.right <= box.left || line.left >= box.right || line.bottom <= box.top || line.top >= box.bottom
    );
}"""
# What an element draws inside its edge where it draws nothing
NO_EDGE = "none"
# How strongly an element is drawn on screen: its own opacity and that of everything it stands in, multiplied; and
# the strength of one drawn fully and not at all
DRAWN_STRENGTH = """(element) => {
    let strength = 1;
    for (let node = element; node; node = node.parentElement) strength *= Number(getComputedStyle(node).opacity);
    return strength;
}"""
FULLY_DRAWN = 1
NOT_DRAWN = 0


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


async def _read_as_story_at(page: Page, review: RunningReview, width: int) -> Locator:
    """Open the review in a window this wide, as its story, and hand back the overview's doubt.

    Opened at that width, the page puts away what it would lay over the story there: the tree and the panel.
    """
    await page.set_viewport_size({"width": width, "height": TALL_ENOUGH})
    await page.goto(review.url)
    await page.click('[data-testid="read-as-story"]')
    await page.wait_for_selector('[data-testid="story-piece"]')
    return page.get_by_test_id("overview-doubt")


async def _ask_about(page: Page, block: Locator, words: str) -> None:
    """Ask about a block, and put the words into the review as a thread under it."""
    await block.hover()
    await block.get_by_test_id("ask-about-this").click()
    await page.fill('[data-testid="comment-input"]', words)
    await page.click('[data-testid="save-comment"]')
    await expect(block.get_by_test_id("comment-thread")).to_contain_text(words)


@pytest.mark.parametrize("width", READING_WIDTHS)
async def test_ask_about_this_stands_over_the_top_edge_of_the_block_pointed_at_over_no_word_of_it_or_the_one_above(
    review: RunningReview, page: Page, width: int
) -> None:
    doubt = await _read_as_story_at(page, review, width)
    band = doubt.get_by_test_id("askable-band")
    asking = doubt.get_by_test_id("ask-about-this")
    words = doubt.get_by_test_id("block-words")
    words_above = page.get_by_test_id("overview-done").get_by_test_id("block-words")
    words_top, words_left = await words.evaluate(TOP_OF), await words.evaluate(LEFT_OF)
    assert await asking.evaluate(DRAWN_STRENGTH) == NOT_DRAWN

    await band.hover()

    assert await asking.evaluate(DRAWN_STRENGTH) == FULLY_DRAWN
    assert await asking.evaluate(TOP_OF) < await band.evaluate(TOP_OF)
    assert await words.evaluate(OVER_NONE_OF_ITS_WORDS, await asking.element_handle())
    assert await words_above.evaluate(OVER_NONE_OF_ITS_WORDS, await asking.element_handle())
    assert (await words.evaluate(TOP_OF), await words.evaluate(LEFT_OF)) == (words_top, words_left)


async def test_ask_about_this_is_offered_in_the_readers_colour_on_the_pages_own_ground(
    review: RunningReview, page: Page
) -> None:
    """Asking is the reader's own act, said and edged in their mark, on a ground that hides the words behind it."""
    doubt = await _read_as_story(page, review)

    asking = await painted(doubt.get_by_test_id("ask-about-this"))

    assert (asking.ground, asking.words, asking.border) == (
        await on_a_probe(page, "backgroundColor", "var(--color-base-100)"),
        await on_a_probe(page, "color", "var(--cr-mark-text)"),
        await on_a_probe(page, "borderTopColor", "var(--cr-mark-border)"),
    )


async def test_a_chapters_doubt_pointed_at_is_lit_by_the_pointers_light_with_the_warnings_wash_showing_through(
    review: RunningReview, page: Page
) -> None:
    """Pointed at, the doubt is lit as a block is, by a light that takes no edge and leaves the warning's wash under it."""
    await _read_as_story(page, review)
    doubt = page.get_by_test_id("chapter-doubt-block")
    band = doubt.get_by_test_id("askable-band")

    await band.hover()

    lit = await painted(band)
    assert (lit.laid, lit.ground, lit.edge) == (
        await light(page, "--cr-hover"),
        await on_a_probe(page, "backgroundColor", "transparent"),
        NO_EDGE,
    )
    assert (await painted(doubt.get_by_test_id("askable-frame"))).ground == await on_a_probe(
        page, "backgroundColor", "var(--cr-warning-tint)"
    )
    assert await doubt.get_by_test_id("ask-about-this").evaluate(DRAWN_STRENGTH) == FULLY_DRAWN


@pytest.mark.parametrize("width", READING_WIDTHS)
async def test_ask_about_this_over_a_chapters_why_stands_over_none_of_what_heads_the_chapter(
    review: RunningReview, page: Page, width: int
) -> None:
    await _read_as_story_at(page, review, width)
    why = page.get_by_test_id("chapter-why-block")
    asking = why.get_by_test_id("ask-about-this")

    await why.get_by_test_id("askable-band").hover()

    assert await asking.evaluate(DRAWN_STRENGTH) == FULLY_DRAWN
    chapter = page.get_by_test_id("story-chapter")
    offer = await asking.element_handle()
    assert await chapter.get_by_test_id("part-head").evaluate(OVER_NONE_OF_ITS_WORDS, offer)
    assert await chapter.get_by_test_id("chapter-counts").evaluate(OVER_NONE_OF_ITS_WORDS, offer)


async def test_a_block_with_a_thread_under_it_stays_banded_where_the_reader_neither_points_nor_types(
    review: RunningReview, page: Page
) -> None:
    doubt = await _read_as_story(page, review)
    await _ask_about(page, doubt, "Was it needed?")
    done = page.get_by_test_id("overview-done")

    await page.get_by_test_id("overview-task").get_by_test_id("block-words").click()

    unbanded = (await painted(done.get_by_test_id("askable-band"))).ground
    assert (await painted(doubt.get_by_test_id("askable-band"))).ground != unbanded


async def test_a_block_whose_thread_is_folded_away_is_banded_no_more_than_the_blocks_beside_it(
    review: RunningReview, page: Page
) -> None:
    doubt = await _read_as_story(page, review)
    await _ask_about(page, doubt, "Was it needed?")

    await doubt.get_by_test_id("fold-comment").click()
    await page.get_by_test_id("overview-task").get_by_test_id("block-words").click()

    unbanded = (await painted(page.get_by_test_id("overview-done").get_by_test_id("askable-band"))).ground
    assert (await painted(doubt.get_by_test_id("askable-band"))).ground == unbanded


async def test_what_more_the_overview_says_folds_under_a_chevron_at_the_end_of_its_row_down_while_away_up_while_open(
    review: RunningReview, page: Page
) -> None:
    await _read_as_story(page, review)
    toggle = page.get_by_test_id("story-more-toggle")
    assert await toggle.evaluate(CHEVRON_AT_THE_END)
    await expect(toggle.locator(CHEVRON)).to_have_css(TURN, POINTING_DOWN)

    await toggle.click()

    await expect(toggle.locator(CHEVRON)).to_have_css(TURN, POINTING_UP)


async def test_a_comment_written_on_the_storys_words_stands_in_from_them_as_a_card_stands_in_from_its_line(
    review: RunningReview, page: Page
) -> None:
    doubt = await _read_as_story(page, review)
    await doubt.hover()

    await doubt.get_by_test_id("ask-about-this").click()

    block_left, _, block_right = await doubt.evaluate(EDGES)
    card_left, card_top, card_right = await doubt.get_by_test_id("comment-box").evaluate(EDGES)
    words_end = await doubt.get_by_test_id("askable-band").evaluate(BOTTOM_OF)
    frame_end = await page.get_by_test_id("story-in-short").evaluate(BOTTOM_OF)
    card_end = await doubt.get_by_test_id("comment-box").evaluate(BOTTOM_OF)
    assert (card_left - block_left, block_right - card_right) == (pytest.approx(CARD_INSET), pytest.approx(CARD_INSET))
    assert 0 < card_top - words_end <= MOST_UNDER_ITS_LINE
    assert frame_end - card_end >= CARD_INSET


async def test_a_thread_on_a_chapters_own_words_hangs_below_the_frame_they_stand_in(
    review: RunningReview, page: Page
) -> None:
    await _read_as_story(page, review)
    why = page.get_by_test_id("chapter-why-block")

    await _ask_about(page, why, "Why do these belong together?")

    # The frame holds the words and their band, and ends with them: the thread under them is no part of it
    frame_ends = await why.get_by_test_id("askable-frame").evaluate(BOTTOM_OF)
    assert frame_ends == await why.get_by_test_id("askable-band").evaluate(BOTTOM_OF)


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


async def test_a_thread_on_the_story_picked_in_the_finish_pane_while_the_files_are_read_takes_the_keyboard(
    review: RunningReview, page: Page
) -> None:
    doubt = await _read_as_story(page, review)
    await _ask_about(page, doubt, "Was it needed?")
    await page.click('[data-testid="read-as-files"]')
    await page.click('[data-testid="quick-submit"]')

    await page.click('[data-testid="finish-comment"]')

    await expect(doubt.locator('[data-testid="comment-thread"]:focus')).to_contain_text("Was it needed?")


async def _open_the_lists(page: Page) -> Locator:
    """Open what more the overview says, and hand back the one thing it lists."""
    await page.click('[data-testid="story-more-toggle"]')
    return page.get_by_test_id("overview-item")


async def test_a_thread_on_a_thing_the_overview_lists_is_in_sight_once_the_page_is_loaded_again_and_the_next_thread_key_reaches_it(
    review: RunningReview, page: Page
) -> None:
    await _read_as_story(page, review)
    decision = await _open_the_lists(page)
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
    decision = await _open_the_lists(page)
    await decision.hover()
    await decision.get_by_test_id("ask-about-this").click()
    await page.fill('[data-testid="comment-input"]', "Why in place?")

    await page.reload()

    await expect(decision.get_by_test_id("comment-input")).to_be_visible()


async def test_a_press_on_the_heading_of_the_lists_a_thread_hangs_in_leaves_them_open(
    review: RunningReview, page: Page
) -> None:
    await _read_as_story(page, review)
    decision = await _open_the_lists(page)
    await _ask_about(page, decision, "Why in place?")

    await page.click('[data-testid="story-more-toggle"]')

    await expect(decision.get_by_test_id("comment-thread")).to_be_visible()


async def test_a_comment_on_a_thing_the_overview_lists_put_away_leaves_the_list_open_with_the_keyboard_on_what_offered_it(
    review: RunningReview, page: Page
) -> None:
    await _read_as_story(page, review)
    decision = await _open_the_lists(page)
    await decision.hover()
    await decision.get_by_test_id("ask-about-this").click()

    await page.press('[data-testid="comment-input"]', "Escape")

    await expect(decision.get_by_test_id("ask-about-this")).to_be_focused()


async def test_a_thread_on_words_a_story_told_again_says_nowhere_stands_at_its_head_with_those_words_whole(
    review: RunningReview, page: Page
) -> None:
    doubt = await _read_as_story(page, review)
    await _ask_about(page, doubt, "Was it needed?")

    await _tell(review, TOLD_AGAIN)

    at_the_head = page.get_by_test_id("unplaced-threads")
    await expect(at_the_head).to_contain_text("1 thread on words the story no longer says")
    written_against = at_the_head.get_by_test_id("stale-quote")
    await expect(written_against).to_contain_text(DOUBT)
    assert await written_against.evaluate(SHOWN_WHOLE_ACROSS)


async def test_a_thread_at_the_head_of_the_story_points_at_nothing_above_it(review: RunningReview, page: Page) -> None:
    doubt = await _read_as_story(page, review)
    await _ask_about(page, doubt, "Was it needed?")

    await _tell(review, TOLD_AGAIN)

    assert not await page.get_by_test_id("unplaced-threads").get_by_test_id("thread-card").evaluate(TAIL_DRAWN)


async def test_a_thread_at_the_head_of_the_story_deleted_gives_the_keyboard_to_the_head_of_the_story(
    review: RunningReview, page: Page
) -> None:
    doubt = await _read_as_story(page, review)
    await _ask_about(page, doubt, "Was it needed?")
    await _tell(review, TOLD_AGAIN)
    at_the_head = page.get_by_test_id("unplaced-threads")

    await at_the_head.get_by_test_id("delete-comment").click()
    await page.click('[data-testid="confirm-go-ahead"]')

    await expect(page.get_by_test_id("story-overview").get_by_test_id("part-head")).to_be_focused()
