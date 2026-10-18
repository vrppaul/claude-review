"""E2E: the panes a reader opens, and the modals the page asks in: one look, inside the window, headed alike.

Where a pane stands, how large it is drawn and what it is painted with are
the browser's to work out: jsdom lays nothing out and applies no stylesheet.
"""

from pathlib import Path

import pytest
from playwright.async_api import FloatRect, Page
from pydantic import BaseModel, ConfigDict

from claude_review.hosting.workspace import ReaderFiles
from tests.e2e.browsers_loop import in_the_browsers_loop
from tests.e2e.painted import on_a_probe, painted
from tests.helpers import ReviewServers, RunningReview, committed_repository, repository_opening, write_files

CHANGED_FILE = "told.py"
COMMITTED = {CHANGED_FILE: "keep one\nfirst two\n"}
CHANGED = {CHANGED_FILE: "keep one\nchanged two\n"}
# A laptop's screen with the browser's bars and the system's dock taking much of its height, and a phone's
SHORT_LAPTOP = {"width": 1366, "height": 560}
PHONE = {"width": 420, "height": 800}
# A window narrower than a pane and the room it keeps from the window's edges
NARROWEST = {"width": 360, "height": 800}
WINDOWS = [SHORT_LAPTOP, PHONE]
# How far, in pixels, a box may stand past another: rounding, not overlap
WITHIN_ROUNDING = 1
# Whether an element stands whole inside the window, within a pixel's rounding: the page moves a pane in once the
# window it is in has been resized, which the browser tells it of after the resize
STANDS_INSIDE = """(element) => {
    const box = element.getBoundingClientRect();
    return box.left >= -1 && box.top >= -1 && box.right <= innerWidth + 1 && box.bottom <= innerHeight + 1;
}"""
# How much taller than its window the page is: none, as it never scrolls
PAGE_OVERFLOW = "document.scrollingElement.scrollHeight - innerHeight"
# Every heading inside an element, by the size its words are drawn at, in pixels
HEADING_SIZES = "(pane) => [...pane.querySelectorAll('h1, h2, h3, h4, h5, h6')].map((heading) => parseFloat(getComputedStyle(heading).fontSize))"
# The width of a pane of rows (Help, Settings, a list to pick from), in pixels: 20rem
MEDIUM_PANE = 320
# What the browser writes after a length in pixels
PIXELS = "px"


class Pane(BaseModel):
    """A pane the reader opens from a control of the header, by the test ids of both."""

    model_config = ConfigDict(frozen=True)

    control: str
    pane: str


SETTINGS = Pane(control="settings-toggle", pane="settings-menu")
HELP = Pane(control="open-help", pane="help-menu")
FINISH = Pane(control="quick-submit", pane="finish-review")
BASES = Pane(control="base-picker", pane="base-list")
# Every pane the header opens in a review of a change no thread has been answered in
FROM_THE_HEADER = [SETTINGS, HELP, FINISH, BASES]


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    """A repository with a change a story can be told of, not committed."""
    committed_repository(tmp_path, COMMITTED)
    write_files(tmp_path, CHANGED)
    return tmp_path


@in_the_browsers_loop
async def review(repository: Path, servers: ReviewServers) -> RunningReview:
    return await servers.start(await repository_opening(repository))


async def _open(page: Page, review: RunningReview, window: dict[str, int]) -> None:
    await page.set_viewport_size(window)
    await page.goto(review.url)
    await page.get_by_test_id("file-section").first.wait_for()


async def _opened(page: Page, pane: Pane) -> FloatRect:
    """Open a pane from its control, and say where its box stands."""
    await page.get_by_test_id(pane.control).click()
    box = await page.get_by_test_id(pane.pane).bounding_box()
    assert box is not None, f"{pane.pane} is not laid out"
    return box


