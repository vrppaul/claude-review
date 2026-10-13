"""E2E: the lines of a narrower base, read from the keyboard in a real browser.

Under a narrower base the removed lines are that base's: they take no
comment. They are still lines the reader moves through — a browser moves no
focus onto a disabled button, so a number that takes no comment must not be
one, or j stops in front of it for good.
"""

from pathlib import Path

import pytest
from httpx import AsyncClient
from playwright.async_api import Page

from tests.e2e.browsers_loop import in_the_browsers_loop
from tests.helpers import ReviewServers, RunningReview, committed_repository, repository_opening, write_files

READ_FILE = "read.py"
COMMITTED_FILES = {READ_FILE: "keep one\nfirst two\nkeep three\nkeep four\n"}
BEFORE_ROUND_ONE = {READ_FILE: "keep one\nround two\nkeep three\nkeep four\n"}
# Answering round 1 removes line 2: in two columns it is a row with nothing on the new side
ANSWERING_ROUND_ONE = {READ_FILE: "keep one\nkeep three\nkeep four\n"}
# What a row says, as one line, for the line number that has the focus
FOCUSED_ROW = "(document.activeElement.closest('tr') || document.activeElement).innerText.replace(/\\s+/g, ' ')"


@pytest.fixture
def narrowed_repo(tmp_path: Path) -> Path:
    """A repository whose line 2 changed before round 1 and was removed after it."""
    repo = committed_repository(tmp_path / "repo", COMMITTED_FILES)
    write_files(repo, BEFORE_ROUND_ONE)
    return repo


@in_the_browsers_loop
async def review(narrowed_repo: Path, servers: ReviewServers) -> RunningReview:
    """A review whose round 1 was answered by removing line 2."""
    started = await servers.start(await repository_opening(narrowed_repo))
    async with AsyncClient(base_url=started.url) as agent:
        await agent.post("/api/retake", json={})
        write_files(narrowed_repo, ANSWERING_ROUND_ONE)
        await agent.post("/api/retake", json={})
    return started


async def _read_since_round_one(page: Page) -> None:
    await page.click('[data-testid="base-picker"]')
    await page.get_by_test_id("base-option").filter(has_text="round 1").click()
    await page.wait_for_selector('[data-testid="narrowed-to"]')


async def _rows_walked_with_j(page: Page, steps: int) -> list[str]:
    """Move down a line at a time from the top, and say which row each step lands on."""
    await page.evaluate("document.activeElement && document.activeElement.blur()")
    walked = []
    for _ in range(steps):
        await page.keyboard.press("j")
        walked.append(await page.evaluate(FOCUSED_ROW))
    return walked


async def test_j_moves_past_a_removed_line_the_narrower_base_owns(review: RunningReview, page: Page) -> None:
    await page.goto(review.url)
    await page.wait_for_selector('[data-testid="file-item"]')
    await _read_since_round_one(page)

    walked = await _rows_walked_with_j(page, len(BEFORE_ROUND_ONE[READ_FILE].splitlines()))

    assert "round two" in walked[1]
    assert "keep four" in walked[-1]


async def test_j_moves_past_it_in_two_columns_too(review: RunningReview, page: Page) -> None:
    await page.goto(review.url)
    await page.wait_for_selector('[data-testid="file-item"]')
    await _read_since_round_one(page)
    await page.get_by_test_id("settings-toggle").click()
    await page.get_by_test_id("layout-split").click()
    await page.get_by_test_id("split-view").wait_for()
    await page.get_by_test_id("settings-toggle").click()

    walked = await _rows_walked_with_j(page, len(BEFORE_ROUND_ONE[READ_FILE].splitlines()))

    assert "round two" in walked[1]
    assert "keep four" in walked[-1]
