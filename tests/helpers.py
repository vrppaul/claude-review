"""What the tests share: building a review, and talking to it the way its page and its agent do.

Every test reaches a review through what the review serves — its routes and
its session socket — and never through the state behind them, so a test
says what a reader or an agent can rely on and survives that state being
rearranged.
"""

import asyncio
import queue
import subprocess
import threading
import time
from collections.abc import Iterator, Mapping
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel, ConfigDict
from starlette.testclient import WebSocketTestSession

from claude_review.domain.models import (
    Comment,
    CommentSeverity,
    DiffFile,
    DiffHunk,
    DiffLine,
    FileStatus,
    LineAnchor,
    LineSide,
    LineType,
    ReaderFiles,
    ReviewMode,
    ReviewWorkspace,
    Turn,
    TurnAuthor,
)
from claude_review.presentation.app import create_app
from claude_review.presentation.state import ServerState

# Where a review built in the test process is reached. Its own page names
# itself by this origin, and the host is what the origin guard checks.
LOCAL_HOST = "127.0.0.1:8000"
LOCAL_ORIGIN = f"http://{LOCAL_HOST}"
# What the review's own page sends with every request. The socket test client
# hardcodes "testserver" as the Host whatever its base URL, so both are
# stated outright.
LOCAL_HEADERS = {"Origin": LOCAL_ORIGIN, "Host": LOCAL_HOST}

# The address a review served for a browser listens on
LOOPBACK = "127.0.0.1"
# Any free port, as the kernel hands one out
ANY_PORT = 0

SESSION_ROUTE = "/api/session"
DIFF_ROUTE = "/api/diff"
CONTEXT_ROUTE = "/api/context"
EVENTS_ROUTE = "/api/events"

# The file most reviews here hold, and the one line it shows
REVIEWED_FILE = "src/a.py"
REVIEWED_LINE = "x = 1"
# A hunk header, for hunks whose header nothing reads
HUNK_HEADER = "@@ -1 +1 @@"

# How long a test waits for something it has set going before giving up on it
SETTLE_SECONDS = 5.0
# How often it looks while it waits
LOOK_EVERY_SECONDS = 0.01
# How long an agent's poll waits when all it wants to know is whether the review has ended
GLANCE_SECONDS = 0.1
# What an agent's poll for events asks: to wait until something is handed
# over, or only to glance at whether anything is
WAIT_FOR_EVENT = {"wait_seconds": SETTLE_SECONDS}
GLANCE_AT_EVENTS = {"wait_seconds": GLANCE_SECONDS}
# How long a server started for a browser has to come up
STARTUP_SECONDS = 5.0


def git(repo: Path, *args: str) -> str:
    """Run a git command in the given repo and return stdout."""
    result = subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)
    return result.stdout


def context_line(old_number: int, new_number: int, content: str) -> DiffLine:
    """A line both sides of the diff share."""
    return DiffLine(type=LineType.CONTEXT, old_no=old_number, new_no=new_number, content=content)


def added_line(new_number: int, content: str) -> DiffLine:
    return DiffLine(type=LineType.ADD, new_no=new_number, content=content)


def removed_line(old_number: int, content: str) -> DiffLine:
    return DiffLine(type=LineType.DELETE, old_no=old_number, content=content)


def diff_file(path: str, lines: list[DiffLine], status: FileStatus = FileStatus.MODIFIED) -> DiffFile:
    """A changed file whose lines make one hunk."""
    return DiffFile(
        path=path,
        status=status,
        hunks=[DiffHunk(header=HUNK_HEADER, old_start=1, new_start=1, lines=lines)],
    )


def one_line_file(path: str = REVIEWED_FILE) -> DiffFile:
    """A file showing a single unchanged line: enough to hang a thread on."""
    return diff_file(path, [context_line(1, 1, REVIEWED_LINE)])


