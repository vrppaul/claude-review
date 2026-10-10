"""E2E: choosing what the working tree is read against, in a real browser.

The header's second half is a control now. What it changes is what is drawn
— never what the review holds, and never where a thread is anchored — so
these tests watch both halves: the diff narrows, and the way back is there.
"""

from pathlib import Path

import pytest
from httpx import AsyncClient
from playwright.async_api import Page

from tests.helpers import ReviewServers, RunningReview, git


async def _said(page: Page, testid: str) -> str:
    """What an element says, as one line: the markup wraps where it likes."""
    return " ".join((await page.get_by_test_id(testid).text_content() or "").split())


# What the review holds once round 1 is answered, and what of it changed after round 1 began
FILES_IN_THE_REVIEW = ("read.py", "untouched.py")
FILES_SINCE_ROUND_ONE = ("read.py",)


@pytest.fixture
def picker_repo(tmp_path: Path) -> Path:
    """A repository with work in it, some of it done after round 1."""
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-b", "main")
    git(repo, "config", "user.email", "test@test.com")
    git(repo, "config", "user.name", "Test")
    (repo / "read.py").write_text("first pass\n")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "initial")

    (repo / "read.py").write_text("first pass\nsecond pass\n")
    (repo / "untouched.py").write_text("nobody comes back to this\n")
    return repo


@pytest.fixture
async def review(picker_repo: Path, servers: ReviewServers) -> RunningReview:
    """A review that has already been through one round."""
    # As the command line names it: the repository, and what it is compared against
    started = await servers.start([], root=picker_repo, title=f"{picker_repo.name}: uncommitted changes")
    async with AsyncClient(base_url=started.url) as agent:
        # The diff taken, and with it the tree round 1 began from written down
        await agent.post("/api/retake", json={})
        # The work that answers round 1, done after its tree was written down
        (picker_repo / "read.py").write_text("first pass\nsecond pass\nand what round 1 asked for\n")
        # Taken again after the work, as the agent does: this is the diff on screen
        await agent.post("/api/retake", json={})
    return started


async def test_the_review_says_what_is_under_review_and_against_what(review: RunningReview, page: Page) -> None:
    """The repository in the tab's title; the base, a control, in the header."""
    await page.goto(review.url)

    await page.wait_for_selector('[data-testid="base-picker"]')
    assert "repo: uncommitted changes" in await page.title()
    assert "uncommitted changes" in await _said(page, "base-picker")


async def test_a_round_can_be_read_against_and_left_again(review: RunningReview, page: Page) -> None:
    """The whole point: what the agent did about round 1, and the way back."""
    await page.goto(review.url)
    await page.wait_for_selector('[data-testid="file-item"]')
    assert await page.locator('[data-testid="file-item"]').count() == len(FILES_IN_THE_REVIEW)

    await page.click('[data-testid="base-picker"]')
    await page.wait_for_selector('[data-testid="base-list"]')
    await page.get_by_test_id("base-option").filter(has_text="round 1").click()

    await page.wait_for_selector('[data-testid="narrowed-to"]')
    assert "changes since round 1" in await _said(page, "narrowed-to")
    assert await page.locator('[data-testid="file-item"]').count() == len(FILES_SINCE_ROUND_ONE)

    await page.click('[data-testid="show-everything"]')

    await page.wait_for_selector('[data-testid="narrowed-to"]', state="detached")
    assert await page.locator('[data-testid="file-item"]').count() == len(FILES_IN_THE_REVIEW)


async def test_a_thread_the_base_cannot_draw_is_counted_rather_than_dropped(review: RunningReview, page: Page) -> None:
    """It is anchored to the review's own diff, which a narrower base has not moved."""
    await page.goto(review.url)
    await page.wait_for_selector('[data-testid="file-item"]')

    section = page.locator('[data-testid="file-section"][data-path$="untouched.py"]')
    await section.get_by_test_id("line-gutter").first.click()
    await page.get_by_test_id("comment-input").fill("nobody has been back to this one")
    await page.get_by_test_id("save-comment").click()
    await page.wait_for_selector("text=nobody has been back to this one")

    await page.click('[data-testid="base-picker"]')
    await page.get_by_test_id("base-option").filter(has_text="round 1").click()
    await page.wait_for_selector('[data-testid="narrowed-to"]')

    assert "1 thread is not on this screen" in await _said(page, "narrowed-to")
    assert "1 comment" in await _said(page, "comment-count")
