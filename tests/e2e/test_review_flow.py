"""E2E tests: full round-trip with real server and real browser."""

import asyncio
import json
import sys
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import uvicorn
from playwright.async_api import Locator, Page

from claude_review.domain.models import ReviewMode
from claude_review.presentation.app import create_app
from claude_review.presentation.state import ServerState
from claude_review.repositories.git_repository import GitRepository
from claude_review.services.diff_service import DiffService
from claude_review.services.text_file_service import TextFileService
from claude_review.services.transcript_service import TranscriptService
from tests.helpers import git

ServerFixture = tuple[str, ServerState]


# --- Shared helpers ---


async def _start_server(diff_files, state, mode=ReviewMode.DIFF) -> AsyncGenerator[ServerFixture]:
    """Start a uvicorn server and yield (url, state)."""
    app = create_app(diff_files=diff_files, state=state, mode=mode)
    # Match the CLI: the default picks uvicorn's older websockets integration
    config = uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning", ws="websockets-sansio")
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


def _section(page: Page, path_suffix: str) -> Locator:
    """One file's section in the stream.

    Every file is on screen at once, so a locator has to say which file it
    means — otherwise it matches the same control in each of them.
    """
    return page.locator(f'[data-testid="file-section"][data-path$="{path_suffix}"]')


def _first_gutter(page: Page, path_suffix: str) -> Locator:
    return _section(page, path_suffix).get_by_test_id("line-gutter").first


async def _click_line_and_comment(page: Page, line_locator, text: str) -> None:
    """Helper: click a line gutter and add a comment."""
    await line_locator.click()
    await page.get_by_test_id("comment-input").fill(text)
    await page.get_by_test_id("save-comment").click()
    await page.wait_for_selector(f"text={text}")


# --- Diff mode fixtures ---


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

    async for fixture in _start_server(diff_files, state, ReviewMode.DIFF):
        yield fixture


# --- Diff mode tests ---


async def test_review_flow_add_comment_and_submit(server_url: ServerFixture, page: Page) -> None:
    """Full round trip: see diff, add comment, submit, verify output."""
    url, state = server_url
    await page.goto(url)
    await page.get_by_test_id("sidebar").wait_for()

    file_buttons = await page.get_by_test_id("file-item").all()
    assert len(file_buttons) >= 1

    line_cell = page.get_by_test_id("line-gutter").first
    await _click_line_and_comment(page, line_cell, "This needs fixing")

    await page.get_by_test_id("quick-submit").click()
    await page.get_by_test_id("submitted-banner").wait_for()

    assert state.result is not None
    assert "This needs fixing" in state.result


async def test_multi_line_range_comment(server_url: ServerFixture, page: Page) -> None:
    """Drag creates a range comment (e.g. file:1-3)."""
    url, state = server_url
    await page.goto(url)
    await page.get_by_test_id("sidebar").wait_for()

    gutters = _section(page, "main.py").get_by_test_id("line-gutter")
    await gutters.first.dispatch_event("mousedown")
    await gutters.nth(4).dispatch_event("mouseenter")
    await _section(page, "main.py").get_by_test_id("raw-view").dispatch_event("mouseup")

    await page.get_by_test_id("comment-input").fill("Refactor this range")
    await page.get_by_test_id("save-comment").click()
    await page.wait_for_selector("text=Refactor this range")

    await page.get_by_test_id("quick-submit").click()
    await page.get_by_test_id("submitted-banner").wait_for()

    assert state.result is not None
    assert "Refactor this range" in state.result
    assert "-" in state.result


async def test_multi_file_review(server_url: ServerFixture, page: Page) -> None:
    """Comments across multiple files all appear in output."""
    url, state = server_url
    await page.goto(url)
    await page.get_by_test_id("sidebar").wait_for()

    assert len(await page.get_by_test_id("file-item").all()) >= 2

    # Both files are already on screen, so neither comment needs navigation
    await _click_line_and_comment(page, _first_gutter(page, "main.py"), "Comment on main")
    await _click_line_and_comment(page, _first_gutter(page, "new_file.ts"), "Comment on new file")

    await page.get_by_test_id("quick-submit").click()
    await page.get_by_test_id("submitted-banner").wait_for()

    assert state.result is not None
    assert "main.py" in state.result
    assert "new_file.ts" in state.result
    # Each comment is filed under the file it was left on, not both under one
    assert state.result.index("Comment on main") < state.result.index("new_file.ts")


