"""E2E: Ctrl+click on a name in the code opens the pane of where it is defined and used.

Which character the pointer stands on is the browser's caret under it,
which only a browser lays out to say; what a pane shows of what it holds,
and what moves as the keyboard walks it, only a browser scrolls.
"""

from pathlib import Path

import pytest
from playwright.async_api import Locator, Page, ViewportSize, expect

from tests.e2e.agent_commands import as_the_agent
from tests.e2e.browsers_loop import in_the_browsers_loop
from tests.e2e.page_reads import FOCUSED_ELEMENT, SCROLLED
from tests.helpers import ReviewServers, RunningReview, committed_repository, repository_opening, write_files

FLAGS = "src/flags.py"
PANE = "src/pane.py"
# A file the change does not touch, which calls the function more times than the pane lists at first
MENU = "src/menu.py"
NAME = "shown"
# The line the change writes, which starts with a call of the function a file it does not touch defines
USING_IT = "shown()"
# A point over the line's first letters, past the room its cell keeps before its code, in pixels
ON_THE_FIRST_LETTERS = {"x": 14, "y": 8}
# The line that defines the function, its number, a point over the name on it and a reach past the name, in pixels
DEFINING = "def shown"
DEFINING_LINE_NUMBER = "1"
ON_THE_DEFINED_NAME = {"x": 50, "y": 8}
PAST_THE_DEFINED_NAME = {"x": 120, "y": 8}
# The words the reader selected
SELECTED_WORDS = "() => getSelection().toString()"
# How many times the file the change does not touch calls the function
CALLS_UNTOUCHED = 9
# How many lines the change writes before the call, so the call stands low in a short window; and after it, so
# the reading area has far to scroll
LINES_BEFORE = 14
LINES_AFTER = 60
# A window narrow and short enough that the pane holds less than all it lists
SMALL_WINDOW: ViewportSize = {"width": 900, "height": 560}
# A window in which the agent's panel stands beside the reading area, and the pane, as wide as it opens, reaches
# past the area's edge once the panel has taken its room
WINDOW_THE_PANEL_NARROWS: ViewportSize = {"width": 1200, "height": 560}
# What the agent says, which opens its panel
WHAT_THE_AGENT_SAYS = "The tests pass."
# How much of what holds the keyboard the reader sees, in sight inside the pane: all of it
WHOLE = 1
# The ways a reader walks with Tab: to the definition, to the uses the pane lists at first, and on to Show more
TABS_THROUGH_THE_PANE = 7
# Out of the pane from the first way in it: on past Show more and the ways to the change's import and call, its
# last stop, or back past its close
TABS_OUT_OF_THE_PANE = TABS_THROUGH_THE_PANE + 3
TABS_BACK_OUT_OF_THE_PANE = 2
# The number of the line the change's call stands on: after the import, a blank line and the lines before it
PRESSED_LINE_NUMBER = str(LINES_BEFORE + 3)


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    """A change that calls a function defined in a file it leaves as it was, and called often in another."""
    untouched_calls = "".join(f"{USING_IT}\n" for _ in range(CALLS_UNTOUCHED))
    root = committed_repository(
        tmp_path / "repo",
        {
            FLAGS: "def shown() -> bool:\n    return True\n",
            MENU: f"from src.flags import shown\n\n{untouched_calls}",
            PANE: "\n",
        },
    )
    lines_before = "".join(f"before_{number} = {number}\n" for number in range(LINES_BEFORE))
    lines_after = "".join(f"after_{number} = {number}\n" for number in range(LINES_AFTER))
    write_files(root, {PANE: f"from src.flags import shown\n\n{lines_before}{USING_IT}\n{lines_after}"})
    return root


@in_the_browsers_loop
async def review(repository: Path, servers: ReviewServers) -> RunningReview:
    return await servers.start(await repository_opening(repository))


async def _press_the_call(page: Page) -> None:
    """Ctrl+click on the name the change's call starts with."""
    await (
        page.get_by_test_id("line-code")
        .filter(has_text=USING_IT)
        .first.click(modifiers=["Control"], position=ON_THE_FIRST_LETTERS)
    )


async def test_ctrl_click_on_a_name_in_the_code_opens_where_it_is_defined_and_used(
    review: RunningReview, page: Page
) -> None:
    await page.goto(review.url)

    await _press_the_call(page)

    pane = page.get_by_test_id("name-lookup")
    await expect(pane.get_by_test_id("name-lookup-heading")).to_have_text(NAME)
    await expect(pane.get_by_test_id("name-defined")).to_contain_text(FLAGS)


