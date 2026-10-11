"""E2E: the review on a narrow screen — a laptop's, or a wide one zoomed in.

The diff is what is reviewed, so the side columns give their width up to it
and, below a breakpoint, lie over it; the header wraps rather than cut its
controls off. Where a box ends up on the screen is the browser's alone: jsdom
lays nothing out.
"""

from pathlib import Path

import pytest
from playwright.async_api import FloatRect, Locator, Page

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
# How far, in pixels, a box may stand past another: rounding, not overlap
WITHIN_ROUNDING = 1
# What a file's path is read across at the least: half the diff, not a sliver beside the header's controls
PATH_SHARE = 0.5


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    """A repository with a file of a long path and a short one, both changed."""
    committed_repository(tmp_path, COMMITTED)
    write_files(tmp_path, CHANGED)
    return tmp_path


@pytest.fixture
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


# The width a box takes when told to be as wide as the diff's least width, in pixels
LEAST_DIFF_WIDTH = """() => {
    const probe = document.createElement('div');
    probe.style.width = 'var(--cr-diff-least-width)';
    document.body.append(probe);
    const width = probe.getBoundingClientRect().width;
    probe.remove();
    return width;
}"""


async def _least_diff_width(page: Page) -> float:
    """The width the diff is never squeezed below, as the stylesheet's token says."""
    least = await page.evaluate(LEAST_DIFF_WIDTH)
    assert least > 0, "the stylesheet names no least width for the diff"
    return least


async def test_on_a_laptop_the_columns_stand_beside_a_readable_diff_and_every_viewed_box_is_in_it(
    review: RunningReview, page: Page
) -> None:
    await _open_with_the_panel(page, review, LAPTOP)

    tree = await _box(page.get_by_test_id("sidebar"))
    diff = await _box(page.get_by_test_id("diff-view"))
    panel = await _box(page.get_by_test_id("agent-panel"))
    # Side by side, none over another, and the diff no narrower than it reads at
    assert tree["x"] + tree["width"] <= diff["x"] + WITHIN_ROUNDING
    assert diff["x"] + diff["width"] <= panel["x"] + WITHIN_ROUNDING
    assert diff["width"] >= await _least_diff_width(page) - WITHIN_ROUNDING
    # A header longer than the diff is wide wraps: its Viewed box stays inside the diff, not under the panel,
    # and the path is read across the diff rather than squeezed beside the controls
    for viewed in await page.get_by_test_id("viewed-toggle").locator("..").all():
        box = await _box(viewed)
        assert box["x"] + box["width"] <= diff["x"] + diff["width"] + WITHIN_ROUNDING
    path = await _box(page.get_by_test_id("file-heading").filter(has_text=LONG_PATH))
    assert path["width"] >= diff["width"] * PATH_SHARE


async def test_zoomed_in_the_header_keeps_every_control_and_the_columns_lie_over_the_diff(
    review: RunningReview, page: Page
) -> None:
    await _open_with_the_panel(page, review, ZOOMED)

    # Every control of the header is on the screen, on one line: the row wraps instead of cutting
    # the last ones off or squeezing a chip's words onto lines of their own
    help_chip = await _box(page.get_by_test_id("open-help"))
    for control in ("quick-submit", "settings-toggle", "toggle-panel", "open-help", "base-picker"):
        box = await _box(page.get_by_test_id(control))
        assert box["x"] >= 0
        assert box["x"] + box["width"] <= ZOOMED["width"] + WITHIN_ROUNDING, f"{control} is cut off"
    assert (await _box(page.get_by_test_id("base-picker")))["height"] <= help_chip["height"] + WITHIN_ROUNDING
    # Nothing is wider than the screen
    assert await page.evaluate("document.documentElement.scrollWidth") <= ZOOMED["width"]

    # The tree and the panel lie over the diff, which keeps the screen's width under them
    diff = await _box(page.get_by_test_id("diff-view"))
    tree = await _box(page.get_by_test_id("sidebar"))
    panel = await _box(page.get_by_test_id("agent-panel"))
    assert tree["x"] + tree["width"] > diff["x"]
    assert panel["x"] < diff["x"] + diff["width"]
    assert diff["width"] >= ZOOMED["width"] - WITHIN_ROUNDING

    # Put away, they leave the whole diff to be read
    await page.get_by_test_id("close-panel").click()
    await page.get_by_test_id("hide-sidebar").click()
    rail = await _box(page.get_by_test_id("show-sidebar"))
    diff = await _box(page.get_by_test_id("diff-view"))
    assert diff["x"] >= rail["x"] + rail["width"] - WITHIN_ROUNDING
    assert diff["x"] + diff["width"] <= ZOOMED["width"] + WITHIN_ROUNDING
