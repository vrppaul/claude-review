"""E2E: the panes a reader opens, and the questions the page asks in them, pressed where they open.

Whether a press reaches a control the page placed, and whether the reading
area moves under it, only a browser shows: jsdom lays nothing out.
"""

from pathlib import Path

import pytest
from playwright.async_api import Page, ViewportSize, expect

from tests.e2e.browsers_loop import in_the_browsers_loop
from tests.e2e.page_reads import FOCUSED_TEST_ID, PAGE_SCROLLED_BY, SCROLLED
from tests.helpers import ReviewServers, RunningReview, committed_repository, repository_opening, write_files

CHANGED_FILE = "told.py"
COMMITTED = {CHANGED_FILE: "keep one\nfirst two\n"}
CHANGED = {CHANGED_FILE: "keep one\nchanged two\n"}
# A laptop's screen with the browser's bars and the system's dock taking much of its height
SHORT_LAPTOP: ViewportSize = {"width": 1366, "height": 560}
# The settings pane and the control of the header that opens it
SETTINGS_TOGGLE = "settings-toggle"
SETTINGS_MENU = "settings-menu"
# The help pane, taller than a short window, the control that opens it, and a key its list names
HELP_TOGGLE = "open-help"
HELP_MENU = "help-menu"
KEY_IN_THE_HELP = "shortcut-key"
# How far the reader turns the wheel over the help, in pixels: more than its whole list of keys is long
PAST_THE_HELPS_FOOT = 2_000
# What the reader writes in a comment they save, and in one they leave half written
SAVED_WORDS = "Name it after the unit"
HALF_A_THOUGHT = "Half a thought"
# A file changed on every line, long enough for the reading area to scroll it far under its header; and a line
# deep in it to comment on, by its place among the line numbers drawn
LONG_FILE = "long.py"
LONG_FILE_LINES = 80
DEEP_LINE = 40
# How far under the foot of the file's header a control is scrolled to, and how far its foot stands above the
# foot of the reading area, in pixels: near enough that a question opened its own way would lie under the
# header, or past the area's foot
JUST_UNDER_THE_HEADER = 10
JUST_ABOVE_THE_FOOT = 20
# Scroll the reading area by as much as stands a control's top that far under the foot of a header kept over it
TOP_UNDER = """(area, [control, header, under]) => {
    area.scrollTop += control.getBoundingClientRect().top - (header.getBoundingClientRect().bottom + under);
}"""
# Scroll the reading area by as much as stands a control's foot that far above the area's own foot
FOOT_ABOVE = """(area, [control, above]) => {
    area.scrollTop += control.getBoundingClientRect().bottom - (area.getBoundingClientRect().bottom - above);
}"""


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    """A repository with a change, not committed."""
    committed_repository(tmp_path, COMMITTED)
    write_files(tmp_path, CHANGED)
    return tmp_path


@in_the_browsers_loop
async def review(repository: Path, servers: ReviewServers) -> RunningReview:
    return await servers.start(await repository_opening(repository))


async def _open(page: Page, review: RunningReview) -> None:
    await page.set_viewport_size(SHORT_LAPTOP)
    await page.goto(review.url)
    await page.get_by_test_id("file-section").first.wait_for()


async def test_the_help_reads_to_its_last_key_in_a_short_window_and_leaves_the_page_where_it_is(
    review: RunningReview, page: Page
) -> None:
    await _open(page, review)
    await page.get_by_test_id(HELP_TOGGLE).click()
    help_pane = page.get_by_test_id(HELP_MENU)
    await help_pane.hover()

    await page.mouse.wheel(0, PAST_THE_HELPS_FOOT)

    await expect(help_pane.get_by_test_id(KEY_IN_THE_HELP).last).to_be_in_viewport()
    assert await page.evaluate(PAGE_SCROLLED_BY) == 0


async def _comment_on_the_first_line(page: Page, words: str) -> None:
    """Write a comment on the review's first line from the keyboard, and leave it being written."""
    await page.keyboard.press("j")
    await page.keyboard.press("Enter")
    await page.get_by_test_id("comment-input").wait_for()
    await page.keyboard.type(words)