def _inside(box: FloatRect, window: dict[str, int]) -> bool:
    return all(
        [
            box["x"] >= -WITHIN_ROUNDING,
            box["y"] >= -WITHIN_ROUNDING,
            box["x"] + box["width"] <= window["width"] + WITHIN_ROUNDING,
            box["y"] + box["height"] <= window["height"] + WITHIN_ROUNDING,
        ]
    )


@pytest.mark.parametrize("window", WINDOWS, ids=["short-laptop", "phone"])
@pytest.mark.parametrize("pane", FROM_THE_HEADER, ids=[pane.pane for pane in FROM_THE_HEADER])
async def test_a_pane_opened_from_the_header_stands_whole_inside_the_window_and_the_page_never_scrolls(
    review: RunningReview, page: Page, window: dict[str, int], pane: Pane
) -> None:
    await _open(page, review, window)

    box = await _opened(page, pane)

    assert _inside(box, window), box
    assert await page.evaluate(PAGE_OVERFLOW) == 0


async def test_storys_introduction_keeps_its_width_and_moves_in_to_stand_inside_a_window_made_narrow_under_it(
    review: RunningReview, reader_files: ReaderFiles, page: Page
) -> None:
    reader_files.guide.unlink()
    await page.goto(review.url)
    await page.get_by_test_id("guide-not-now").click()
    introduction = page.get_by_test_id("story-introduction")
    await introduction.wait_for()

    await page.set_viewport_size(NARROWEST)
    await page.wait_for_function(STANDS_INSIDE, arg=await introduction.element_handle())

    box = await introduction.bounding_box()
    assert box is not None
    assert (box["width"], _inside(box, NARROWEST)) == (MEDIUM_PANE, True)


async def test_every_pane_and_the_question_asked_before_a_story_is_drawn_on_one_ground_edge_corner_and_lift(
    review: RunningReview, page: Page
) -> None:
    await _open(page, review, SHORT_LAPTOP)
    looks = []
    for pane in FROM_THE_HEADER:
        await _opened(page, pane)
        looks.append(await painted(page.get_by_test_id(pane.pane)))
        await page.keyboard.press("Escape")
    await page.get_by_test_id("read-as-story").click()
    looks.append(await painted(page.get_by_test_id("story-opt-in")))

    one_look = (
        await on_a_probe(page, "backgroundColor", "var(--color-base-200)"),
        await on_a_probe(page, "borderTopColor", "var(--cr-pane-edge)"),
        await on_a_probe(page, "borderTopLeftRadius", "var(--radius-box)"),
        await on_a_probe(page, "boxShadow", "var(--cr-shadow-raised)"),
    )
    assert [(look.ground, look.border, look.radius, look.edge) for look in looks] == [one_look] * len(looks)


async def test_every_pane_the_header_opens_is_headed_by_its_name_at_one_size_beside_the_way_to_close_it(
    review: RunningReview, page: Page
) -> None:
    await _open(page, review, SHORT_LAPTOP)
    heads = []
    for pane in FROM_THE_HEADER:
        await _opened(page, pane)
        heading = await painted(page.get_by_test_id(f"{pane.pane}-heading"))
        await page.get_by_test_id(f"{pane.pane}-close").click()
        await page.get_by_test_id(pane.pane).wait_for(state="detached")
        heads.append((heading.size, heading.weight))

    the_head = (await on_a_probe(page, "fontSize", "var(--text-sm)"), "600")
    assert heads == [the_head] * len(FROM_THE_HEADER)


async def test_no_heading_inside_a_pane_is_larger_than_the_pane_is_headed_with(
    review: RunningReview, page: Page
) -> None:
    await _open(page, review, SHORT_LAPTOP)
    await _opened(page, HELP)

    headed = (await painted(page.get_by_test_id(f"{HELP.pane}-heading"))).size
    sizes = await page.get_by_test_id(HELP.pane).evaluate(HEADING_SIZES)

    assert max(sizes) == float(headed.removesuffix(PIXELS)), sizes
