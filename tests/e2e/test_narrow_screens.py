"""E2E: the review on a narrow screen — a laptop's, or a wide one zoomed in.

The diff is what is reviewed, so the side columns give their width up to it
and, below a breakpoint, lie over it; the header wraps rather than cut its
controls off. Where a box ends up on the screen is the browser's alone: jsdom
lays nothing out.
"""

from pathlib import Path

import pytest
from playwright.async_api import FloatRect, Locator, Page

from tests.e2e.browsers_loop import in_the_browsers_loop
from tests.helpers import ReviewServers, RunningReview, committed_repository, repository_opening, write_files

# A file whose header is long: its path alone is wider than the diff on a laptop's screen, and as
# Markdown it carries the choice of how it is shown as well
LONG_PATH = "docs/claude_review/presentation/wire/very/deeply/nested/folder/a_rather_long_page_name.md"
SHORT_PATH = "b.py"
COMMITTED = {LONG_PATH: "first = 1\nsecond = 2\n", SHORT_PATH: "value = 1\n"}
CHANGED = {LONG_PATH: "first = 10\nsecond = 2\n", SHORT_PATH: "value = 2\n"}
# A laptop's screen, which holds the tree, the diff and the panel side by side
LAPTOP = {"width": 1024, "height": 768}
# A wide screen zoomed to twice its size: too narrow to stand a column beside the diff
ZOOMED = {"width": 640, "height": 400}
# A phone's screen: narrower than the diff reads at, even before the rail of the tree put away stands beside it
PHONE = {"width": 420, "height": 800}
# How far, in pixels, a box may stand past another: rounding, not overlap
WITHIN_ROUNDING = 1


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    """A repository with a file of a long path and a short one, both changed."""
    committed_repository(tmp_path, COMMITTED)
    write_files(tmp_path, CHANGED)
    return tmp_path


@in_the_browsers_loop
async def review(repository: Path, servers: ReviewServers) -> RunningReview:
    return await servers.start(await repository_opening(repository))


async def _box(element: Locator) -> FloatRect:
    box = await element.bounding_box()
    assert box is not None, "the element is not laid out"
    return box


async def _open_with_the_panel(page: Page, review: RunningReview, screen: dict[str, int]) -> None:
    """The review on a screen of this size, the agent panel opened beside the diff."""
    await page.set_viewport_size(screen)
    await page.goto(review.url)
    await page.get_by_test_id("file-section").first.wait_for()
    await page.get_by_test_id("toggle-panel").click()
    await page.get_by_test_id("agent-panel").wait_for()


async def test_on_a_laptop_every_viewed_box_stands_in_the_diff_and_none_under_the_panel(
    review: RunningReview, page: Page
) -> None:
    """A header longer than the diff is wide wraps: its Viewed box is never pushed under the panel beside it."""
    await _open_with_the_panel(page, review, LAPTOP)

    diff = await _box(page.get_by_test_id("diff-view"))

    for viewed in await page.get_by_test_id("viewed-toggle").locator("..").all():
        box = await _box(viewed)
        assert box["x"] + box["width"] <= diff["x"] + diff["width"] + WITHIN_ROUNDING


async def test_zoomed_in_the_review_opens_on_the_diff_alone_and_the_toggles_lay_the_columns_over_it(
    review: RunningReview, page: Page
) -> None:
    await page.set_viewport_size(ZOOMED)
    await page.goto(review.url)
    await page.get_by_test_id("file-section").first.wait_for()

    # Opened, nothing lies over the diff: the tree is put away to its rail, and the panel is shut
    assert await page.get_by_test_id("sidebar").count() == 0
    assert await page.get_by_test_id("agent-panel").count() == 0
    rail = await _box(page.get_by_test_id("show-sidebar"))
    diff = await _box(page.get_by_test_id("diff-view"))
    assert diff["x"] >= rail["x"] + rail["width"] - WITHIN_ROUNDING
    assert diff["x"] + diff["width"] <= ZOOMED["width"] + WITHIN_ROUNDING

    # The toggles bring each column, lying over the diff, which keeps the screen's width under them
    await page.get_by_test_id("show-sidebar").click()
    await page.get_by_test_id("toggle-panel").click()
    await page.get_by_test_id("agent-panel").wait_for()
    diff = await _box(page.get_by_test_id("diff-view"))
    tree = await _box(page.get_by_test_id("sidebar"))
    panel = await _box(page.get_by_test_id("agent-panel"))
    assert tree["x"] + tree["width"] > diff["x"]
    assert panel["x"] < diff["x"] + diff["width"]
    assert diff["width"] >= ZOOMED["width"] - WITHIN_ROUNDING

    # Every control of the header is on the screen: the row wraps instead of cutting the last ones off
    for control in ("quick-submit", "settings-toggle", "toggle-panel", "open-help", "base-picker"):
        box = await _box(page.get_by_test_id(control))
        assert box["x"] >= 0
        assert box["x"] + box["width"] <= ZOOMED["width"] + WITHIN_ROUNDING, f"{control} is cut off"
    # Nothing is wider than the screen
    assert await page.evaluate("document.documentElement.scrollWidth") <= ZOOMED["width"]

    # Put away again, they leave the whole diff to be read
    await page.get_by_test_id("close-panel").click()
    await page.get_by_test_id("hide-sidebar").click()
    rail = await _box(page.get_by_test_id("show-sidebar"))
    diff = await _box(page.get_by_test_id("diff-view"))
    assert diff["x"] >= rail["x"] + rail["width"] - WITHIN_ROUNDING
    assert diff["x"] + diff["width"] <= ZOOMED["width"] + WITHIN_ROUNDING


async def test_on_a_phone_the_diff_takes_what_the_rail_leaves_and_the_page_is_no_wider_than_the_screen(
    review: RunningReview, page: Page
) -> None:
    """Narrower than it reads at, the diff stands beside the tree's rail, not under it nor past the screen's edge."""
    await page.set_viewport_size(PHONE)
    await page.goto(review.url)
    await page.get_by_test_id("file-section").first.wait_for()

    rail = await _box(page.get_by_test_id("show-sidebar"))
    diff = await _box(page.get_by_test_id("diff-view"))
    assert diff["x"] >= rail["x"] + rail["width"] - WITHIN_ROUNDING
    assert await page.evaluate("document.documentElement.scrollWidth") == PHONE["width"]
