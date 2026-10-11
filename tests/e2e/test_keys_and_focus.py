"""E2E: where the keyboard is after each thing the reader does.

Focus is the reader's cursor: a key acts where it is, and a control that
goes away must hand the keyboard to what remains rather than drop it on the
page. jsdom moves no focus as a browser does — not into a modal, not back
out of one — so these are held in the browser.
"""

from pathlib import Path

import pytest
from playwright.async_api import Page

from tests.helpers import ReviewServers, RunningReview, git, repository_opening, write_files

# One file, changed on a line, so the first line number the keys reach is in it
CHANGED_FILE = "main.py"
COMMITTED = {CHANGED_FILE: "def hello():\n    return 'hello'\n"}
CHANGED = {CHANGED_FILE: "def hello():\n    return 'hi'\n"}
# What has the keyboard, by the test id it carries
FOCUSED_TEST_ID = "document.activeElement?.dataset.testid"


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    """A repository with one file changed and not committed."""
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.email", "test@test.com")
    git(tmp_path, "config", "user.name", "Test")
    write_files(tmp_path, COMMITTED)
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "initial")
    write_files(tmp_path, CHANGED)
    return tmp_path


@pytest.fixture
async def review(repository: Path, servers: ReviewServers) -> RunningReview:
    return await servers.start(await repository_opening(repository))


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