async def test_empty_submit_button_disabled(server_url: ServerFixture, page: Page) -> None:
    """Submit with no comments — button should be disabled."""
    url, _state = server_url
    await page.goto(url)
    await page.get_by_test_id("sidebar").wait_for()

    submit_btn = page.get_by_test_id("quick-submit")
    assert await submit_btn.is_disabled()


# --- Review body tests ---


async def test_review_body_only_via_modal(server_url: ServerFixture, page: Page) -> None:
    """Submit with only a review summary via the modal, no inline comments."""
    url, state = server_url
    await page.goto(url)
    await page.get_by_test_id("sidebar").wait_for()

    await page.get_by_test_id("finish-review").click()
    await page.get_by_test_id("review-body").wait_for()

    modal_textarea = page.get_by_test_id("review-body")
    await modal_textarea.fill("Wrong approach, reconsider the design.")

    await page.get_by_test_id("modal-submit").click()
    await page.get_by_test_id("submitted-banner").wait_for()

    assert state.result is not None
    assert "Wrong approach" in state.result


async def test_review_body_with_inline_comment_via_modal(server_url: ServerFixture, page: Page) -> None:
    """Add inline comment, then open modal to add summary, submit from modal."""
    url, state = server_url
    await page.goto(url)
    await page.get_by_test_id("sidebar").wait_for()

    line_cell = page.get_by_test_id("line-gutter").first
    await _click_line_and_comment(page, line_cell, "Fix this line")

    await page.get_by_test_id("finish-review").click()
    await page.wait_for_selector("text=1 inline comment")

    modal_textarea = page.get_by_test_id("review-body")
    await modal_textarea.fill("Generally good.")

    await page.get_by_test_id("modal-submit").click()
    await page.get_by_test_id("submitted-banner").wait_for()

    assert state.result is not None
    assert "Generally good." in state.result
    assert "Fix this line" in state.result


async def test_nothing_written_means_nothing_to_send(server_url: ServerFixture, page: Page) -> None:
    """Neither the button nor the shortcut sends an empty review."""
    url, state = server_url
    await page.goto(url)
    await page.get_by_test_id("sidebar").wait_for()

    assert await page.get_by_test_id("quick-submit").is_disabled()

    await page.keyboard.press("Control+Shift+Enter")
    assert state.result is None


async def test_a_summary_on_its_own_is_a_review(server_url: ServerFixture, page: Page) -> None:
    """The header and the dialog agree on what counts as something to send."""
    url, state = server_url
    await page.goto(url)
    await page.get_by_test_id("sidebar").wait_for()

    await page.get_by_test_id("finish-review").click()
    await page.get_by_test_id("review-body").fill("The shape is right; the naming needs work.")
    await page.keyboard.press("Escape")

    submit = page.get_by_test_id("quick-submit")
    assert not await submit.is_disabled()

    await submit.click()
    await page.get_by_test_id("submitted-banner").wait_for()

    assert state.result is not None
    assert "The shape is right" in state.result


async def test_modal_esc_closes_and_preserves_body(server_url: ServerFixture, page: Page) -> None:
    """Esc closes the modal, and reopening preserves the typed text."""
    url, _state = server_url
    await page.goto(url)
    await page.get_by_test_id("sidebar").wait_for()

    # Open modal and type
    await page.get_by_test_id("finish-review").click()
    modal_textarea = page.get_by_test_id("review-body")
    await modal_textarea.fill("Draft feedback")

    # Close with Esc
    await page.keyboard.press("Escape")
    await page.get_by_test_id("finish-review").wait_for()

    # Reopen — text should still be there
    await page.get_by_test_id("finish-review").click()
    modal_textarea = page.get_by_test_id("review-body")
    assert await modal_textarea.input_value() == "Draft feedback"


# --- Files mode fixtures ---


@pytest.fixture
def text_files(tmp_path: Path) -> list[Path]:
    """Create text files for files-mode testing."""
    f1 = tmp_path / "plan.md"
    f1.write_text("# My Plan\n\nStep 1: Do something\nStep 2: Do more\n")
    f2 = tmp_path / "notes.md"
    f2.write_text("Some notes\nMore notes\n")
    return [f1, f2]


