"""E2E: where the keyboard is after each thing the reader does.

Focus is the reader's cursor: a key acts where it is, and a control that
goes away must hand the keyboard to what remains rather than drop it on the
page. jsdom moves no focus as a browser does — not into a modal, not back
out of one — so these are held in the browser.
"""

import re
from pathlib import Path

import pytest
from playwright.async_api import Page, expect

from claude_review.hosting.workspace import ReaderFiles
from tests.e2e.browsers_loop import in_the_browsers_loop
from tests.e2e.page_reads import FOCUSED_ELEMENT, FOCUSED_TEST_ID, SCROLLED
from tests.helpers import ReviewServers, RunningReview, committed_repository, git, repository_opening, write_files

# One file, changed on a line, so the first line number the keys reach is in it
CHANGED_FILE = "main.py"
COMMITTED = {CHANGED_FILE: "def hello():\n    return 'hello'\n"}
CHANGED = {CHANGED_FILE: "def hello():\n    return 'hi'\n"}
# Files changed on every line, each long enough to fill more than the band at
# the top of the screen, for jumps between them to land on a file's header
JUMPED_TO = ("first.py", "second.py", "third.py", "fourth.py")
JUMPED_FILE_LINES = 40
# The file picked in the tree: under the one the review opens on, which is drawn already, so nothing
# above it is built after the pick and moves it
PICKED_FILE = "second.py"
# The first line of a file added whole, as its number names it
FIRST_LINE = "Comment on line 1"
# How far into the first file the reader scrolls by hand: past its head, with screens of it below still
DEEP_IN_THE_FILE = 300
# A file long enough for the diff to leave out more lines above its change,
# which is near its end, than one step shows: what the reader shows a step at
# a time, then all at once
LONG_FILE = "long.py"
LONG_FILE_LINES = 60
CHANGED_NEAR_THE_END = 55
# What the keyboard is on: the test id it carries, and the line its number names
FOCUSED_PLACE = "document.activeElement?.dataset.place"
# What stands between the side of a line and its number in the place a line number names, and how far
# up a step of `k` goes
PLACE_PARTS = ":"
A_LINE = 1
# How the welcome says how many stops the tour has, and how the tour says where it is
STOPS_ANNOUNCED = re.compile(r"(\d+) stops")
STOP_REACHED = re.compile(r"^\d+ of (\d+)$")
# The step that waits for a comment on a line, and the one a comment opened there leads to
COMMENT_ON_A_LINE = "Comment on a line"
ADD_IT = "Add it to the review"
# What a gap says while its lines are being read, in place of how many it hides
READING = "Reading"


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    """A repository with one file changed and not committed."""
    committed_repository(tmp_path, COMMITTED)
    write_files(tmp_path, CHANGED)
    return tmp_path


@in_the_browsers_loop
async def review(repository: Path, servers: ReviewServers) -> RunningReview:
    return await servers.start(await repository_opening(repository))


@in_the_browsers_loop
async def gapped(tmp_path: Path, servers: ReviewServers) -> RunningReview:
    """A review of one long file changed near its end, with the lines above the change left out."""
    lines = [f"line_{number} = {number}" for number in range(1, LONG_FILE_LINES + 1)]
    committed_repository(tmp_path, {LONG_FILE: "\n".join(lines) + "\n"})
    lines[CHANGED_NEAR_THE_END - 1] = "changed = True"
    write_files(tmp_path, {LONG_FILE: "\n".join(lines) + "\n"})
    return await servers.start(await repository_opening(tmp_path))


@in_the_browsers_loop
async def several_files(tmp_path: Path, servers: ReviewServers) -> RunningReview:
    """A review of several files, each added whole: a stream of file sections to jump between."""
    committed_repository(tmp_path, COMMITTED)
    lines = "".join(f"line {number}\n" for number in range(JUMPED_FILE_LINES))
    write_files(tmp_path, dict.fromkeys(JUMPED_TO, lines))
    git(tmp_path, "add", ".")
    return await servers.start(await repository_opening(tmp_path))


async def _open_review(page: Page, review: RunningReview) -> None:
    await page.goto(review.url)
    await page.get_by_test_id("sidebar").wait_for()


async def _start_a_comment(page: Page, words: str) -> None:
    """Open a comment field on the first line from the keyboard, and write in it."""
    await page.keyboard.press("j")
    await page.keyboard.press("Enter")
    await page.get_by_test_id("comment-input").wait_for()
    await page.keyboard.type(words)