def line_anchor(
    file: str,
    start_line: int,
    end_line: int | None = None,
    *,
    side: LineSide = LineSide.NEW,
    quote: list[str] | None = None,
    outdated: bool = False,
) -> LineAnchor:
    """Lines of one side of a file; a single line unless an end is given."""
    return LineAnchor(
        file=file,
        side=side,
        start_line=start_line,
        end_line=end_line or start_line,
        quote=quote or [],
        outdated=outdated,
    )


def comment(
    anchor: LineAnchor,
    body: str,
    *,
    severity: CommentSeverity = CommentSeverity.NOTE,
    turns: list[Turn] | None = None,
    images: list[Path] | None = None,
    raised_by: TurnAuthor = TurnAuthor.READER,
    resolved: bool = False,
) -> Comment:
    """A thread as the reader sends it: an ordinary note unless it says otherwise."""
    return Comment(
        anchor=anchor,
        severity=severity,
        body=body,
        turns=turns or [],
        images=images or [],
        raised_by=raised_by,
        resolved=resolved,
    )


class ReviewFactory:
    """Builds reviews the way the command line does, each with a state of its own.

    A review of a repository is given room to write down its trees, as the
    command line gives it, unless the test is about one that has none.
    """

    def __init__(
        self, workspace: ReviewWorkspace, marking_workspace: ReviewWorkspace, reader_files: ReaderFiles
    ) -> None:
        self._workspace = workspace
        self._marking_workspace = marking_workspace
        self._reader_files = reader_files

    def app(
        self,
        diff_files: list[DiffFile],
        *,
        mode: ReviewMode = ReviewMode.DIFF,
        root: Path | None = None,
        base: str | None = None,
        title: str = "",
        keeps_marks: bool = True,
    ) -> FastAPI:
        writes_marks = root is not None and keeps_marks
        return create_app(
            diff_files=diff_files,
            state=ServerState(shutdown_event=asyncio.Event()),
            mode=mode,
            workspace=self._marking_workspace if writes_marks else self._workspace,
            reader_files=self._reader_files,
            title=title,
            root=root,
            base=base,
        )


def http_client(app: FastAPI) -> AsyncClient:
    """Talk to a review over HTTP, as the agent's commands do: no page, so no Origin."""
    return AsyncClient(transport=ASGITransport(app=app), base_url=LOCAL_ORIGIN)


def page_client(app: FastAPI) -> TestClient:
    """Talk to a review as its own page does, session socket included.

    Enter it before use: every request and socket then shares one event loop,
    as they do in the real server.
    """
    return TestClient(app, base_url=LOCAL_ORIGIN, headers=LOCAL_HEADERS)


def open_session(client: TestClient, headers: Mapping[str, str] | None = None) -> WebSocketTestSession:
    """Open the session socket a review on screen holds.

    The headers are copied: the test client writes the handshake's own
    headers into whatever it is given.
    """
    return client.websocket_connect(SESSION_ROUTE, headers=dict(headers or {}))


def next_push(socket: WebSocketTestSession, kind: str) -> dict:
    """Read what the server pushes until a push of one kind arrives.

    The socket carries more than any one test is about — a review is told
    when an agent attaches, and when a round retakes the diff — so what comes
    first is not always what the test waits for. A read that never returns
    fails the test rather than hanging it.
    """
    deadline = time.monotonic() + SETTLE_SECONDS
    while (remaining := deadline - time.monotonic()) > 0:
        pushed = _receive_within(socket, remaining)
        if pushed["type"] == kind:
            return pushed
    failure = f"no {kind} push arrived"
    raise AssertionError(failure)


def _receive_within(socket: WebSocketTestSession, seconds: float) -> dict:
    """One push, read off a thread of its own so that waiting for it has an end.

    The test client's read blocks until something arrives. A thread left
    waiting is let go when the socket closes.
    """
    received: queue.Queue[dict] = queue.Queue()
    threading.Thread(target=_receive_into, args=(socket, received), daemon=True).start()
    try:
        return received.get(timeout=seconds)
    except queue.Empty:
        failure = "nothing was pushed"
        raise AssertionError(failure) from None


def _receive_into(socket: WebSocketTestSession, received: queue.Queue[dict]) -> None:
    received.put(socket.receive_json())


