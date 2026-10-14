"""E2E: a thread is drawn as a card hung under the line it is about.

The card stands right under its line, as wide as the line less a little at
each side, and points up at the line with a tail. Where a card stands, how
wide it is and whether its tail is drawn are only true in a browser.
"""

from pathlib import Path

import pytest
from playwright.async_api import Locator, Page

from tests.e2e.browsers_loop import in_the_browsers_loop
from tests.e2e.thread_card import TAIL_DRAWN
from tests.helpers import ReviewServers, RunningReview, committed_repository, repository_opening, write_files

# One file, changed on a line, so the first line number the keys reach is in it
CHANGED_FILE = "main.py"
COMMITTED = {CHANGED_FILE: "def hello():\n    return 'hello'\n"}
CHANGED = {CHANGED_FILE: "def hello():\n    return 'hi'\n"}
# Where the left, bottom and right edges of the row a line's number stands in are on screen, in pixels
ROW_EDGES = "(gutter) => { const row = gutter.closest('tr').getBoundingClientRect(); return [row.left, row.bottom, row.right]; }"
# Where the left, top and right edges of an element are on screen, in pixels
EDGES = "(element) => { const box = element.getBoundingClientRect(); return [box.left, box.top, box.right]; }"
# How far a card stands in from each side of its line, and the most it stands under it, as the boards draw them
CARD_INSET = 12
MOST_UNDER_ITS_LINE = 12


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
