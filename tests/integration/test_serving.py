"""A review held open in this process: what it hands back, whatever else goes wrong while it runs.

What goes wrong is played by what the review is built on — a repository
that goes away, one that cannot be staged, a terminal that cannot be told.
The review is reached into only where nothing it is built on can play it:
its own check on its reader failing, and its own wait for a first page
running out.
"""

import asyncio
import contextlib
import signal
import tempfile
from collections.abc import AsyncGenerator, Iterator
from contextlib import AbstractAsyncContextManager
from pathlib import Path
from typing import override

import pytest
from httpx import URL, AsyncClient
from structlog.typing import EventDict

from claude_review.hosting.announcer import ReviewAnnouncer
from claude_review.hosting.errors import ReviewStoppedError, ServerStartError
from claude_review.hosting.hosted_review import HostedReview
from claude_review.hosting.ports import ANY_FREE_PORT, bind
from claude_review.hosting.serving import hold_open, serve_review, stop_signals
from claude_review.presentation.schemas.pushes import ChangedPush
from claude_review.repositories.git_repository import GitRepository, GitStagedTree
from claude_review.services.review_opening import ReviewOpening, open_diff
from tests.helpers import (
    IMAGES_ROUTE,
    INITIAL_FILE,
    INITIAL_FILES,
    LOOK_EVERY_SECONDS,
    PNG,
    SETTLE_SECONDS,
    ReviewFactory,
    committed_repository,
    message_json,
    next_push,
)
from tests.page_socket import page_socket_held

SUBMIT_ROUTE = "/api/submit"
MESSAGE_ROUTE = "/api/message"
THE_ROUND = "Rename the helper."
# A round sent with the review kept open for the next, and the last round, sent and ending the review
A_ROUND = {"threads": [], "body": THE_ROUND, "end": False}
LAST_ROUND = {"threads": [], "body": THE_ROUND, "end": True}
# What the pieces of a staging are called in the temporary directory
STAGING_LEFTOVERS = ("*.git-index", "*.git-objects")
# The record every review keeps of itself in the temporary directory, each in a directory of its own
KEPT_RECORDS = "claude-review-*/*/review.json"
# The name the review reads how long it waits for its first page by, as it is put together
FIRST_PAGE_DEADLINE_NAME = "claude_review.services.review.review.FIRST_PAGE_DEADLINE_SECONDS"
# A wait for a first page a test outlasts, and which the server still comes up well within, as it does in the real one
SHORT_FIRST_PAGE_DEADLINE_SECONDS = 1.0


class StagingThatHangs(GitRepository):
    """A repository whose working tree takes git as long as anyone cares to wait to stage, as a huge one does."""

    def __init__(self) -> None:
        super().__init__(objects=None)
        self.staging = asyncio.Event()

    @override
    @contextlib.asynccontextmanager
    async def staged(self, path: Path) -> AsyncGenerator[GitStagedTree]:
        async with super().staged(path) as staged:
            self.staging.set()
            await asyncio.Event().wait()
            yield staged


class RepositoryThatGoesAway(GitRepository):
    """A repository read as git reads it until its disk goes away, from then on failing whatever it is asked."""

    def __init__(self) -> None:
        super().__init__(objects=None)
        self.gone = False

    @override
    async def changed_paths(self, path: Path) -> list[str]:
        if self.gone:
            failure = "the disk went away"
            raise OSError(failure)
        return await super().changed_paths(path)


class RepositoryThatCannotBeStaged(GitRepository):
    """A repository whose working tree cannot be read at all, as one on a disk already gone is."""

    def __init__(self) -> None:
        super().__init__(objects=None)

    @override
    def staged(self, path: Path) -> AbstractAsyncContextManager[GitStagedTree]:
        failure = "the repository went away"
        raise OSError(failure)


class RecordingAnnouncer(ReviewAnnouncer):
    """Whoever started the review, as a test: it holds on to what it is told."""

    def __init__(self) -> None:
        self.address: asyncio.Future[str] = asyncio.get_running_loop().create_future()
        self.images_left: list[Path] = []
        self.told_nobody_came = False

    @override
    async def listening_at(self, url: str) -> None:
        self.address.set_result(url)

    @override
    def images_left_in(self, directory: Path) -> None:
        self.images_left.append(directory)

    @override
    def never_opened(self) -> None:
        self.told_nobody_came = True


class TerminalThatIsGone(RecordingAnnouncer):
    """Whoever started the review, gone: their terminal closed, so telling them where the review is fails."""

    @override
    async def listening_at(self, url: str) -> None:
        failure = "the terminal went away"
        raise BrokenPipeError(failure)


@pytest.fixture(autouse=True)
def kept_under_this_test(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep what the review writes, and what it remembers about its reader, under this test's own directory."""
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))


@pytest.fixture
def signals_never_end_the_tests() -> Iterator[list[int]]:
    """Catch any stop signal a test sends that nothing of the review answers, rather than let it end the run."""
    unanswered: list[int] = []
    left_as_found = signal.signal(signal.SIGTERM, lambda number, _frame: unanswered.append(number))
    yield unanswered
    signal.signal(signal.SIGTERM, left_as_found)