async def test_v_after_a_jump_from_the_tree_marks_the_file_jumped_to(several_files: RunningReview, page: Page) -> None:
    """Landed on a file's header, the file above ends at the band's edge: the file read is the one jumped to."""
    await _open_review(page, several_files)

    for path in JUMPED_TO:
        await page.get_by_test_id("file-item").filter(has_text=path).click()
        await page.keyboard.press("v")
        section = page.locator(f'[data-testid="file-section"][data-path="{path}"]')
        assert await section.get_by_test_id("viewed-toggle").is_checked(), f"v after jumping to {path}"


async def test_a_line_key_after_a_file_picked_in_the_tree_lands_on_its_first_line_and_takes_the_reader_nowhere_back(
    several_files: RunningReview, page: Page
) -> None:
    """The pick leaves the keyboard on the tree's row, outside what is read: the key starts where the reader reads."""
    await _open_review(page, several_files)
    files = page.get_by_test_id("diff-view")
    picked = page.locator(f'[data-testid="file-section"][data-path="{PICKED_FILE}"]')
    await page.get_by_test_id("file-item").filter(has_text=PICKED_FILE).click()
    scrolled_to = await files.evaluate(SCROLLED)

    await page.keyboard.press("j")

    await expect(picked.get_by_role("button", name=FIRST_LINE, exact=True)).to_be_focused()
    assert await files.evaluate(SCROLLED) >= scrolled_to > 0


async def test_a_line_key_deep_in_a_file_lands_on_a_line_the_reader_sees_and_leaves_the_files_where_they_are(
    several_files: RunningReview, page: Page
) -> None:
    """Scrolled by hand, the keyboard is on nothing: the key starts where the reader reads.

    The pointer is brought to the line it lands on: one under the header kept in sight would be scrolled out to reach.
    """
    await _open_review(page, several_files)
    files = page.get_by_test_id("diff-view")
    await files.evaluate("(area, depth) => area.scrollBy(0, depth)", DEEP_IN_THE_FILE)

    await page.keyboard.press("j")
    await page.locator(FOCUSED_ELEMENT).hover()

    assert await _focused(page) == "line-gutter"
    assert await files.evaluate(SCROLLED) == DEEP_IN_THE_FILE


async def test_a_line_key_with_the_keyboard_on_a_line_scrolled_away_lands_on_a_line_the_reader_sees(
    several_files: RunningReview, page: Page
) -> None:
    """The line the keyboard was left on is out of sight: the key starts where the reader reads, and takes them nowhere back."""
    await _open_review(page, several_files)
    files = page.get_by_test_id("diff-view")
    await page.keyboard.press("j")
    await files.evaluate("(area, depth) => area.scrollBy(0, depth)", DEEP_IN_THE_FILE)

    await page.keyboard.press("j")
    await page.locator(FOCUSED_ELEMENT).hover()

    assert await files.evaluate(SCROLLED) == DEEP_IN_THE_FILE


async def test_k_from_the_first_line_in_sight_steps_up_onto_a_line_the_reader_sees(
    several_files: RunningReview, page: Page
) -> None:
    """The line above is under the header kept in sight until the page scrolls it out from under it."""
    await _open_review(page, several_files)
    files = page.get_by_test_id("diff-view")
    await files.evaluate("(area, depth) => area.scrollBy(0, depth)", DEEP_IN_THE_FILE)
    await page.keyboard.press("j")
    side, first_in_sight = (await page.evaluate(FOCUSED_PLACE)).split(PLACE_PARTS)

    await page.keyboard.press("k")
    stepped_to = await files.evaluate(SCROLLED)
    await page.locator(FOCUSED_ELEMENT).hover()

    assert await page.evaluate(FOCUSED_PLACE) == f"{side}{PLACE_PARTS}{int(first_in_sight) - A_LINE}"
    assert await files.evaluate(SCROLLED) == stepped_to < DEEP_IN_THE_FILE


async def test_the_tour_moves_on_to_the_field_the_reader_opened_and_keeps_its_count(
    review: RunningReview, reader_files: ReaderFiles, page: Page
) -> None:
    """The step after opening a comment lights the field it opened, and the count is the welcome's to the end."""
    reader_files.guide.unlink()
    await _open_review(page, review)
    welcome = page.get_by_test_id("guide-welcome")
    announced = STOPS_ANNOUNCED.search(await welcome.inner_text())
    assert announced is not None
    await page.get_by_test_id("guide-start").click()
    tour = page.get_by_test_id("guide-tour")
    while await tour.get_by_role("heading").inner_text() != COMMENT_ON_A_LINE:
        await tour.get_by_test_id("guide-next").click()

    await page.get_by_test_id("line-gutter").first.click()
    await page.get_by_test_id("comment-input").wait_for()

    await tour.get_by_role("heading", name=ADD_IT).wait_for()
    reached = STOP_REACHED.match(await tour.get_by_text(STOP_REACHED).inner_text())
    assert reached is not None
    assert reached.group(1) == announced.group(1)


