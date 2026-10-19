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
# How far a pane stands from the control it points at, at the most, in pixels: the room its arrow takes, half
# the diagonal of a 10 px square, and a pixel's rounding
ARROWS_ROOM = 8
# Which element holds the keyboard, by its test id
FOCUSED_TEST_ID = "document.activeElement?.dataset.testid"
# More changed files than a short window's tree shows at once, each changed on its one line
LONG_TREE = [f"src/part_{number:02}.py" for number in range(40)]
BEFORE = "value = 1\n"
AFTER = "value = 2\n"
# How far the tree is scrolled down, in pixels, and whether an element has moved up from where it stood
SCROLLED_BY = 400
SCROLLED_ABOVE = "([element, top]) => element.getBoundingClientRect().top < top"
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
# Whether an element is what the reader sees at its middle: nothing is drawn over it there, nothing clips it
SEEN_AT_ITS_MIDDLE = """(element) => {
    const box = element.getBoundingClientRect();
    return element.contains(document.elementFromPoint((box.left + box.right) / 2, (box.top + box.bottom) / 2));
}"""
# How far a reading area has scrolled, in pixels
SCROLLED = "(area) => area.scrollTop"
# A question's two answers, by their test ids
ANSWERS = ("confirm-keep", "confirm-go-ahead")


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


async def _comment_on_the_first_line(page: Page, words: str) -> None:
    """Write a comment on the review's first line from the keyboard, and leave it being written."""
    await page.keyboard.press("j")
    await page.keyboard.press("Enter")
    await page.get_by_test_id("comment-input").wait_for()
    await page.keyboard.type(words)


async def _boxes(page: Page, control: str, question: str) -> tuple[FloatRect, FloatRect]:
    """Where a control stands, and the question it opened."""
    control_box = await page.get_by_test_id(control).bounding_box()
    question_box = await page.get_by_test_id(question).bounding_box()
    assert control_box is not None
    assert question_box is not None
    return control_box, question_box


async def test_the_question_before_a_comment_is_deleted_hangs_under_the_bin_that_asked_it(
    review: RunningReview, page: Page
) -> None:
    await _open(page, review, SHORT_LAPTOP)
    await _comment_on_the_first_line(page, "Name it after the unit")
    await page.keyboard.press("Control+Enter")

    await page.get_by_test_id("delete-comment").click()

    bin_box, question = await _boxes(page, "delete-comment", "delete-dialog")
    below_by = question["y"] - (bin_box["y"] + bin_box["height"])
    ends_apart = abs(question["x"] + question["width"] - (bin_box["x"] + bin_box["width"]))
    assert (0 <= below_by <= ARROWS_ROOM, ends_apart <= WITHIN_ROUNDING, _inside(question, SHORT_LAPTOP)) == (
        True,
        True,
        True,
    ), (bin_box, question)


async def test_the_question_before_a_comment_is_deleted_leaves_the_rest_of_the_page_to_be_pressed(
    review: RunningReview, page: Page
) -> None:
    await _open(page, review, SHORT_LAPTOP)
    await _comment_on_the_first_line(page, "Name it after the unit")
    await page.keyboard.press("Control+Enter")
    await page.get_by_test_id("delete-comment").click()

    await page.get_by_test_id(SETTINGS.control).click()

    await page.get_by_test_id(SETTINGS.pane).wait_for()
    await page.get_by_test_id("delete-dialog").wait_for(state="detached")


async def test_keeping_a_comment_the_question_asked_about_gives_the_keyboard_back_to_the_bin(
    review: RunningReview, page: Page
) -> None:
    await _open(page, review, SHORT_LAPTOP)
    await _comment_on_the_first_line(page, "Name it after the unit")
    await page.keyboard.press("Control+Enter")
    await page.get_by_test_id("delete-comment").focus()
    await page.keyboard.press("Enter")
    asked_on = await page.evaluate(FOCUSED_TEST_ID)

    await page.keyboard.press("Enter")

    await page.get_by_test_id("delete-dialog").wait_for(state="detached")
    assert (asked_on, await page.evaluate(FOCUSED_TEST_ID)) == ("confirm-keep", "delete-comment")


async def test_the_question_before_a_comment_is_discarded_hangs_over_the_cancel_that_asked_it(
    review: RunningReview, page: Page
) -> None:
    await _open(page, review, SHORT_LAPTOP)
    await _comment_on_the_first_line(page, "Half a thought")

    await page.get_by_test_id("cancel-comment").click()

    cancel, question = await _boxes(page, "cancel-comment", "discard-dialog")
    above_by = cancel["y"] - (question["y"] + question["height"])
    ends_apart = abs(question["x"] + question["width"] - (cancel["x"] + cancel["width"]))
    assert (0 <= above_by <= ARROWS_ROOM, ends_apart <= WITHIN_ROUNDING) == (True, True), (cancel, question)


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


async def _seen_whole(page: Page, question: str) -> bool:
    """Whether a question stands whole in what is seen of the reading area, under its file's header, and the
    middle of each of its answers is the answer: nothing lies over it, nothing cuts it off."""
    area = await page.get_by_test_id("diff-view").bounding_box()
    header = await page.get_by_test_id("file-header").bounding_box()
    asked = await page.get_by_test_id(question).bounding_box()
    assert area is not None
    assert header is not None
    assert asked is not None
    answers_seen = [await page.get_by_test_id(answer).evaluate(SEEN_AT_ITS_MIDDLE) for answer in ANSWERS]
    return all(
        [
            asked["y"] >= header["y"] + header["height"] - WITHIN_ROUNDING,
            asked["y"] + asked["height"] <= area["y"] + area["height"] + WITHIN_ROUNDING,
            *answers_seen,
        ]
    )