async def _served(hosted: HostedReview, announcer: ReviewAnnouncer) -> str:
    """Serve a review put together by the test, Ctrl+C and `kill` answered from the start."""
    with stop_signals() as signals:
        listening = bind(ANY_FREE_PORT, may_fall_back=False)
        return await serve_review(hosted, listening=listening, announcer=announcer, signals=signals)


async def _held_open(opening: ReviewOpening, announcer: ReviewAnnouncer) -> str:
    """Hold a review open the way the command line does: in a workspace of its own, on a port of its own."""
    with stop_signals() as signals:
        return await hold_open(opening, port=ANY_FREE_PORT, announcer=announcer, signals=signals)


async def _opened(repo: Path, repository: GitRepository) -> ReviewOpening:
    """Open a review of the repository the way the command line does, Ctrl+C and `kill` answered from the start."""
    with stop_signals():
        return await open_diff(repo, None, repository)


@pytest.fixture
async def opening(tmp_git_repo: Path) -> ReviewOpening:
    (tmp_git_repo / INITIAL_FILE).write_text("changed\n")
    return await open_diff(tmp_git_repo, None, GitRepository(objects=None))


@pytest.fixture
async def announcer() -> RecordingAnnouncer:
    return RecordingAnnouncer()


def _port_of(address: str) -> int:
    """The port the review at this address listens on."""
    port = URL(address).port
    if port is None:
        failure = f"{address} names no port"
        raise AssertionError(failure)
    return port


def _events(logged: list[EventDict]) -> list[str]:
    return [entry["event"] for entry in logged]


async def _until_logged(logged: list[EventDict], event: str) -> None:
    """Return once the review has logged an event."""
    while event not in _events(logged):
        await asyncio.sleep(LOOK_EVERY_SECONDS)