@pytest.fixture
async def files_mode_server(text_files: list[Path]) -> AsyncGenerator[ServerFixture]:
    """Start a real server in files mode."""
    diff_files = TextFileService().read_files(text_files)
    state = ServerState(shutdown_event=asyncio.Event())

    async for fixture in _start_server(diff_files, state, ReviewMode.FILES):
        yield fixture


# --- Files mode tests ---


async def test_files_mode_sidebar_shows_files_without_diff_decorations(
    files_mode_server: ServerFixture, page: Page
) -> None:
    """Sidebar shows plain file list — no status badges, no +/- stats."""
    url, _state = files_mode_server
    await page.goto(url)
    await page.get_by_test_id("sidebar").wait_for()

    heading = await page.get_by_test_id("sidebar-heading").text_content()
    assert heading == "2 files"

    file_buttons = await page.get_by_test_id("file-item").all()
    assert len(file_buttons) == 2


async def test_files_mode_comment_and_submit(files_mode_server: ServerFixture, page: Page) -> None:
    """Full round-trip in files mode: click line, comment, submit, verify output."""
    url, state = files_mode_server
    await page.goto(url)
    await page.get_by_test_id("sidebar").wait_for()

    line_cell = page.get_by_test_id("line-gutter").first
    await _click_line_and_comment(page, line_cell, "Plan needs more detail")

    await page.get_by_test_id("quick-submit").click()
    await page.get_by_test_id("submitted-banner").wait_for()

    assert state.result is not None
    assert "Plan needs more detail" in state.result


async def test_files_mode_comments_across_multiple_files(files_mode_server: ServerFixture, page: Page) -> None:
    """Comments on different files all appear in the submission output."""
    url, state = files_mode_server
    await page.goto(url)
    await page.get_by_test_id("sidebar").wait_for()

    line_cell = page.get_by_test_id("line-gutter").first
    await _click_line_and_comment(page, line_cell, "Comment on plan")

    file_buttons = await page.get_by_test_id("file-item").all()
    assert len(file_buttons) >= 2
    await file_buttons[1].click()
    await page.get_by_test_id("line-gutter").first.wait_for()

    line_cell = page.get_by_test_id("line-gutter").first
    await _click_line_and_comment(page, line_cell, "Comment on notes")

    await page.get_by_test_id("quick-submit").click()
    await page.get_by_test_id("submitted-banner").wait_for()

    assert state.result is not None
    assert "Comment on plan" in state.result
    assert "Comment on notes" in state.result


# --- Markdown view mode tests (use files mode with .md files) ---


async def test_markdown_file_shows_view_toggle(files_mode_server: ServerFixture, page: Page) -> None:
    """Markdown files show the content view toggle in the header."""
    url, _state = files_mode_server
    await page.goto(url)
    await page.get_by_test_id("sidebar").wait_for()

    plan = _section(page, "plan.md")
    toggle = plan.get_by_test_id("content-view-toggle")
    await toggle.wait_for()
    assert await toggle.is_visible()

    assert await plan.get_by_test_id("view-mode-raw").is_visible()
    assert await plan.get_by_test_id("view-mode-preview").is_visible()
    assert await plan.get_by_test_id("view-mode-side-by-side").is_visible()


async def test_markdown_preview_renders_content(files_mode_server: ServerFixture, page: Page) -> None:
    """Switching to preview mode renders markdown as HTML."""
    url, _state = files_mode_server
    await page.goto(url)
    await page.get_by_test_id("sidebar").wait_for()

    plan = _section(page, "plan.md")
    await plan.get_by_test_id("view-mode-preview").click()
    await plan.get_by_test_id("preview-view").wait_for()

    # plan.md contains "# My Plan" which should render as an h1
    heading = plan.get_by_test_id("markdown-content").locator("h1")
    await heading.wait_for()
    assert await heading.text_content() == "My Plan"