async def test_ctrl_click_on_a_name_whose_pane_was_closed_opens_it_again(review: RunningReview, page: Page) -> None:
    await page.goto(review.url)
    await _press_the_call(page)
    await page.keyboard.press("Escape")
    await expect(page.get_by_test_id("name-lookup")).to_have_count(0)

    await _press_the_call(page)

    await expect(page.get_by_test_id("name-lookup").get_by_test_id("name-lookup-heading")).to_have_text(NAME)


async def test_the_way_holding_the_keyboard_stays_in_sight_as_the_agents_panel_opens_beside_the_pane(
    review: RunningReview, page: Page
) -> None:
    await page.set_viewport_size(WINDOW_THE_PANEL_NARROWS)
    await page.goto(review.url)
    await _press_the_call(page)
    await expect(page.locator(FOCUSED_ELEMENT)).to_have_text("Go to symbol")

    await as_the_agent(review, "say", WHAT_THE_AGENT_SAYS)

    await expect(page.get_by_test_id("agent-panel")).to_contain_text(WHAT_THE_AGENT_SAYS)
    await expect(page.locator(FOCUSED_ELEMENT)).to_be_in_viewport(ratio=WHOLE)


async def test_tab_walks_the_ways_to_a_names_places_in_sight_in_its_pane_and_leaves_the_reading_area_still(
    review: RunningReview, page: Page
) -> None:
    await page.set_viewport_size(SMALL_WINDOW)
    await page.goto(review.url)
    await _press_the_call(page)
    await expect(page.locator(FOCUSED_ELEMENT)).to_have_text("Go to symbol")
    area = page.get_by_test_id("diff-view")
    scrolled_at_first = await area.evaluate(SCROLLED)

    await expect(page.locator(FOCUSED_ELEMENT)).to_be_in_viewport(ratio=WHOLE)
    for _ in range(TABS_THROUGH_THE_PANE):
        await page.keyboard.press("Tab")
        await expect(page.locator(FOCUSED_ELEMENT)).to_be_in_viewport(ratio=WHOLE)

    await expect(page.locator(FOCUSED_ELEMENT)).to_have_text("Show 4 more")
    assert await area.evaluate(SCROLLED) == scrolled_at_first


@pytest.mark.parametrize(
    ("key", "presses"),
    [("Shift+Tab", TABS_BACK_OUT_OF_THE_PANE), ("Tab", TABS_OUT_OF_THE_PANE)],
)
async def test_tab_out_of_the_pane_closes_it_and_puts_the_keyboard_back_on_the_line_pressed(
    review: RunningReview, page: Page, key: str, presses: int
) -> None:
    await page.set_viewport_size(SMALL_WINDOW)
    await page.goto(review.url)
    await _press_the_call(page)
    await expect(page.locator(FOCUSED_ELEMENT)).to_have_text("Go to symbol")
    area = page.get_by_test_id("diff-view")
    scrolled_at_first = await area.evaluate(SCROLLED)

    for _ in range(presses):
        await page.keyboard.press(key)

    await expect(page.get_by_test_id("name-lookup")).to_have_count(0)
    await expect(page.locator(FOCUSED_ELEMENT)).to_have_text(PRESSED_LINE_NUMBER)
    assert await area.evaluate(SCROLLED) == scrolled_at_first


async def _arrive_at_the_definition(page: Page, review: RunningReview) -> Locator:
    """Go from the change's call to where the function is defined, and hand over that line's code."""
    await page.goto(review.url)
    await _press_the_call(page)
    await page.get_by_test_id("name-defined").get_by_test_id("go-to-symbol").click()
    defining = page.get_by_test_id("line-code").filter(has_text=DEFINING)
    await expect(page.locator(FOCUSED_ELEMENT)).to_have_text(DEFINING_LINE_NUMBER)
    return defining


async def test_the_first_ctrl_click_on_the_line_arrived_at_opens_where_its_name_is_defined_and_used(
    review: RunningReview, page: Page
) -> None:
    defining = await _arrive_at_the_definition(page, review)

    await defining.click(modifiers=["Control"], position=ON_THE_DEFINED_NAME)

    await expect(page.get_by_test_id("name-lookup").get_by_test_id("name-lookup-heading")).to_have_text(NAME)


async def test_a_drag_over_the_line_arrived_at_selects_its_words(review: RunningReview, page: Page) -> None:
    defining = await _arrive_at_the_definition(page, review)

    await defining.hover(position=ON_THE_FIRST_LETTERS)
    await page.mouse.down()
    await defining.hover(position=PAST_THE_DEFINED_NAME)
    await page.mouse.up()

    assert NAME in await page.evaluate(SELECTED_WORDS)