async def test_a_file_changed_under_the_review_is_said_to_the_review_on_screen(
    reviews: ReviewFactory, announcer: RecordingAnnouncer, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """Said, never acted on: the reader decides when to take the diff again.

    The repository stands apart from the test's directory, where the review keeps what it writes: nothing but the
    file changed moves in it.
    """
    repository = committed_repository(tmp_path_factory.mktemp("apart"), INITIAL_FILES)
    (repository / INITIAL_FILE).write_text("changed\n")
    opened = await open_diff(repository, None, GitRepository(objects=None))
    serving = asyncio.ensure_future(_served(reviews.hosted(opened), announcer))
    address = await asyncio.wait_for(announcer.address, SETTLE_SECONDS)

    # The tree is watched only once a page is there to be told
    async with page_socket_held(_port_of(address)) as page, AsyncClient(base_url=address) as agent:
        (repository / INITIAL_FILE).write_text("changed again, by somebody else\n")
        moved = await asyncio.to_thread(next_push, page, ChangedPush)
        await agent.post(SUBMIT_ROUTE, json=LAST_ROUND)
    await asyncio.wait_for(serving, timeout=SETTLE_SECONDS)

    assert moved == ChangedPush(moved_count=1)


async def test_a_watch_on_the_tree_that_fails_leaves_the_review_running_and_its_round_handed_back(
    opening: ReviewOpening, reviews: ReviewFactory, announcer: RecordingAnnouncer, logged: list[EventDict]
) -> None:
    """The watch only helps; the reader's unsent work and the last round matter more than it."""
    repository = RepositoryThatGoesAway()
    serving = asyncio.ensure_future(_served(reviews.hosted(opening, repository=repository), announcer))
    address = await asyncio.wait_for(announcer.address, SETTLE_SECONDS)

    repository.gone = True
    # The tree is watched only once a page is there to be told
    async with page_socket_held(_port_of(address)), AsyncClient(base_url=address) as agent:
        await asyncio.wait_for(_until_logged(logged, "review_helper_failed"), SETTLE_SECONDS)
        await agent.post(SUBMIT_ROUTE, json=LAST_ROUND)

    assert THE_ROUND in await asyncio.wait_for(serving, timeout=SETTLE_SECONDS)


async def test_a_review_that_cannot_tell_whoever_started_it_where_it_is_ends_rather_than_running_unseen(
    opening: ReviewOpening, reviews: ReviewFactory, logged: list[EventDict]
) -> None:
    """Run on, it would hold its port and keep its agent waiting for a reader who was never told where to look."""
    handed_back = await asyncio.wait_for(_served(reviews.hosted(opening), TerminalThatIsGone()), SETTLE_SECONDS)

    assert handed_back == ""
    assert "review_part_failed" in _events(logged)


async def test_a_review_nobody_opens_in_time_ends_and_says_so_to_whoever_started_it(
    opening: ReviewOpening, reviews: ReviewFactory, announcer: RecordingAnnouncer, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Started in the background and never opened, it would hold its port and its memory until the machine stops.

    Said as it ends, for an agent hearing it closed must not take it for the
    reader closing it. The hour is shortened where the review reads it: the
    review builds its parts from its module's constants, and is put together
    here as the command line puts it together.
    """
    monkeypatch.setattr(FIRST_PAGE_DEADLINE_NAME, SHORT_FIRST_PAGE_DEADLINE_SECONDS)

    await asyncio.wait_for(_served(reviews.hosted(opening), announcer), timeout=SETTLE_SECONDS)

    assert announcer.told_nobody_came


async def _the_check_fails() -> None:
    failure = "the event loop went away"
    raise OSError(failure)


async def test_a_review_that_can_no_longer_tell_its_page_closed_ends_rather_than_running_for_good(
    opening: ReviewOpening,
    reviews: ReviewFactory,
    announcer: RecordingAnnouncer,
    logged: list[EventDict],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Run on, it would hold its port and keep its agent waiting long after the reader has gone.

    The check is the review's own, and nothing the review is built on can
    fail it: the review handed to the server is given one that fails.
    """
    hosted = reviews.hosted(opening)
    monkeypatch.setattr(hosted.review, "end_once_its_reader_is_gone", _the_check_fails)

    handed_back = await asyncio.wait_for(_served(hosted, announcer), timeout=SETTLE_SECONDS)

    assert handed_back == ""
    assert "review_part_failed" in _events(logged)


async def test_a_review_that_cannot_open_says_why_and_ends_as_a_fault(
    opening: ReviewOpening, reviews: ReviewFactory, announcer: RecordingAnnouncer, logged: list[EventDict]
) -> None:
    """Never listening, it must still say what stopped it rather than leave only a server that stopped."""
    hosted = reviews.hosted(opening, repository=RepositoryThatCannotBeStaged())

    with pytest.raises(ServerStartError, match="fault"):
        await asyncio.wait_for(_served(hosted, announcer), timeout=SETTLE_SECONDS)

    assert "review_opening_failed" in _events(logged)


async def test_a_stop_signal_while_the_review_opens_leaves_nothing_of_its_staging_behind(
    tmp_git_repo: Path, tmp_path: Path, signals_never_end_the_tests: list[int]
) -> None:
    """`kill` while git stages a large tree: what the staging wrote goes with the review, not left in /tmp."""
    repository = StagingThatHangs()
    opening = asyncio.ensure_future(_opened(tmp_git_repo, repository))
    await asyncio.wait_for(repository.staging.wait(), SETTLE_SECONDS)

    signal.raise_signal(signal.SIGTERM)
    done, _ = await asyncio.wait({opening}, timeout=SETTLE_SECONDS)

    assert opening in done, "the signal stopped nothing"
    with pytest.raises(ReviewStoppedError):
        opening.result()
    assert signals_never_end_the_tests == [], "the signal reached no one who stops the opening"
    assert [left for pattern in STAGING_LEFTOVERS for left in tmp_path.glob(pattern)] == []


async def test_an_opening_cancelled_by_anything_but_a_stop_signal_stays_cancelled(tmp_git_repo: Path) -> None:
    """Only a signal's own stop is said as one: whatever else cancels the work is told it was cancelled."""
    repository = StagingThatHangs()
    opening = asyncio.ensure_future(_opened(tmp_git_repo, repository))
    await asyncio.wait_for(repository.staging.wait(), SETTLE_SECONDS)

    opening.cancel()

    with pytest.raises(asyncio.CancelledError):
        await opening


async def test_a_review_its_reader_finished_leaves_no_record_of_itself(
    opening: ReviewOpening, announcer: RecordingAnnouncer, tmp_path: Path
) -> None:
    """The same change opened after it is a new review, in its first round, with no story."""
    serving = asyncio.ensure_future(_held_open(opening, announcer))
    address = await asyncio.wait_for(announcer.address, SETTLE_SECONDS)
    async with AsyncClient(base_url=address) as page:
        await page.post(SUBMIT_ROUTE, json=A_ROUND)
        await page.post(SUBMIT_ROUTE, json=LAST_ROUND)
    await asyncio.wait_for(serving, timeout=SETTLE_SECONDS)

    assert list(tmp_path.glob(KEPT_RECORDS)) == []


async def test_images_never_sent_go_with_the_review_and_those_sent_stay_for_the_agent(
    opening: ReviewOpening, announcer: RecordingAnnouncer
) -> None:
    """The agent may open what it was handed once the review is over; nobody will send the rest, so it is not left in /tmp."""
    serving = asyncio.ensure_future(_held_open(opening, announcer))
    address = await asyncio.wait_for(announcer.address, SETTLE_SECONDS)
    async with AsyncClient(base_url=address) as page:
        pasted = [
            (await page.post(IMAGES_ROUTE, content=PNG, headers={"Content-Type": "image/png"})).json()["image_id"]
            for _ in range(2)
        ]
        await page.post(MESSAGE_ROUTE, json=message_json("", images=pasted[:1]))
        await page.post(SUBMIT_ROUTE, json=LAST_ROUND)
    await asyncio.wait_for(serving, timeout=SETTLE_SECONDS)

    [left_in] = announcer.images_left
    assert [image.name for image in left_in.iterdir()] == pasted[:1]
