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
from tests.e2e.line_keys import LESS_THAN_A_LINE_APART, LINE_KEYS, LINES_UNDER_THE_HEADER, SCROLLED
from tests.helpers import ReviewServers, RunningReview, committed_repository, git, repository_opening, write_files

# One file, changed on a line, so the first line number the keys reach is in it
CHANGED_FILE = "main.py"
COMMITTED = {CHANGED_FILE: "def hello():\n    return 'hello'\n"}
CHANGED = {CHANGED_FILE: "def hello():\n    return 'hi'\n"}
# What has the keyboard, by the test id it carries
FOCUSED_TEST_ID = "document.activeElement?.dataset.testid"
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
# up two steps of `k` go
PLACE_PARTS = ":"
TWO_LINES = 2
# How the welcome says how many stops the tour has, and how the tour says where it is
STOPS_ANNOUNCED = re.compile(r"(\d+) stops")
STOP_REACHED = re.compile(r"^\d+ of (\d+)$")
# The step that waits for a comment on a line, and the one a comment opened there leads to
COMMENT_ON_A_LINE = "Comment on a line"
ADD_IT = "Add it to the review"
# What a gap says while its lines are being read, in place of how many it hides
READING = "Reading…"


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


async def test_keeping_what_was_written_gives_the_keyboard_back_to_the_field(review: RunningReview, page: Page) -> None:
    """Escape asks before the words go; keeping them closes the question and the reader types on."""
    await _open_review(page, review)
    await _start_a_comment(page, "Half a thought")

    await page.keyboard.press("Escape")
    question = page.get_by_test_id("discard-dialog")
    await question.wait_for()
    assert await question.evaluate("dialog => dialog.contains(document.activeElement)")
    await page.keyboard.press("Enter")
    await question.wait_for(state="detached")

    assert await page.evaluate(FOCUSED_TEST_ID) == "comment-input"
    await page.keyboard.type(", and the rest")
    assert await page.get_by_test_id("comment-input").input_value() == "Half a thought, and the rest"


async def test_v_after_a_jump_from_the_tree_marks_the_file_jumped_to(several_files: RunningReview, page: Page) -> None:
    """Landed on a file's header, the file above ends at the band's edge: the file read is the one jumped to."""
    await _open_review(page, several_files)

    for path in JUMPED_TO:
        await page.get_by_test_id("file-item").filter(has_text=path).click()
        await page.keyboard.press("v")
        section = page.locator(f'[data-testid="file-section"][data-path="{path}"]')
        assert await section.get_by_test_id("viewed-toggle").is_checked(), f"v after jumping to {path}"


@pytest.mark.parametrize("line_key", LINE_KEYS)
async def test_a_line_key_after_a_file_picked_in_the_tree_lands_on_its_first_line_and_takes_the_reader_nowhere_back(
    several_files: RunningReview, page: Page, line_key: str
) -> None:
    """The pick leaves the keyboard on the tree's row, outside what is read: the key starts where the reader reads."""
    await _open_review(page, several_files)
    files = page.get_by_test_id("diff-view")
    picked = page.locator(f'[data-testid="file-section"][data-path="{PICKED_FILE}"]')
    await page.get_by_test_id("file-item").filter(has_text=PICKED_FILE).click()
    scrolled_to = await files.evaluate(SCROLLED)

    await page.keyboard.press(line_key)

    await expect(picked.get_by_role("button", name=FIRST_LINE, exact=True)).to_be_focused()
    assert await files.evaluate(SCROLLED) >= scrolled_to > 0


@pytest.mark.parametrize("line_key", LINE_KEYS)
async def test_a_line_key_deep_in_a_file_lands_on_the_first_line_in_sight_under_the_header_kept_over_it(
    several_files: RunningReview, page: Page, line_key: str
) -> None:
    """Scrolled by hand, the keyboard is on nothing: the key starts at the first line the reader sees."""
    await _open_review(page, several_files)
    files = page.get_by_test_id("diff-view")
    await files.evaluate("(area, depth) => area.scrollBy(0, depth)", DEEP_IN_THE_FILE)

    await page.keyboard.press(line_key)

    # The file the reader is deep in is the first: its header is the one kept in sight over its lines
    kept_in_sight = page.get_by_test_id("file-header").first
    assert await _focused(page) == "line-gutter"
    assert -LESS_THAN_A_LINE_APART <= await kept_in_sight.evaluate(LINES_UNDER_THE_HEADER) < 1
    assert await files.evaluate(SCROLLED) == DEEP_IN_THE_FILE


