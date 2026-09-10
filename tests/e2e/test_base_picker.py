"""E2E: choosing what the working tree is read against, in a real browser.

The header's second half is a control now. What it changes is what is drawn
— never what the review holds, and never where a thread is anchored — so
these tests watch both halves: the diff narrows, and the way back is there.
"""

import asyncio
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import uvicorn
from playwright.async_api import Page

from claude_review.domain.models import ReviewMode
from claude_review.presentation.app import create_app
from claude_review.presentation.state import ServerState
from claude_review.repositories.git_repository import GitRepository
from claude_review.services.diff_service import DiffService
from claude_review.services.version_service import VersionService
from tests.helpers import git


async def _said(page: Page, testid: str) -> str:
    """What an element says, as one line: the markup wraps where it likes."""
    return " ".join((await page.get_by_test_id(testid).text_content() or "").split())


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
async def review(picker_repo: Path, tmp_path: Path) -> AsyncGenerator[tuple[str, ServerState]]:
    """A review that has already been through one round."""
    objects = tmp_path / "objects"
    objects.mkdir()
    git_repo = GitRepository(objects=objects)
    state = ServerState(shutdown_event=asyncio.Event())

    mark = await VersionService(git_repository=git_repo).take(picker_repo, round_number=1)
    assert mark is not None
    state.snapshots.append(mark)
    # The work that answers round 1, done after its tree was written down
    (picker_repo / "read.py").write_text("first pass\nsecond pass\nand what round 1 asked for\n")

    diff_files = await DiffService(git_repository=git_repo).get_diff(picker_repo)
    app = create_app(diff_files=diff_files, state=state, mode=ReviewMode.DIFF, root=picker_repo, objects=objects)
    config = uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning", ws="websockets-sansio")
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve())

    for _ in range(50):
        await asyncio.sleep(0.1)
        if server.started:
            break
    assert server.started, "Server failed to start within 5 seconds"

    yield f"http://127.0.0.1:{server.servers[0].sockets[0].getsockname()[1]}", state

    server.should_exit = True
    await task


async def test_the_header_says_what_is_under_review_and_against_what(
    review: tuple[str, ServerState], page: Page
) -> None:
    url, _ = review
    await page.goto(url)

    await page.wait_for_selector('[data-testid="base-picker"]')
    assert "repo" in await _said(page, "review-title")
    assert "uncommitted changes" in await _said(page, "base-picker")


async def test_a_round_can_be_read_against_and_left_again(review: tuple[str, ServerState], page: Page) -> None:
    """The whole point: what the agent did about round 1, and the way back."""
    url, _ = review
    await page.goto(url)
    await page.wait_for_selector('[data-testid="file-item"]')
    assert await page.locator('[data-testid="file-item"]').count() == 2

    await page.click('[data-testid="base-picker"]')
    await page.wait_for_selector('[data-testid="base-list"]')
    await page.click('[data-testid="base-option"]:has-text("round 1")')

    await page.wait_for_selector('[data-testid="narrowed-to"]')
    assert "changes since round 1" in await _said(page, "narrowed-to")
    assert await page.locator('[data-testid="file-item"]').count() == 1

    await page.click('[data-testid="show-everything"]')

    await page.wait_for_selector('[data-testid="narrowed-to"]', state="detached")
    assert await page.locator('[data-testid="file-item"]').count() == 2


async def test_a_thread_the_base_cannot_draw_is_counted_rather_than_dropped(
    review: tuple[str, ServerState], page: Page
) -> None:
    """It is anchored to the review's own diff, which a narrower base has not moved."""
    url, _ = review
    await page.goto(url)
    await page.wait_for_selector('[data-testid="file-item"]')

    section = page.locator('[data-testid="file-section"][data-path$="untouched.py"]')
    await section.get_by_test_id("line-gutter").first.click()
    await page.get_by_test_id("comment-input").fill("nobody has been back to this one")
    await page.get_by_test_id("save-comment").click()
    await page.wait_for_selector("text=nobody has been back to this one")

    await page.click('[data-testid="base-picker"]')
    await page.click('[data-testid="base-option"]:has-text("round 1")')
    await page.wait_for_selector('[data-testid="narrowed-to"]')

    assert "1 thread is not on this screen" in await _said(page, "narrowed-to")
    assert "1 comment" in await _said(page, "comment-count")
