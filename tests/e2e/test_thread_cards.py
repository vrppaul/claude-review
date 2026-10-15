"""E2E: a thread is drawn as a card hung under the line it is about.

The card stands right under its line, as wide as the line less a little at
each side, and points up at the line with a tail. Where a card stands, how
wide it is and whether its tail is drawn are only true in a browser.
"""

from pathlib import Path

import pytest
from playwright.async_api import Locator, Page, expect

from tests.e2e.browsers_loop import in_the_browsers_loop
from tests.e2e.folds import CHEVRON, POINTING_DOWN, POINTING_UP, TURN
from tests.e2e.thread_card import CARD_INSET, EDGES, MOST_UNDER_ITS_LINE, TAIL_DRAWN
from tests.helpers import ReviewServers, RunningReview, committed_repository, repository_opening, write_files

# One file, changed on a line, so the first line number the keys reach is in it
CHANGED_FILE = "main.py"
COMMITTED = {CHANGED_FILE: "def hello():\n    return 'hello'\n"}
CHANGED = {CHANGED_FILE: "def hello():\n    return 'hi'\n"}
# Where the left, bottom and right edges of the row a line's number stands in are on screen, in pixels
ROW_EDGES = "(gutter) => { const row = gutter.closest('tr').getBoundingClientRect(); return [row.left, row.bottom, row.right]; }"
# How far apart two things may stand that differ by the edge round one of them, in pixels
AN_EDGE_APART = 1


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    """A repository with one file changed and not committed."""
    committed_repository(tmp_path, COMMITTED)
    write_files(tmp_path, CHANGED)
    return tmp_path


@in_the_browsers_loop
async def review(repository: Path, servers: ReviewServers) -> RunningReview:
    return await servers.start(await repository_opening(repository))


async def _comment_on_the_first_line(page: Page, review: RunningReview) -> Locator:
    """Open the review, put a comment on its first line from the keyboard, and hand back the line's number."""
    await page.goto(review.url)
    await page.get_by_test_id("sidebar").wait_for()
    await page.keyboard.press("j")
    await page.keyboard.press("Enter")
    await page.get_by_test_id("comment-input").wait_for()
    await page.keyboard.type("Name it after the unit")
    await page.keyboard.press("Control+Enter")
    await page.get_by_test_id("thread-card").wait_for()
    return page.get_by_test_id("line-gutter").first


async def test_a_thread_hangs_right_under_its_line_as_wide_as_the_line_less_a_little_at_each_side(
    review: RunningReview, page: Page
) -> None:
    gutter = await _comment_on_the_first_line(page, review)

    row_left, row_bottom, row_right = await gutter.evaluate(ROW_EDGES)
    card_left, card_top, card_right = await page.get_by_test_id("thread-card").evaluate(EDGES)

    assert 0 < card_top - row_bottom <= MOST_UNDER_ITS_LINE
    assert (card_left - row_left, row_right - card_right) == (pytest.approx(CARD_INSET), pytest.approx(CARD_INSET))


async def test_a_thread_under_its_line_points_up_at_it(review: RunningReview, page: Page) -> None:
    await _comment_on_the_first_line(page, review)

    assert await page.get_by_test_id("thread-card").evaluate(TAIL_DRAWN)


async def test_a_comment_being_written_stands_where_its_card_will_as_wide_and_pointing_up_at_its_line(
    review: RunningReview, page: Page
) -> None:
    await page.goto(review.url)
    await page.get_by_test_id("sidebar").wait_for()
    await page.keyboard.press("j")
    await page.keyboard.press("Enter")
    box = page.get_by_test_id("comment-box")
    being_written = await box.evaluate(EDGES)
    await page.keyboard.type("Name it after the unit")
    await page.keyboard.press("Control+Enter")
    await page.get_by_test_id("thread-card").wait_for()

    assert await page.get_by_test_id("thread-card").evaluate(EDGES) == pytest.approx(being_written)


async def test_a_thread_folded_away_is_as_wide_as_its_card_and_its_fold_stays_where_it_was_turned_from_up_to_down(
    review: RunningReview, page: Page
) -> None:
    await _comment_on_the_first_line(page, review)
    card_left, _, card_right = await page.get_by_test_id("thread-card").evaluate(EDGES)
    fold_left, _, fold_right = await page.get_by_test_id("fold-comment").evaluate(EDGES)
    await expect(page.get_by_test_id("fold-comment").locator(CHEVRON)).to_have_css(TURN, POINTING_UP)

    await page.get_by_test_id("fold-comment").click()

    folded_left, _, folded_right = await page.get_by_test_id("folded-thread").evaluate(EDGES)
    unfold_left, _, unfold_right = await page.get_by_test_id("fold-comment").evaluate(EDGES)
    await expect(page.get_by_test_id("fold-comment").locator(CHEVRON)).to_have_css(TURN, POINTING_DOWN)
    assert (folded_left, folded_right) == (pytest.approx(card_left), pytest.approx(card_right))
    # The card's edge is a hair's width round it, the folded line's a mark down its left side alone
    assert (unfold_left, unfold_right) == (
        pytest.approx(fold_left, abs=AN_EDGE_APART),
        pytest.approx(fold_right, abs=AN_EDGE_APART),
    )
