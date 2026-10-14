"""E2E: Story introduced once, under the switch, to a reader who has never tried it.

A newcomer is welcomed first; once the welcome is put away, a pane under
the switch introduces Story. Said not to show it again, it is gone from
every review on the machine, which the server keeps, so a reload does not
bring it back. Where the keyboard lands as it goes is only true in a
browser.
"""

from pathlib import Path

import pytest
from playwright.async_api import Page

from claude_review.hosting.workspace import ReaderFiles
from tests.e2e.browsers_loop import in_the_browsers_loop
from tests.helpers import ReviewServers, RunningReview, committed_repository, repository_opening, write_files

CHANGED_FILE = "told.py"
COMMITTED_FILES = {CHANGED_FILE: "keep one\nfirst two\n"}
# The change under review, which a story can be told of
THE_CHANGE = {CHANGED_FILE: "keep one\nchanged two\n"}
# Which element holds the keyboard, by its test id
FOCUSED_TEST_ID = "document.activeElement?.dataset.testid"


@pytest.fixture
def changed_repo(tmp_path: Path) -> Path:
    """A repository with a change a story can be told of."""
    repo = committed_repository(tmp_path / "repo", COMMITTED_FILES)
    write_files(repo, THE_CHANGE)
    return repo


@in_the_browsers_loop
async def review(changed_repo: Path, servers: ReviewServers) -> RunningReview:
    """A review of the change, which no agent has told a story of."""
    return await servers.start(await repository_opening(changed_repo))


async def _welcomed_and_introduced(page: Page, review: RunningReview, reader_files: ReaderFiles) -> None:
    """Open the review as somebody who never opened one, put the welcome away, and meet Story's introduction."""
    reader_files.guide.unlink()
    await page.goto(review.url)
    await page.get_by_test_id("guide-not-now").click()
    await page.get_by_test_id("story-introduction").wait_for()


async def _press(page: Page, test_id: str) -> None:
    """Press a control from the keyboard: the keyboard on it, then Enter."""
    await page.get_by_test_id(test_id).focus()
    await page.keyboard.press("Enter")


async def test_story_put_away_for_good_by_a_newcomer_is_not_introduced_after_a_reload(
    review: RunningReview, reader_files: ReaderFiles, page: Page
) -> None:
    await _welcomed_and_introduced(page, review, reader_files)

    await page.get_by_test_id("story-introduction-hide").click()
    await page.get_by_test_id("story-introduction-hidden").wait_for()
    await page.reload()
    await page.get_by_test_id("reading-view").wait_for()

    assert await page.get_by_test_id("story-introduction").count() == 0


async def test_the_keyboard_goes_to_undo_once_story_is_put_away_for_good(
    review: RunningReview, reader_files: ReaderFiles, page: Page
) -> None:
    await _welcomed_and_introduced(page, review, reader_files)

    await _press(page, "story-introduction-hide")
    await page.get_by_test_id("story-introduction-hidden").wait_for()

    assert await page.evaluate(FOCUSED_TEST_ID) == "story-introduction-undo"


async def test_the_keyboard_goes_to_story_once_its_introduction_is_put_away_for_now(
    review: RunningReview, reader_files: ReaderFiles, page: Page
) -> None:
    await _welcomed_and_introduced(page, review, reader_files)

    await _press(page, "story-introduction-close")
    await page.get_by_test_id("story-introduction").wait_for(state="detached")

    assert await page.evaluate(FOCUSED_TEST_ID) == "read-as-story"
