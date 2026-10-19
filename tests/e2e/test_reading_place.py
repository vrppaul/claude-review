"""E2E: a retake keeps the reader in the file they were reading.

The agent's work changes what is drawn above the reader as well as where
they are. The browser keeps the reader in place while the rows they look
at stay on the page; when the work rewrites the very file being read, its
rows are drawn afresh, and a page that keeps its scroll offset across the
new diff puts the reader in another file. What is in view is the browser's
alone: jsdom lays nothing out.
"""

from pathlib import Path

import pytest
from httpx import AsyncClient
from playwright.async_api import Locator, Page, ViewportSize, expect

from tests.e2e.browsers_loop import in_the_browsers_loop
from tests.helpers import ReviewServers, RunningReview, committed_repository, repository_opening, write_files

# Three files, each changed far down: one above the file being read, and one
# below it changed on enough lines that the line read can be scrolled to the top
ABOVE_FILE = "above.py"
READ_FILE = "read.py"
BELOW_FILE = "zz_below.py"
FILE_LENGTH = 200
CHANGED_LINE = 100
CHANGED_BELOW = range(50, 110)
# Where the agent's work adds lines in the file above and in the file being
# read, and how many: enough rows to move everything below by more than a screen
GROWN_AT = 10
GROWN_BY = 80
# A screen short enough that the files do not all fit on it
SCREEN: ViewportSize = {"width": 1280, "height": 600}


def _lines(path: str, changed: dict[int, str] | None = None) -> str:
    """A file of numbered lines, some of them changed."""
    return "".join(f"{(changed or {}).get(number, f'{path} line {number}')}\n" for number in range(1, FILE_LENGTH + 1))


def _grown(path: str) -> str:
    """The file as the agent's work leaves it: lines added near its top, its change still there."""
    added = "\n".join(f"{path} grown {count}" for count in range(GROWN_BY))
    return _lines(path, {GROWN_AT: f"grown here\n{added}", CHANGED_LINE: "changed"})


@pytest.fixture
def three_files(tmp_path: Path) -> Path:
    """A repository where every file changed far down."""
    paths = (ABOVE_FILE, READ_FILE, BELOW_FILE)
    repo = committed_repository(tmp_path / "repo", {path: _lines(path) for path in paths})
    write_files(repo, {path: _lines(path, {CHANGED_LINE: "changed"}) for path in (ABOVE_FILE, READ_FILE)})
    write_files(repo, {BELOW_FILE: _lines(BELOW_FILE, dict.fromkeys(CHANGED_BELOW, "changed"))})
    return repo


@in_the_browsers_loop
async def review(three_files: Path, servers: ReviewServers) -> RunningReview:
    return await servers.start(await repository_opening(three_files))


def _section(page: Page, path: str) -> Locator:
    return page.locator(f'[data-testid="file-section"][data-path="{path}"]')


async def test_a_retake_that_rewrites_the_file_being_read_keeps_the_reader_in_it(
    review: RunningReview, three_files: Path, page: Page
) -> None:
    await page.set_viewport_size(SCREEN)
    await page.goto(review.url)
    # The reader reads the changed line of the file, brought to the top of the area
    read = _section(page, READ_FILE).get_by_role("button", name=f"Comment on line {CHANGED_LINE}", exact=True)
    await read.scroll_into_view_if_needed()
    await read.evaluate("number => number.scrollIntoView({ block: 'start' })")

    # The agent's work grows the file above and the file being read, above the line read, and retakes the diff
    write_files(three_files, {ABOVE_FILE: _grown(ABOVE_FILE), READ_FILE: _grown(READ_FILE)})
    async with AsyncClient(base_url=review.url) as agent:
        await agent.post("/api/retake", json={})
    await page.get_by_text(f"{READ_FILE} grown {GROWN_BY - 1}", exact=True).wait_for(state="attached")

    await expect(_section(page, READ_FILE)).to_be_in_viewport()