async def test_side_by_side_shows_both_panes(files_mode_server: ServerFixture, page: Page) -> None:
    """Side-by-side mode shows raw view and rendered markdown."""
    url, _state = files_mode_server
    await page.goto(url)
    await page.get_by_test_id("sidebar").wait_for()

    plan = _section(page, "plan.md")
    await plan.get_by_test_id("view-mode-side-by-side").click()
    await plan.get_by_test_id("side-by-side-view").wait_for()

    # Left pane: raw view with line gutters
    assert await plan.get_by_test_id("raw-view").is_visible()
    assert len(await plan.get_by_test_id("line-gutter").all()) > 0

    # Right pane: rendered markdown
    assert await plan.get_by_test_id("markdown-content").first.is_visible()


async def test_commenting_works_in_side_by_side(files_mode_server: ServerFixture, page: Page) -> None:
    """Adding a comment in the left pane of side-by-side mode works."""
    url, state = files_mode_server
    await page.goto(url)
    await page.get_by_test_id("sidebar").wait_for()

    plan = _section(page, "plan.md")
    await plan.get_by_test_id("view-mode-side-by-side").click()
    await plan.get_by_test_id("side-by-side-view").wait_for()

    await _click_line_and_comment(page, _first_gutter(page, "plan.md"), "Side-by-side comment")

    await page.get_by_test_id("quick-submit").click()
    await page.get_by_test_id("submitted-banner").wait_for()

    assert state.result is not None
    assert "Side-by-side comment" in state.result


async def test_view_mode_persists_across_file_navigation(files_mode_server: ServerFixture, page: Page) -> None:
    """Switching to preview on one .md file persists when navigating to another .md file."""
    url, _state = files_mode_server
    await page.goto(url)
    await page.get_by_test_id("sidebar").wait_for()

    # The choice is one setting for the whole review, so switching it on one
    # markdown file applies to every other one in the stream
    await _section(page, "plan.md").get_by_test_id("view-mode-preview").click()

    await _section(page, "plan.md").get_by_test_id("preview-view").wait_for()
    assert await _section(page, "notes.md").get_by_test_id("preview-view").is_visible()


async def test_preview_shows_comment_badge(files_mode_server: ServerFixture, page: Page) -> None:
    """Adding comments in raw mode shows a badge when switching to preview."""
    url, _state = files_mode_server
    await page.goto(url)
    await page.get_by_test_id("sidebar").wait_for()

    # Add a comment in raw mode
    await _click_line_and_comment(page, _first_gutter(page, "plan.md"), "Needs work")

    # Switch to preview — badge should show
    plan = _section(page, "plan.md")
    await plan.get_by_test_id("view-mode-preview").click()
    await plan.get_by_test_id("preview-view").wait_for()

    badge = plan.get_by_test_id("preview-comment-badge")
    await badge.wait_for()
    badge_text = await badge.text_content()
    assert badge_text is not None
    assert "1 comment" in badge_text
    assert "Raw" in badge_text


async def test_toggle_hidden_for_non_markdown_in_diff_mode(server_url: ServerFixture, page: Page) -> None:
    """Non-markdown files (e.g. .py, .ts) do not show the view toggle."""
    url, _state = server_url
    await page.goto(url)
    await page.get_by_test_id("sidebar").wait_for()

    toggle = page.get_by_test_id("content-view-toggle")
    assert await toggle.count() == 0


# --- Transcript mode fixtures ---


@pytest.fixture
def transcript_file(tmp_path: Path) -> Path:
    """Create a JSONL conversation file for transcript-mode testing."""
    f = tmp_path / "conversation.jsonl"
    lines = [
        json.dumps(
            {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": "can you refactor the auth module?\nuse JWT instead of sessions",
                },
            }
        ),
        json.dumps(
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "def authenticate(token):\n    return jwt.decode(token)"}],
                },
            }
        ),
    ]
    f.write_text("\n".join(lines))
    return f


@pytest.fixture
async def transcript_mode_server(transcript_file: Path) -> AsyncGenerator[ServerFixture]:
    """Start a real server in transcript mode."""
    diff_files = TranscriptService().parse(transcript_file)
    state = ServerState(shutdown_event=asyncio.Event())

    async for fixture in _start_server(diff_files, state, ReviewMode.TRANSCRIPT):
        yield fixture


# --- Transcript mode tests ---


async def test_transcript_mode_sidebar_shows_messages(transcript_mode_server: ServerFixture, page: Page) -> None:
    """Sidebar shows message list with 'Messages' header."""
    url, _state = transcript_mode_server
    await page.goto(url)
    await page.get_by_test_id("sidebar").wait_for()

    heading = await page.get_by_test_id("sidebar-heading").text_content()
    assert heading == "2 messages"

    file_buttons = await page.get_by_test_id("file-item").all()
    assert len(file_buttons) == 2


