"""E2E: where the keyboard is after each thing the reader does.

Focus is the reader's cursor: a key acts where it is, and a control that
goes away must hand the keyboard to what remains rather than drop it on the
page. jsdom moves no focus as a browser does — not into a modal, not back
out of one — so these are held in the browser.
"""

import re
from pathlib import Path

import pytest
from playwright.async_api import Page

from claude_review.hosting.workspace import ReaderFiles
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
# A file long enough for the diff to leave out more lines above its change,
# which is near its end, than one step shows: what the reader shows a step at
# a time, then all at once
LONG_FILE = "long.py"
LONG_FILE_LINES = 60
CHANGED_NEAR_THE_END = 55
# What the keyboard is on: the test id it carries, and the line its number names
FOCUSED_PLACE = "document.activeElement?.dataset.place"
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


@pytest.fixture
async def review(repository: Path, servers: ReviewServers) -> RunningReview:
    return await servers.start(await repository_opening(repository))


@pytest.fixture
async def gapped(tmp_path: Path, servers: ReviewServers) -> RunningReview:
    """A review of one long file changed near its end, with the lines above the change left out."""
    lines = [f"line_{number} = {number}" for number in range(1, LONG_FILE_LINES + 1)]
    committed_repository(tmp_path, {LONG_FILE: "\n".join(lines) + "\n"})
    lines[CHANGED_NEAR_THE_END - 1] = "changed = True"
    write_files(tmp_path, {LONG_FILE: "\n".join(lines) + "\n"})
    return await servers.start(await repository_opening(tmp_path))


@pytest.fixture
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


async def test_the_help_opens_over_a_pane_and_gives_the_keyboard_back_into_it(
    review: RunningReview, page: Page
) -> None:
    """A modal is a layer above a pane: ? from inside the pane leaves it open, and Escape returns into it."""
    await _open_review(page, review)
    await page.get_by_test_id("settings-toggle").click()
    pane = page.get_by_test_id("settings-menu")
    assert await pane.evaluate("pane => pane.contains(document.activeElement)")

    await page.keyboard.press("?")
    help_dialog = page.get_by_test_id("help-dialog")
    await help_dialog.wait_for()
    await help_dialog.get_by_text("Keyboard", exact=True).click()
    assert await pane.is_visible()
    await page.keyboard.press("Escape")
    await help_dialog.wait_for(state="detached")

    assert await pane.evaluate("pane => pane.contains(document.activeElement)")
    await page.keyboard.press("Escape")
    await pane.wait_for(state="detached")
    assert await page.evaluate(FOCUSED_TEST_ID) == "settings-toggle"


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