async def test_the_question_before_a_comment_is_discarded_asked_just_under_the_files_header_opens_below_cancel_seen_whole(
    long_change: RunningReview, page: Page
) -> None:
    await _open(page, long_change, SHORT_LAPTOP)
    await _comment_deep_in_the_file(page, "Half a thought")
    cancel = page.get_by_test_id("cancel-comment")
    await page.get_by_test_id("diff-view").evaluate(
        TOP_UNDER,
        [
            await cancel.element_handle(),
            await page.get_by_test_id("file-header").element_handle(),
            JUST_UNDER_THE_HEADER,
        ],
    )

    await cancel.click()

    cancel_box, question = await _boxes(page, "cancel-comment", "discard-dialog")
    below_by = question["y"] - (cancel_box["y"] + cancel_box["height"])
    assert (0 <= below_by <= ARROWS_ROOM, await _seen_whole(page, "discard-dialog")) == (True, True), (
        cancel_box,
        question,
    )


async def _bin_near_the_foot(page: Page, review: RunningReview) -> None:
    """A comment saved deep in the long file, its bin scrolled to stand just above the foot of the reading area."""
    await _open(page, review, SHORT_LAPTOP)
    await _comment_deep_in_the_file(page, "Name it after the unit")
    await page.keyboard.press("Control+Enter")
    bin_button = page.get_by_test_id("delete-comment")
    await bin_button.wait_for()
    await page.get_by_test_id("diff-view").evaluate(
        FOOT_ABOVE, [await bin_button.element_handle(), JUST_ABOVE_THE_FOOT]
    )


async def test_the_question_before_a_comment_is_deleted_asked_near_the_foot_of_the_reading_area_opens_above_the_bin_seen_whole(
    long_change: RunningReview, page: Page
) -> None:
    await _bin_near_the_foot(page, long_change)

    await page.get_by_test_id("delete-comment").click()

    bin_box, question = await _boxes(page, "delete-comment", "delete-dialog")
    above_by = bin_box["y"] - (question["y"] + question["height"])
    assert (0 <= above_by <= ARROWS_ROOM, await _seen_whole(page, "delete-dialog")) == (True, True), (
        bin_box,
        question,
    )


async def test_the_question_taking_the_keyboard_leaves_the_reading_area_where_the_reader_had_it(
    long_change: RunningReview, page: Page
) -> None:
    await _bin_near_the_foot(page, long_change)
    area = page.get_by_test_id("diff-view")
    scrolled_to = await area.evaluate(SCROLLED)

    await page.get_by_test_id("delete-comment").click()

    await page.get_by_test_id("delete-dialog").wait_for()
    assert (await page.evaluate(FOCUSED_TEST_ID), await area.evaluate(SCROLLED)) == ("confirm-keep", scrolled_to)


@pytest.fixture
def many_files(tmp_path: Path) -> Path:
    """A repository with more changed files than the tree of files shows at once on a short window."""
    committed_repository(tmp_path, dict.fromkeys(LONG_TREE, BEFORE))
    write_files(tmp_path, dict.fromkeys(LONG_TREE, AFTER))
    return tmp_path


@in_the_browsers_loop
async def long_tree(many_files: Path, servers: ReviewServers) -> RunningReview:
    return await servers.start(await repository_opening(many_files))


async def test_the_tree_of_files_keeps_its_heading_in_sight_as_its_list_scrolls(
    long_tree: RunningReview, page: Page
) -> None:
    await _open(page, long_tree, SHORT_LAPTOP)
    heading = page.get_by_test_id("sidebar-heading")
    first_file = page.get_by_test_id("file-item").first
    heading_before, file_before = await heading.bounding_box(), await first_file.bounding_box()
    assert heading_before is not None
    assert file_before is not None

    await first_file.hover()
    await page.mouse.wheel(0, SCROLLED_BY)
    await page.wait_for_function(SCROLLED_ABOVE, arg=[await first_file.element_handle(), file_before["y"]])

    assert await heading.bounding_box() == heading_before


async def test_the_side_column_and_the_agent_panel_are_headed_by_one_bar(review: RunningReview, page: Page) -> None:
    await _open(page, review, SHORT_LAPTOP)
    await page.get_by_test_id("toggle-panel").click()

    side = await painted(page.get_by_test_id("sidebar-head"))
    panel = await painted(page.get_by_test_id("panel-status"))

    assert (side.ground, side.height) == (panel.ground, panel.height)


async def test_no_heading_inside_a_pane_is_larger_than_the_pane_is_headed_with(
    review: RunningReview, page: Page
) -> None:
    await _open(page, review, SHORT_LAPTOP)
    await _opened(page, HELP)

    headed = (await painted(page.get_by_test_id(f"{HELP.pane}-heading"))).size
    sizes = await page.get_by_test_id(HELP.pane).evaluate(HEADING_SIZES)

    assert max(sizes) == float(headed.removesuffix(PIXELS)), sizes
