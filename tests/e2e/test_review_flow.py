"""E2E tests: full round-trip with real server and real browser."""

import asyncio
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import uvicorn
from playwright.async_api import Page, async_playwright

from claude_review.presentation.app import create_app
from claude_review.presentation.schemas import ServerState
from claude_review.repositories.git_repository import GitRepository
from claude_review.services.diff_service import DiffService
from tests.helpers import git

ServerFixture = tuple[str, ServerState]


@pytest.fixture
def e2e_repo(tmp_path: Path) -> Path:
    """Create a git repo with several types of changes for e2e testing."""
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.email", "test@test.com")
    git(tmp_path, "config", "user.name", "Test")

    (tmp_path / "main.py").write_text("def hello():\n    return 'hello'\n\ndef world():\n    return 'world'\n")
    (tmp_path / "utils.py").write_text("# utils\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "initial")

    # Make changes: modify + add staged
    (tmp_path / "main.py").write_text("def hello():\n    return 'hi'\n\ndef world():\n    return 'world'\n")
    (tmp_path / "new_file.ts").write_text("export const x = 1;\nexport const y = 2;\nexport const z = 3;\n")
    git(tmp_path, "add", "new_file.ts")

    return tmp_path


@pytest.fixture
async def server_url(e2e_repo: Path) -> AsyncGenerator[ServerFixture]:
    """Start a real server against the e2e repo and yield its URL."""
    git_repo = GitRepository()
    diff_service = DiffService(git_repository=git_repo)
    diff_files = await diff_service.get_diff(e2e_repo)

    state = ServerState(shutdown_event=asyncio.Event())
    app = create_app(diff_files=diff_files, state=state)

    config = uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning")
    server = uvicorn.Server(config)

    task = asyncio.create_task(server.serve())

    for _ in range(50):
        await asyncio.sleep(0.1)
        if server.started:
            break
    assert server.started, "Server failed to start within 5 seconds"

    port = server.servers[0].sockets[0].getsockname()[1]
    url = f"http://127.0.0.1:{port}"

    yield url, state

    server.should_exit = True
    await task


async def _click_line_and_comment(page: Page, line_locator, text: str) -> None:
    """Helper: click a line gutter and add a comment."""
    await line_locator.click()
    await page.locator("textarea").fill(text)
    await page.locator("button:text('Comment')").click()
    await page.wait_for_selector(f"text={text}")


async def test_review_flow_add_comment_and_submit(server_url: ServerFixture) -> None:
    """Full round trip: see diff, add comment, submit, verify output."""
    url, state = server_url

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(url)

        await page.wait_for_selector("aside")
        file_buttons = await page.query_selector_all("aside button")
        assert len(file_buttons) >= 1

        # Double-click a line to select + open comment box
        line_cell = page.locator("td.cursor-pointer").first
        await _click_line_and_comment(page, line_cell, "This needs fixing")

        # Submit
        await page.locator("button:text('Submit Review')").click()
        await page.wait_for_selector("text=Review submitted")

        assert state.result is not None
        assert "This needs fixing" in state.result

        await browser.close()


async def test_multi_line_range_comment(server_url: ServerFixture) -> None:
    """Shift+click creates a range comment (e.g. file:1-3)."""
    url, state = server_url

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(url)
        await page.wait_for_selector("aside")

        # Drag from first gutter cell to a later one for multi-line range
        first_cell = page.locator("td.cursor-pointer").first
        later_cell = page.locator("td.cursor-pointer").nth(4)

        # Simulate drag: mousedown on first, mouseenter on later, mouseup
        await first_cell.dispatch_event("mousedown")
        await later_cell.dispatch_event("mouseenter")
        await page.dispatch_event("div.overflow-auto", "mouseup")

        # Comment box should appear — fill and save
        await page.locator("textarea").first.fill("Refactor this range")
        await page.locator("button:text('Comment')").first.click()
        await page.wait_for_selector("text=Refactor this range")

        # Submit
        await page.locator("button:text('Submit Review')").click()
        await page.wait_for_selector("text=Review submitted")

        assert state.result is not None
        # Should contain a range like "file:X-Y"
        assert "Refactor this range" in state.result
        assert "-" in state.result  # range notation present

        await browser.close()


async def test_multi_file_review(server_url: ServerFixture) -> None:
    """Comments across multiple files all appear in output."""
    url, state = server_url

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(url)
        await page.wait_for_selector("aside")

        file_buttons = await page.query_selector_all("aside button")
        assert len(file_buttons) >= 2, f"Expected at least 2 files, got {len(file_buttons)}"

        # Comment on first file
        line_cell = page.locator("td.cursor-pointer").first
        await _click_line_and_comment(page, line_cell, "Comment on file 1")

        # Switch to second file and wait for diff to render
        await file_buttons[1].click()
        await page.locator("td.cursor-pointer").first.wait_for()

        # Comment on second file
        line_cell = page.locator("td.cursor-pointer").first
        await _click_line_and_comment(page, line_cell, "Comment on file 2")

        # Submit
        await page.locator("button:text('Submit Review')").click()
        await page.wait_for_selector("text=Review submitted")

        assert state.result is not None
        assert "Comment on file 1" in state.result
        assert "Comment on file 2" in state.result

        await browser.close()


async def test_empty_submit_button_disabled(server_url: ServerFixture) -> None:
    """Submit with no comments — button should be disabled."""
    url, _state = server_url

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(url)
        await page.wait_for_selector("aside")

        submit_btn = page.locator("button:text('Submit Review')")
        assert await submit_btn.is_disabled()

        await browser.close()