async def test_the_help_opened_from_inside_a_pane_takes_its_place_and_gives_the_keyboard_to_help_as_it_closes(
    review: RunningReview, page: Page
) -> None:
    """One pane at a time: ? from inside a pane opens the help in its place, and Escape gives the keyboard back."""
    await _open_review(page, review)
    await page.get_by_test_id("settings-toggle").click()
    pane = page.get_by_test_id("settings-menu")
    assert await pane.evaluate("pane => pane.contains(document.activeElement)")

    await page.keyboard.press("?")
    help_menu = page.get_by_test_id("help-menu")
    await help_menu.wait_for()
    assert await help_menu.evaluate("pane => pane.contains(document.activeElement)")
    await pane.wait_for(state="detached")
    await page.keyboard.press("Escape")
    await help_menu.wait_for(state="detached")

    assert await page.evaluate(FOCUSED_TEST_ID) == "open-help"


async def test_a_pane_opened_by_its_keys_from_a_field_and_closed_by_its_button_gives_the_keyboard_back_to_the_field(
    review: RunningReview, page: Page
) -> None:
    await _open_review(page, review)
    await _start_a_comment(page, "Half a thought")
    await page.keyboard.press("Control+Shift+Enter")
    await page.get_by_test_id("finish-review").wait_for()

    await page.get_by_test_id("quick-submit").click()

    await expect(page.get_by_test_id("comment-input")).to_be_focused()


async def _press(page: Page, test_id: str) -> None:
    """Press a control from the keyboard: the keyboard on it, then Enter."""
    await page.get_by_test_id(test_id).first.focus()
    await page.keyboard.press("Enter")


async def _focused(page: Page) -> str | None:
    return await page.evaluate(FOCUSED_TEST_ID)


async def test_the_keyboard_stays_on_a_step_up_and_lands_on_the_first_line_shown_once_none_is_hidden(
    gapped: RunningReview, page: Page
) -> None:
    """The button pressed is disabled while it reads, which takes the keyboard off it: it comes back while the button
    stays; read whole, the gap goes, and its first line takes it."""
    await _open_review(page, gapped)
    gap = page.get_by_test_id("hunk-gap").first
    hidden_before = await gap.inner_text()

    await _press(page, "expand-up")
    # Read once the gap says how many it hides now: while reading it says neither that nor what it said before
    await gap.filter(has_not_text=hidden_before).filter(has_not_text=READING).wait_for()
    assert await _focused(page) == "expand-up"

    await _press(page, "expand-all")
    await page.locator('[data-place="new:1"]').wait_for()
    assert (await _focused(page), await page.evaluate(FOCUSED_PLACE)) == ("line-gutter", "new:1")


async def test_the_keyboard_goes_with_the_tree_of_files_to_its_rail_and_comes_back_with_it(
    review: RunningReview, page: Page
) -> None:
    await _open_review(page, review)

    await _press(page, "hide-sidebar")
    await page.get_by_test_id("show-sidebar").wait_for()
    assert await _focused(page) == "show-sidebar"

    await page.keyboard.press("Enter")
    await page.get_by_test_id("hide-sidebar").wait_for()
    assert await _focused(page) == "hide-sidebar"


async def test_the_keyboard_goes_from_the_agent_panels_own_button_to_the_control_that_brings_the_panel_back(
    review: RunningReview, page: Page
) -> None:
    await _open_review(page, review)
    await page.keyboard.press("c")
    await page.get_by_test_id("agent-panel").wait_for()

    await _press(page, "close-panel")
    await page.get_by_test_id("agent-panel").wait_for(state="detached")

    assert await _focused(page) == "toggle-panel"


async def test_f_with_the_keyboard_on_a_file_of_the_tree_leaves_it_on_the_rail_of_the_tree(
    review: RunningReview, page: Page
) -> None:
    await _open_review(page, review)
    await page.get_by_test_id("file-item").first.focus()

    await page.keyboard.press("f")
    await page.get_by_test_id("show-sidebar").wait_for()

    assert await _focused(page) == "show-sidebar"