async def test_transcript_mode_comment_and_submit(transcript_mode_server: ServerFixture, page: Page) -> None:
    """Full round-trip in transcript mode: comment on message, submit, verify output."""
    url, state = transcript_mode_server
    await page.goto(url)
    await page.get_by_test_id("sidebar").wait_for()

    line_cell = page.get_by_test_id("line-gutter").first
    await _click_line_and_comment(page, line_cell, "Wrong approach")

    await page.get_by_test_id("quick-submit").click()
    await page.get_by_test_id("submitted-banner").wait_for()

    assert state.result is not None
    assert "Transcript Review" in state.result
    assert "Wrong approach" in state.result


async def test_every_file_is_on_screen_at_once(server_url: ServerFixture, page: Page) -> None:
    """The diff reads as one stream: no file has to be selected to be seen."""
    url, _state = server_url
    await page.goto(url)
    await page.get_by_test_id("sidebar").wait_for()

    sections = page.get_by_test_id("file-section")
    await sections.first.wait_for()

    file_count = len(await page.get_by_test_id("file-item").all())
    assert await sections.count() == file_count


async def test_folding_a_file_hides_its_lines(server_url: ServerFixture, page: Page) -> None:
    """A file can be folded away without leaving the stream."""
    url, _state = server_url
    await page.goto(url)
    await page.get_by_test_id("sidebar").wait_for()

    main = _section(page, "main.py")
    await main.get_by_test_id("raw-view").wait_for()

    await main.get_by_test_id("collapse-file").click()
    await main.get_by_test_id("raw-view").wait_for(state="detached")

    # The other files are untouched
    assert await _section(page, "new_file.ts").get_by_test_id("raw-view").is_visible()


async def test_marking_a_file_viewed_folds_it(server_url: ServerFixture, page: Page) -> None:
    """Marking a file done folds it, the way a long review needs."""
    url, _state = server_url
    await page.goto(url)
    await page.get_by_test_id("sidebar").wait_for()

    main = _section(page, "main.py")
    await main.get_by_test_id("raw-view").wait_for()

    await main.get_by_test_id("viewed-toggle").check()
    await main.get_by_test_id("raw-view").wait_for(state="detached")


async def test_filtering_the_sidebar_narrows_the_list(server_url: ServerFixture, page: Page) -> None:
    """A long review is navigated by narrowing the list, not by scrolling it."""
    url, _state = server_url
    await page.goto(url)
    await page.get_by_test_id("sidebar").wait_for()

    await page.get_by_test_id("file-filter").fill("new_file")

    items = await page.get_by_test_id("file-item").all()
    assert len(items) == 1
    text = await items[0].text_content()
    assert text is not None
    assert "new_file.ts" in text


async def test_sidebar_counts_files_marked_viewed(server_url: ServerFixture, page: Page) -> None:
    """Progress through a review is visible without counting rows by eye."""
    url, _state = server_url
    await page.goto(url)
    await page.get_by_test_id("sidebar").wait_for()

    await _section(page, "main.py").get_by_test_id("viewed-toggle").check()

    heading = page.get_by_test_id("sidebar-heading")
    await heading.filter(has_text="1 viewed").wait_for()


async def test_a_file_further_down_the_stream_is_readable(server_url: ServerFixture, page: Page) -> None:
    """Files build as they are approached, so scrolling to one shows its lines."""
    url, _state = server_url
    await page.goto(url)
    await page.get_by_test_id("sidebar").wait_for()

    last = _section(page, "new_file.ts")
    await last.scroll_into_view_if_needed()

    await last.get_by_test_id("raw-view").wait_for()
    assert await last.get_by_test_id("line-gutter").count() > 0


async def test_scrolling_to_a_file_from_the_sidebar_shows_its_lines(server_url: ServerFixture, page: Page) -> None:
    """The sidebar moves the reader, and the file it lands on is ready to read."""
    url, _state = server_url
    await page.goto(url)
    await page.get_by_test_id("sidebar").wait_for()

    items = await page.get_by_test_id("file-item").all()
    await items[-1].click()

    visible_sections = page.get_by_test_id("file-section")
    assert await visible_sections.count() >= 2
    await page.get_by_test_id("raw-view").last.wait_for()