@pytest.mark.parametrize("line_key", LINE_KEYS)
async def test_a_line_key_with_the_keyboard_on_a_line_scrolled_away_lands_on_the_first_line_in_sight(
    several_files: RunningReview, page: Page, line_key: str
) -> None:
    """The line the keyboard was left on is out of sight: the key starts where the reader reads, and takes them nowhere back."""
    await _open_review(page, several_files)
    files = page.get_by_test_id("diff-view")
    await page.keyboard.press("j")
    await files.evaluate("(area, depth) => area.scrollBy(0, depth)", DEEP_IN_THE_FILE)

    await page.keyboard.press(line_key)

    kept_in_sight = page.get_by_test_id("file-header").first
    assert -LESS_THAN_A_LINE_APART <= await kept_in_sight.evaluate(LINES_UNDER_THE_HEADER) < 1
    assert await files.evaluate(SCROLLED) == DEEP_IN_THE_FILE


async def test_k_from_the_first_line_in_sight_brings_each_line_above_it_into_sight_under_the_header(
    several_files: RunningReview, page: Page
) -> None:
    """A line the keyboard steps to is one the reader sees: never one behind the header kept in sight over it."""
    await _open_review(page, several_files)
    files = page.get_by_test_id("diff-view")
    await files.evaluate("(area, depth) => area.scrollBy(0, depth)", DEEP_IN_THE_FILE)
    await page.keyboard.press("j")
    side, first_in_sight = (await page.evaluate(FOCUSED_PLACE)).split(PLACE_PARTS)

    await page.keyboard.press("k")
    await page.keyboard.press("k")

    kept_in_sight = page.get_by_test_id("file-header").first
    assert await page.evaluate(FOCUSED_PLACE) == f"{side}{PLACE_PARTS}{int(first_in_sight) - TWO_LINES}"
    assert -LESS_THAN_A_LINE_APART <= await kept_in_sight.evaluate(LINES_UNDER_THE_HEADER) < LESS_THAN_A_LINE_APART
    assert await files.evaluate(SCROLLED) < DEEP_IN_THE_FILE


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


async def test_the_keyboard_lands_on_what_remains_after_each_thing_done_to_a_comment(
    gapped: RunningReview, page: Page
) -> None:
    """Saved, settled, taken up again, folded, deleted or put away, the keyboard is never left on nothing."""
    await _open_review(page, gapped)
    await page.keyboard.press("j")
    commented = await page.evaluate(FOCUSED_PLACE)

    await page.keyboard.press("Enter")
    await page.get_by_test_id("comment-input").wait_for()
    await page.keyboard.press("Escape")
    await page.get_by_test_id("comment-input").wait_for(state="detached")
    assert (await _focused(page), await page.evaluate(FOCUSED_PLACE)) == ("line-gutter", commented)

    await page.keyboard.press("Enter")
    await page.keyboard.type("Name it after the unit")
    await page.keyboard.press("Control+Enter")
    await page.get_by_test_id("comment-thread").wait_for()
    assert await _focused(page) == "comment-thread"

    await _press(page, "resolve-comment")
    await page.get_by_test_id("resolved-thread").wait_for()
    assert await _focused(page) == "comment-thread"

    await _press(page, "reopen-thread")
    await page.get_by_test_id("folded-thread").wait_for()
    assert await _focused(page) == "comment-thread"

    await _press(page, "fold-comment")
    await page.get_by_test_id("delete-comment").wait_for()
    assert await _focused(page) == "fold-comment"
    await page.keyboard.press("Enter")
    await page.get_by_test_id("folded-thread").wait_for()
    assert await _focused(page) == "fold-comment"
    await page.keyboard.press("Enter")

    await _press(page, "delete-comment")
    await page.get_by_test_id("confirm-go-ahead").focus()
    await page.keyboard.press("Enter")
    await page.get_by_test_id("comment-thread").wait_for(state="detached")
    assert (await _focused(page), await page.evaluate(FOCUSED_PLACE)) == ("line-gutter", commented)


async def test_the_keyboard_stays_on_a_step_up_and_lands_on_the_first_line_shown_once_none_is_hidden(
    gapped: RunningReview, page: Page
) -> None:
    """The button pressed keeps the keyboard while it stays; read whole, the gap goes, and its first line takes it."""
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


async def test_the_keyboard_lands_on_the_help_once_the_tour_is_skipped(
    review: RunningReview, reader_files: ReaderFiles, page: Page
) -> None:
    reader_files.guide.unlink()
    await _open_review(page, review)
    await page.get_by_test_id("guide-start").click()

    await _press(page, "guide-skip")
    await page.get_by_test_id("guide-tour").wait_for(state="detached")

    assert await _focused(page) == "open-help"


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