def until_the_review_is_on_round(client: TestClient, round_number: int) -> None:
    """Return once the review says it is writing a round.

    What the page says over its socket is taken in the order it was said,
    but not before a request that follows it; this waits for it to land.
    """
    next(reading for reading in _readings(client, DIFF_ROUTE) if reading["round"] == round_number)


def until_the_review_holds_threads(client: TestClient, count: int) -> list[dict]:
    """Return the threads the review holds, once it holds as many as the page sent."""
    return next(reading["threads"] for reading in _readings(client, CONTEXT_ROUTE) if len(reading["threads"]) == count)


def _readings(client: TestClient, route: str) -> Iterator[dict]:
    """What a route says, again and again, until the test has waited long enough."""
    deadline = time.monotonic() + SETTLE_SECONDS
    while time.monotonic() < deadline:
        yield client.get(route).json()
        time.sleep(LOOK_EVERY_SECONDS)
    failure = f"{route} never said what the test waited for"
    raise AssertionError(failure)


async def until_an_agent_waits(client: AsyncClient, headers: dict[str, str] | None = None) -> None:
    """Return once a poll for events is waiting on the review.

    A poll says an agent is there before it starts to wait, with nothing in
    between to yield to: once the review reports an agent, the poll is
    waiting, and whatever the test does next wakes it rather than lands in
    the queue ahead of it.
    """
    deadline = asyncio.get_running_loop().time() + SETTLE_SECONDS
    while asyncio.get_running_loop().time() < deadline:
        if (await client.get(DIFF_ROUTE, headers=headers)).json()["answerer_attached"]:
            return
        await asyncio.sleep(LOOK_EVERY_SECONDS)
    failure = "no agent started waiting on the review"
    raise AssertionError(failure)


async def review_has_ended(client: AsyncClient) -> bool:
    """Whether an agent asking the review for work is told it is over.

    While the review is open, what the reader has handed over comes out
    first, so the agent reads past it to what the review says once nothing
    is left.
    """
    while True:
        event = (await client.get(EVENTS_ROUTE, params=GLANCE_AT_EVENTS)).json()
        if event["type"] == "closed":
            return True
        if event["type"] == "timeout":
            return False


class RunningReview(BaseModel):
    """A review served on a real port, for a browser or another process to reach."""

    port: int

    @property
    def url(self) -> str:
        return f"http://{LOOPBACK}:{self.port}"


class ServedReview(BaseModel):
    """A server a test started, and the task serving it until the test is over."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    server: uvicorn.Server
    serving: asyncio.Task[None]


class ReviewServers:
    """Serves reviews on real ports for as long as a test runs, and stops them after it."""

    def __init__(self, reviews: ReviewFactory) -> None:
        self._reviews = reviews
        self._running: list[ServedReview] = []

    async def start(
        self,
        diff_files: list[DiffFile],
        *,
        mode: ReviewMode = ReviewMode.DIFF,
        root: Path | None = None,
        title: str = "",
    ) -> RunningReview:
        app = self._reviews.app(diff_files, mode=mode, root=root, title=title)
        # Match the command line: the default picks uvicorn's older websockets integration
        config = uvicorn.Config(app, host=LOOPBACK, port=ANY_PORT, log_level="warning", ws="websockets-sansio")
        server = uvicorn.Server(config)
        self._running.append(ServedReview(server=server, serving=asyncio.create_task(server.serve())))

        await _until_started(server)
        return RunningReview(port=server.servers[0].sockets[0].getsockname()[1])

    async def stop(self) -> None:
        for served in self._running:
            served.server.should_exit = True
            await served.serving


async def _until_started(server: uvicorn.Server) -> None:
    """Return once the server is listening."""
    deadline = asyncio.get_running_loop().time() + STARTUP_SECONDS
    while asyncio.get_running_loop().time() < deadline:
        if server.started:
            return
        await asyncio.sleep(LOOK_EVERY_SECONDS)
    failure = f"the review did not come up within {STARTUP_SECONDS} seconds"
    raise AssertionError(failure)