async def test_split_layout_faces_the_two_versions(server_url: ServerFixture, page: Page) -> None:
    """A replacement can be read across rather than down."""
    url, _state = server_url
    await page.goto(url)
    await page.get_by_test_id("sidebar").wait_for()

    await page.get_by_test_id("layout-split").click()

    main = _section(page, "main.py")
    await main.get_by_test_id("split-view").wait_for()
    assert await main.get_by_test_id("raw-view").count() == 0


async def test_comment_left_in_split_layout_reaches_claude(server_url: ServerFixture, page: Page) -> None:
    """Commenting works the same in either layout."""
    url, state = server_url
    await page.goto(url)
    await page.get_by_test_id("sidebar").wait_for()

    await page.get_by_test_id("layout-split").click()
    main = _section(page, "main.py")
    await main.get_by_test_id("split-view").wait_for()

    await _click_line_and_comment(page, main.get_by_test_id("line-gutter").first, "Split comment")

    await page.get_by_test_id("quick-submit").click()
    await page.get_by_test_id("submitted-banner").wait_for()

    assert state.result is not None
    assert "Split comment" in state.result


async def test_a_comment_can_be_left_without_a_mouse(server_url: ServerFixture, page: Page) -> None:
    """The tool's central action has a keyboard path."""
    url, state = server_url
    await page.goto(url)
    await page.get_by_test_id("sidebar").wait_for()

    await page.keyboard.press("j")
    await page.keyboard.press("Enter")

    await page.get_by_test_id("comment-input").wait_for()
    await page.keyboard.type("Typed, not clicked")
    await page.keyboard.press("Control+Enter")
    await page.wait_for_selector("text=Typed, not clicked")

    await page.keyboard.press("Control+Shift+Enter")
    await page.get_by_test_id("submitted-banner").wait_for()

    assert state.result is not None
    assert "Typed, not clicked" in state.result


async def test_j_and_k_move_between_lines(server_url: ServerFixture, page: Page) -> None:
    """Moving is moving focus, so the browser keeps the cursor on screen."""
    url, _state = server_url
    await page.goto(url)
    await page.get_by_test_id("sidebar").wait_for()

    await page.keyboard.press("j")
    first = await page.evaluate("document.activeElement.getAttribute('aria-label')")
    await page.keyboard.press("j")
    second = await page.evaluate("document.activeElement.getAttribute('aria-label')")
    await page.keyboard.press("k")
    back = await page.evaluate("document.activeElement.getAttribute('aria-label')")

    assert first != second
    assert back == first


async def test_question_mark_shows_the_keys(server_url: ServerFixture, page: Page) -> None:
    url, _state = server_url
    await page.goto(url)
    await page.get_by_test_id("sidebar").wait_for()

    await page.keyboard.press("?")
    await page.get_by_test_id("shortcuts-list").wait_for()

    await page.keyboard.press("Escape")
    await page.get_by_test_id("shortcuts-list").wait_for(state="detached")


async def test_v_marks_the_file_you_are_in_as_viewed(server_url: ServerFixture, page: Page) -> None:
    url, _state = server_url
    await page.goto(url)
    await page.get_by_test_id("sidebar").wait_for()

    await page.keyboard.press("j")
    await page.keyboard.press("v")

    await page.get_by_test_id("sidebar-heading").filter(has_text="1 viewed").wait_for()


async def test_typing_a_comment_does_not_trigger_shortcuts(server_url: ServerFixture, page: Page) -> None:
    """The letters that move around must still be letters inside a comment."""
    url, _state = server_url
    await page.goto(url)
    await page.get_by_test_id("sidebar").wait_for()

    await page.keyboard.press("j")
    await page.keyboard.press("Enter")
    await page.get_by_test_id("comment-input").wait_for()
    await page.keyboard.type("just keep vjunk pn")

    assert await page.get_by_test_id("comment-input").input_value() == "just keep vjunk pn"