async def test_the_question_before_a_comment_is_deleted_leaves_the_rest_of_the_page_to_be_pressed(
    review: RunningReview, page: Page
) -> None:
    await _open(page, review)
    await _comment_on_the_first_line(page, SAVED_WORDS)
    await page.keyboard.press("Control+Enter")
    await page.get_by_test_id("delete-comment").click()

    await page.get_by_test_id(SETTINGS_TOGGLE).click()

    await page.get_by_test_id(SETTINGS_MENU).wait_for()
    await page.get_by_test_id("delete-dialog").wait_for(state="detached")


@in_the_browsers_loop
async def long_change(tmp_path: Path, servers: ReviewServers) -> RunningReview:
    """A review of one file changed on every one of its many lines."""
    committed_repository(tmp_path, {LONG_FILE: "".join(f"before = {number}\n" for number in range(LONG_FILE_LINES))})
    write_files(tmp_path, {LONG_FILE: "".join(f"after = {number}\n" for number in range(LONG_FILE_LINES))})
    return await servers.start(await repository_opening(tmp_path))


async def _comment_deep_in_the_file(page: Page, words: str) -> None:
    """Write a comment on a line deep in the long file, and leave it being written."""
    await page.get_by_test_id("line-gutter").nth(DEEP_LINE).click()
    await page.get_by_test_id("comment-input").wait_for()
    await page.keyboard.type(words)


async def test_the_question_before_a_comment_is_discarded_asked_just_under_the_files_header_is_answered_where_it_opens(
    long_change: RunningReview, page: Page
) -> None:
    """Pressed where it opened, its answer is reached without the reading area moving to show it."""
    await _open(page, long_change)
    await _comment_deep_in_the_file(page, HALF_A_THOUGHT)
    area = page.get_by_test_id("diff-view")
    cancel = page.get_by_test_id("cancel-comment")
    await area.evaluate(
        TOP_UNDER,
        [
            await cancel.element_handle(),
            await page.get_by_test_id("file-header").element_handle(),
            JUST_UNDER_THE_HEADER,
        ],
    )
    scrolled_to = await area.evaluate(SCROLLED)
    await cancel.click()

    await page.get_by_test_id("confirm-keep").click()

    await page.get_by_test_id("discard-dialog").wait_for(state="detached")
    assert await area.evaluate(SCROLLED) == scrolled_to


async def _bin_near_the_foot(page: Page, review: RunningReview) -> None:
    """A comment saved deep in the long file, its bin scrolled to stand just above the foot of the reading area."""
    await _open(page, review)
    await _comment_deep_in_the_file(page, SAVED_WORDS)
    await page.keyboard.press("Control+Enter")
    bin_button = page.get_by_test_id("delete-comment")
    await bin_button.wait_for()
    await page.get_by_test_id("diff-view").evaluate(
        FOOT_ABOVE, [await bin_button.element_handle(), JUST_ABOVE_THE_FOOT]
    )


async def test_the_question_before_a_comment_is_deleted_asked_near_the_foot_of_the_reading_area_is_answered_where_it_opens(
    long_change: RunningReview, page: Page
) -> None:
    """Pressed where it opened, its answer is reached without the reading area moving to show it."""
    await _bin_near_the_foot(page, long_change)
    area = page.get_by_test_id("diff-view")
    scrolled_to = await area.evaluate(SCROLLED)
    await page.get_by_test_id("delete-comment").click()

    await page.get_by_test_id("confirm-keep").click()

    await page.get_by_test_id("delete-dialog").wait_for(state="detached")
    assert await area.evaluate(SCROLLED) == scrolled_to


async def test_the_question_taking_the_keyboard_leaves_the_reading_area_where_the_reader_had_it(
    long_change: RunningReview, page: Page
) -> None:
    await _bin_near_the_foot(page, long_change)
    area = page.get_by_test_id("diff-view")
    scrolled_to = await area.evaluate(SCROLLED)

    await page.get_by_test_id("delete-comment").click()

    await page.get_by_test_id("delete-dialog").wait_for()
    assert (await page.evaluate(FOCUSED_TEST_ID), await area.evaluate(SCROLLED)) == ("confirm-keep", scrolled_to)