async def test_a_suggestion_reaches_claude_as_a_replacement(server_url: ServerFixture, page: Page) -> None:
    """Saying what the code should be beats describing it."""
    url, state = server_url
    await page.goto(url)
    await page.get_by_test_id("sidebar").wait_for()

    await _first_gutter(page, "main.py").click()
    await page.get_by_test_id("comment-input").fill("Return the greeting we agreed on")
    await page.get_by_test_id("suggest-change").click()

    await page.get_by_test_id("save-comment").click()
    await page.get_by_test_id("quick-submit").click()
    await page.get_by_test_id("submitted-banner").wait_for()

    assert state.result is not None
    assert "```suggestion" in state.result
    assert "Return the greeting we agreed on" in state.result


async def test_ignoring_whitespace_retakes_the_diff(server_url: ServerFixture, page: Page) -> None:
    """The toggle asks git again rather than filtering what is already loaded."""
    url, _state = server_url
    await page.goto(url)
    await page.get_by_test_id("sidebar").wait_for()

    before = await page.get_by_test_id("file-section").count()
    await page.get_by_test_id("ignore-whitespace").check()
    await page.wait_for_timeout(300)

    # Nothing in the fixture is whitespace-only, so the review is unchanged —
    # what matters is that it came back rather than emptying out
    assert await page.get_by_test_id("file-section").count() == before


async def test_comments_survive_a_reload(server_url: ServerFixture, page: Page) -> None:
    """A stray reload should not cost an hour of reading."""
    url, state = server_url
    await page.goto(url)
    await page.get_by_test_id("sidebar").wait_for()

    await _click_line_and_comment(page, _first_gutter(page, "main.py"), "Written before the reload")

    await page.reload()
    await page.get_by_test_id("restored-notice").wait_for()
    await page.wait_for_selector("text=Written before the reload")

    await page.get_by_test_id("quick-submit").click()
    await page.get_by_test_id("submitted-banner").wait_for()

    assert state.result is not None
    assert "Written before the reload" in state.result


async def test_a_question_asked_in_a_thread_is_answered_in_it(server_url: ServerFixture, page: Page) -> None:
    """The whole round trip: asked in the browser, answered from outside it."""
    url, _state = server_url
    port = int(url.rsplit(":", 1)[1])
    await page.goto(url)
    await page.get_by_test_id("sidebar").wait_for()

    # Asking is only offered while something is waiting to answer
    waiting = asyncio.create_task(_take_question(port, seconds=15))
    await page.get_by_test_id("end-review").wait_for()

    await _first_gutter(page, "main.py").click()
    await page.get_by_test_id("comment-input").fill("Was the old greeting used anywhere else?")
    await page.get_by_test_id("ask-now").click()
    await page.get_by_test_id("awaiting-answer").wait_for()

    asked = await waiting
    assert asked["question"]["body"] == "Was the old greeting used anywhere else?"
    assert asked["question"]["quote"] == ["def hello():"]

    await _send_reply(
        port,
        asked["question"]["thread_id"],
        asked["question"]["question_id"],
        "No, it was the only caller.",
    )

    answer = page.get_by_test_id("thread-answer")
    await answer.wait_for()
    assert "No, it was the only caller." in await answer.text_content()
    # And it is marked as something the reader has not looked at yet
    await page.get_by_test_id("comment-unread").wait_for()


async def test_a_round_is_sent_without_ending_the_review(server_url: ServerFixture, page: Page) -> None:
    """Rounds appear once something is waiting to answer them."""
    url, state = server_url
    port = int(url.rsplit(":", 1)[1])
    await page.goto(url)
    await page.get_by_test_id("sidebar").wait_for()

    # An agent waiting on the review is what makes a round worth offering
    waiting = asyncio.create_task(_take_question(port, seconds=15))
    await page.get_by_test_id("end-review").wait_for()

    await _click_line_and_comment(page, _first_gutter(page, "main.py"), "Shorten this greeting")
    await page.get_by_test_id("quick-submit").click()

    handed_over = await waiting
    assert handed_over["type"] == "round"
    assert "Shorten this greeting" in handed_over["round"]["markdown"]

    # The review is still open, with its threads on screen
    assert not state.shutdown_event.is_set()
    await page.wait_for_selector("text=Shorten this greeting")

    await page.get_by_test_id("end-review").click()
    await page.get_by_test_id("submitted-banner").wait_for()
    assert state.shutdown_event.is_set()


async def test_a_second_round_carries_only_what_is_new(server_url: ServerFixture, page: Page) -> None:
    """A round is what has been written since the last one, not the review again."""
    url, _state = server_url
    port = int(url.rsplit(":", 1)[1])
    await page.goto(url)
    await page.get_by_test_id("sidebar").wait_for()

    first = asyncio.create_task(_take_question(port, seconds=15))
    await page.get_by_test_id("end-review").wait_for()

    await _click_line_and_comment(page, _first_gutter(page, "main.py"), "Shorten this greeting")
    await page.get_by_test_id("quick-submit").click()
    await first

    second = asyncio.create_task(_take_question(port, seconds=15))
    await _click_line_and_comment(page, _first_gutter(page, "new_file.ts"), "And name this properly")
    await page.get_by_test_id("quick-submit").click()

    round_two = await second
    assert "round 2" in round_two["round"]["markdown"]
    assert "And name this properly" in round_two["round"]["markdown"]
    assert "Shorten this greeting" not in round_two["round"]["markdown"]


async def test_the_panel_carries_a_message_to_the_agent_and_back(server_url: ServerFixture, page: Page) -> None:
    """The whole round trip for what belongs to no line of the diff."""
    url, _state = server_url
    port = int(url.rsplit(":", 1)[1])
    await page.goto(url)
    await page.get_by_test_id("sidebar").wait_for()

    # The panel shows itself once something is there to answer
    waiting = asyncio.create_task(_take_question(port, seconds=15))
    await page.get_by_test_id("panel-input").wait_for()

    await page.get_by_test_id("panel-input").fill("Which tests cover this?")
    await page.get_by_test_id("send-message").click()
    await page.get_by_test_id("panel-working").wait_for()

    handed_over = await waiting
    assert handed_over["type"] == "message"
    assert handed_over["message"]["text"] == "Which tests cover this?"

    await _say(port, handed_over["message"]["message_id"], "The e2e one, and two unit tests.")

    answer = page.get_by_test_id("panel-answer")
    await answer.wait_for()
    assert "The e2e one, and two unit tests." in await answer.text_content()


async def test_a_message_carries_the_thread_it_points_at(server_url: ServerFixture, page: Page) -> None:
    """Pointing at a thread saves retyping which line it was, and losing it."""
    url, _state = server_url
    port = int(url.rsplit(":", 1)[1])
    await page.goto(url)
    await page.get_by_test_id("sidebar").wait_for()

    waiting = asyncio.create_task(_take_question(port, seconds=15))
    await page.get_by_test_id("panel-input").wait_for()

    await _click_line_and_comment(page, _first_gutter(page, "main.py"), "Is this greeting used?")

    await page.get_by_test_id("panel-input").fill("Look again at @")
    await page.get_by_test_id("thread-option").first.click()
    await page.get_by_test_id("send-message").click()

    handed_over = await waiting
    [thread] = handed_over["message"]["threads"]
    assert thread["body"] == "Is this greeting used?"
    assert thread["quote"] == ["def hello():"]


async def test_the_review_says_when_the_tree_moves_under_it(server_url: ServerFixture, page: Page) -> None:
    """Said, never acted on: the reader decides when to take the diff again."""
    url, state = server_url
    await page.goto(url)
    await page.get_by_test_id("sidebar").wait_for()

    state.push({"type": "changed", "files": 2})

    notice = page.get_by_test_id("tree-moved")
    await notice.wait_for()
    assert "2 files have changed" in " ".join((await notice.text_content() or "").split())

    await page.get_by_test_id("dismiss-moved").click()
    assert await notice.count() == 0


async def _say(port: int, message_id: str, text: str) -> None:
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "claude_review",
        "say",
        "--port",
        str(port),
        "--message",
        message_id,
        text,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    assert proc.returncode == 0, stderr.decode()


async def _take_question(port: int, seconds: int = 10) -> dict:
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "claude_review",
        "wait",
        "--port",
        str(port),
        "--seconds",
        str(seconds),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    return json.loads(stdout)


async def _send_reply(port: int, thread_id: str, question_id: str, text: str) -> None:
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "claude_review",
        "reply",
        "--port",
        str(port),
        "--thread",
        thread_id,
        "--question",
        question_id,
        text,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    assert proc.returncode == 0, stderr.decode()
