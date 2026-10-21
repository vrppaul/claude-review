"""What the tests share: building a review, and talking to it the way its page and its agent do.

Every test reaches a review through what the review serves — its routes and
its session socket — and never through the state behind them, so a test
says what a reader or an agent can rely on and survives that state being
rearranged.
"""

import asyncio
import contextlib
from abc import ABC, abstractmethod
from http import HTTPMethod
import queue
import subprocess
import threading
import time
from collections.abc import AsyncGenerator, Iterator, Mapping, Sequence
from pathlib import Path
from typing import override
from urllib.parse import urlencode

from anyio import EndOfStream
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient, Response
from pydantic import BaseModel, ConfigDict, TypeAdapter
from starlette.testclient import WebSocketTestSession
from starlette.types import Message, Scope

from claude_review.domain.interfaces import Clock, PageChannel, ReviewedRepository
from claude_review.domain.models import (
    FIRST_ROUND,
    Anchor,
    AnchorKind,
    CommentSeverity,
    DiffFile,
    DiffHunk,
    DiffLine,
    EpochMillis,
    FileStatus,
    LineAnchor,
    LineSide,
    LineType,
    OfConversation,
    OfFiles,
    ReviewMode,
    StoryAnchor,
    StoryBlock,
    Thread,
    Turn,
    TurnAuthor,
)
from claude_review.domain.page_events import PageEvent
from claude_review.hosting.hosted_review import HostedReview, host_review
from claude_review.hosting.ports import bind
from claude_review.hosting.review_server import ReviewServer
from claude_review.hosting.workspace import ReaderFiles, ReviewWorkspace
from claude_review.presentation.asgi import HTTP_DISCONNECT, HTTP_REQUEST, HTTP_SCOPE
from claude_review.presentation.schemas.agent import AgentWork
from claude_review.presentation.schemas.content import ReviewResponse
from claude_review.presentation.schemas.pushes import ProgressPush, Push, ServerPush
from claude_review.presentation.schemas.session import Delivery, SessionMessage, Welcome
from claude_review.repositories.git_repository import GitRepository
from claude_review.repositories.system_clock import SystemClock
from claude_review.services.review.review_lifetime import EndReason, ReviewLifetime
from claude_review.services.review_opening import OpenedRepository, ReviewOpening, open_diff
from tests.held_still import RepositoryHeldStill, change_held_still

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
# What a request handed straight to the app says it speaks
ASGI_VERSION = "3.0"
HTTP_VERSION = "1.1"

# The branch every test repository starts on, and the file its first commit holds, by its name and what is in it
DEFAULT_BRANCH = "main"
INITIAL_FILE = "initial.txt"
INITIAL_FILES = {INITIAL_FILE: "initial content\n"}
# The session a conversation a test writes is of, named on each of its entries as Claude Code names it
SESSION_ID = "63b8ade4-8f1c-4c55-9e4e-0d2a7c1b9f30"

SESSION_ROUTE = "/api/session"
# Reads what the server says down the session socket, as the page does
SESSION_MESSAGES = TypeAdapter[SessionMessage](SessionMessage)
REVIEW_ROUTE = "/api/review"
DIFF_ROUTE = "/api/diff"
CATCH_UP_ROUTE = "/api/catch-up"
CONVERSATION_ROUTE = "/api/conversation"
EVENTS_ROUTE = "/api/events"
IMAGES_ROUTE = "/api/images"
# Where the agent tells the story of the change and a page reads it, where the reader asks the agent for
# one, and where they stop the one they asked for
STORY_ROUTE = "/api/story"
STORY_REQUEST_ROUTE = "/api/story/request"
STORY_CANCEL_ROUTE = "/api/story/cancel"


# How a refusal of a method says which methods are taken, and how it parts them
ALLOW = "allow"
METHOD_SEPARATOR = ","


def methods_allowed(response: Response) -> set[str]:
    """The methods a refusal of a method names as taken, read as any client reads its Allow header."""
    return {method.strip() for method in response.headers[ALLOW].split(METHOD_SEPARATOR)}


def thread_route(thread_id: str) -> str:
    """Where one thread the review holds is read in full."""
    return f"{CATCH_UP_ROUTE}/threads/{thread_id}"


# The file most reviews here hold, and the one line it shows
REVIEWED_FILE = "src/a.py"
REVIEWED_LINE = "x = 1"
# A hunk header, for hunks whose header nothing reads
HUNK_HEADER = "@@ -1 +1 @@"

# The id the browser gives the first thread it mints, and the one a test
# names when it holds only one
FIRST_THREAD_ID = "comment-1"
# What makes a review built here the same review as another: nothing, since
# none of them is opened twice
TEST_IDENTITY = "a review under test"

# A PNG as far as anything here reads one: its signature, and enough after it to be a file
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32

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
# What is said of a review started in another event loop than its servers', where it would answer nobody
STARTED_IN_ANOTHER_LOOP = (
    "a review is started in the event loop its servers were made in: "
    "the fixture that starts one runs in the loop of the `servers` it asks for"
)


# What git reads as yes in a variable of its environment
GIT_YES = "1"


def git(repo: Path, *args: str) -> str:
    """Run a git command in the given repo and return stdout."""
    result = subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)
    return result.stdout


def write_files(root: Path, files: dict[str, str]) -> None:
    """Write each file under the root, by its path there, with what it holds."""
    for path, text in files.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text)


def committed_repository(root: Path, files: dict[str, str]) -> Path:
    """A repository at `root` whose first commit holds these files, made the one way every test makes one."""
    root.mkdir(parents=True, exist_ok=True)
    git(root, "init", "-b", DEFAULT_BRANCH)
    git(root, "config", "user.email", "test@test.com")
    git(root, "config", "user.name", "Test")
    write_files(root, files)
    git(root, "add", ".")
    git(root, "commit", "-m", "initial")
    return root


async def repository_opening(repo: Path) -> ReviewOpening:
    """What the command line opens a review of a repository's uncommitted changes on."""
    return await open_diff(repo, None, GitRepository(objects=None))


def context_line(old_number: int, new_number: int, content: str) -> DiffLine:
    """A line both sides of the diff share."""
    return DiffLine(kind=LineType.CONTEXT, old_number=old_number, new_number=new_number, content=content)


def added_line(new_number: int, content: str) -> DiffLine:
    return DiffLine(kind=LineType.ADD, new_number=new_number, content=content)


def removed_line(old_number: int, content: str) -> DiffLine:
    return DiffLine(kind=LineType.DELETE, old_number=old_number, content=content)


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


def story_anchor(block: StoryBlock, *, quote: Sequence[str] = (), outdated: bool = False) -> StoryAnchor:
    """A block of the story's words; quoting nothing, for the review to fill in, unless a quote is given."""
    return StoryAnchor(block=block, quote=list(quote), outdated=outdated)


def thread(
    anchor: Anchor,
    body: str,
    *,
    thread_id: str = FIRST_THREAD_ID,
    severity: CommentSeverity = CommentSeverity.NOTE,
    turns: list[Turn] | None = None,
    images: list[Path] | None = None,
    raised_by: TurnAuthor = TurnAuthor.READER,
    resolved: bool = False,
) -> Thread:
    """A thread as the reader sends it: an ordinary note unless it says otherwise."""
    return Thread(
        thread_id=thread_id,
        anchor=anchor,
        severity=severity,
        body=body,
        turns=turns or [],
        images=images or [],
        raised_by=raised_by,
        resolved=resolved,
    )


def line_json(
    file: str, start_line: int, end_line: int | None = None, *, side: LineSide = LineSide.NEW
) -> dict[str, object]:
    """Lines of one side of a file, as the page names them; a single line unless an end is given.

    Its quote sent empty, for the review to fill in from its diff.
    """
    return {
        "kind": AnchorKind.LINE,
        "file": file,
        "side": side,
        "start_line": start_line,
        "end_line": end_line or start_line,
        "quote": [],
        "outdated": False,
    }


def turn_json(
    author: TurnAuthor,
    body: str,
    *,
    turn_id: str,
    round_number: int = FIRST_ROUND,
    images: list[str] | None = None,
) -> dict[str, object]:
    """One turn of a thread as the page sends it back, by the id the page gave it, images named by theirs."""
    return {"turn_id": turn_id, "author": author, "body": body, "round": round_number, "images": images or []}


def thread_json(
    anchor: dict[str, object],
    body: str,
    *,
    thread_id: str = FIRST_THREAD_ID,
    severity: CommentSeverity = CommentSeverity.NOTE,
    images: list[str] | None = None,
    turns: list[dict[str, object]] | None = None,
    raised_by: TurnAuthor = TurnAuthor.READER,
    resolved: bool = False,
) -> dict[str, object]:
    """A thread as the page sends it: the reader's own ordinary note unless it says otherwise."""
    return {
        "thread_id": thread_id,
        "anchor": anchor,
        "severity": severity,
        "body": body,
        "images": images or [],
        "turns": turns or [],
        "raised_by": raised_by,
        "resolved": resolved,
    }


class RecordingPage(PageChannel):
    """Pages on screen, as a test: what they are told, in order."""

    def __init__(self) -> None:
        self.told: list[PageEvent] = []

    @override
    def tell(self, event: PageEvent) -> None:
        self.told.append(event)


class FixedClock(Clock):
    """A clock that says the moment a test set it to, until the test sets another: so a test says when things happened."""

    def __init__(self, moment: EpochMillis) -> None:
        self.moment = moment

    @override
    def now(self) -> EpochMillis:
        return self.moment


def files_opening_of(diff_files: list[DiffFile], *, title: str = "") -> ReviewOpening:
    """What a review of files read once opens on, built by the test; a change is opened by `hosted_change`."""
    return ReviewOpening(source=OfFiles(), diff_files=diff_files, title=title, identity=TEST_IDENTITY)


def conversation_opening_of(diff_files: list[DiffFile], *, title: str = "") -> ReviewOpening:
    """What a review of a conversation opens on, its turns built by the test."""
    return ReviewOpening(source=OfConversation(), diff_files=diff_files, title=title, identity=TEST_IDENTITY)


class ReviewFactory:
    """Hosts reviews the way the command line does, each a review of its own.

    A review of a repository is given room to write down its trees, as the
    command line gives it, unless the test is about one that has none.
    """

    def __init__(
        self, workspace: ReviewWorkspace, marking_workspace: ReviewWorkspace, reader_files: ReaderFiles
    ) -> None:
        self._workspace = workspace
        self._marking_workspace = marking_workspace
        self._reader_files = reader_files

    def hosted(
        self,
        opening: ReviewOpening,
        *,
        keeps_marks: bool = True,
        clock: Clock | None = None,
        repository: ReviewedRepository | None = None,
    ) -> HostedReview:
        """The review put together as the command line puts it together, over git unless the test names another."""
        reads_a_repository = isinstance(opening.source, OpenedRepository)
        workspace = self._marking_workspace if reads_a_repository and keeps_marks else self._workspace
        return host_review(
            opening,
            repository=repository or GitRepository(objects=workspace.objects),
            workspace=workspace,
            reader_files=self._reader_files,
            clock=clock or SystemClock(),
        )

    def hosted_change(
        self,
        diff_files: list[DiffFile],
        *,
        title: str = "",
        too_large: frozenset[str] = frozenset(),
        clock: Clock | None = None,
    ) -> HostedReview:
        """A review of these files as a repository's change, over a repository held still (tests/held_still.py)."""
        return self.hosted(
            change_held_still(diff_files, title=title),
            clock=clock,
            repository=RepositoryHeldStill(diff_files, too_large=too_large),
        )

    def app(self, opening: ReviewOpening, *, keeps_marks: bool = True, clock: Clock | None = None) -> FastAPI:
        """The app that serves the review, for a test that speaks to it and to nothing else."""
        return self.hosted(opening, keeps_marks=keeps_marks, clock=clock).app

    def app_of_change(
        self,
        diff_files: list[DiffFile],
        *,
        title: str = "",
        too_large: frozenset[str] = frozenset(),
        clock: Clock | None = None,
    ) -> FastAPI:
        """The app that serves a review of these files as a repository's change, held still."""
        return self.hosted_change(diff_files, title=title, too_large=too_large, clock=clock).app


@contextlib.asynccontextmanager
async def http_client(app: FastAPI) -> AsyncGenerator[AsyncClient]:
    """Talk to a review over HTTP, as the agent's commands do: no page, so no Origin.

    The review is opened first, as a server opens it before it answers
    anybody; the transport alone would hand the app requests without that.
    """
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url=LOCAL_ORIGIN) as client,
    ):
        yield client


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


def open_session_at(client: TestClient, route: str) -> WebSocketTestSession:
    """Open a socket at any route, the way the page opens its own."""
    return client.websocket_connect(route)


def message_said(said: str | bytes) -> SessionMessage:
    """One thing the server said down the session socket, read as the page reads it."""
    return SESSION_MESSAGES.validate_json(said)


class PushSource(ABC):
    """A page's session socket as a test reads it: what the review says, a message at a time."""

    @abstractmethod
    def receive(self, *, timeout: float) -> str:
        """The next message the review says, within `timeout` seconds.

        Raises:
            TimeoutError: if none arrives in time.
        """


class HeldSession(PushSource):
    """The session socket the test client holds, read with an end to every wait.

    The test client's read blocks until something arrives, so each read
    runs on a thread of its own; a thread left waiting is let go when the
    socket closes.
    """

    def __init__(self, socket: WebSocketTestSession) -> None:
        self._socket = socket

    @override
    def receive(self, *, timeout: float) -> str:
        received: queue.Queue[str] = queue.Queue()
        threading.Thread(target=_receive_into, args=(self._socket, received), daemon=True).start()
        try:
            return received.get(timeout=timeout)
        except queue.Empty:
            failure = "nothing was said down the socket"
            raise TimeoutError(failure) from None


def welcome_of(socket: WebSocketTestSession) -> Welcome:
    """The welcome every connection starts with."""
    message = message_said(HeldSession(socket).receive(timeout=SETTLE_SECONDS))
    assert isinstance(message, Welcome), f"a connection began with {message.type}, not a welcome"
    return message


def next_push[PushT: Push](socket: WebSocketTestSession | PushSource, kind: type[PushT]) -> PushT:
    """Read what the server pushes until a push of one kind arrives.

    The socket carries more than any one test is about — a review is told
    when an agent attaches, and when a round retakes the diff — so what comes
    first is not always what the test waits for. A read that never returns
    fails the test rather than hanging it.
    """
    for push in _pushes(socket):
        if isinstance(push, kind):
            return push
    failure = f"no {kind.__name__} arrived"
    raise AssertionError(failure)


def pushes_until(socket: WebSocketTestSession | PushSource, kind: type[Push]) -> list[ServerPush]:
    """Everything the server pushes, up to and including the first push of one kind."""
    pushed: list[ServerPush] = []
    for push in _pushes(socket):
        pushed.append(push)
        if isinstance(push, kind):
            return pushed
    failure = f"no {kind.__name__} arrived"
    raise AssertionError(failure)


def work_pushed(socket: WebSocketTestSession | PushSource) -> AgentWork:
    """The work the next progress push says is under way."""
    work = next_push(socket, ProgressPush).work
    assert work is not None, "the progress push said the work was over"
    return work


def _pushes(socket: WebSocketTestSession | PushSource) -> Iterator[ServerPush]:
    """Every push delivered down a socket as it arrives, passing over welcomes, for as long as a test waits."""
    source = socket if isinstance(socket, PushSource) else HeldSession(socket)
    deadline = time.monotonic() + SETTLE_SECONDS
    while (remaining := deadline - time.monotonic()) > 0:
        try:
            said = source.receive(timeout=remaining)
        except TimeoutError:
            return
        message = message_said(said)
        if isinstance(message, Delivery):
            yield message.push


def _receive_into(socket: WebSocketTestSession, received: queue.Queue[str]) -> None:
    try:
        received.put(socket.receive_text())
    except EndOfStream:
        # The socket closed while this waited, a test having given up on it:
        # nothing more will come
        return


def review_facts(client: TestClient) -> ReviewResponse:
    """What the review says it is and where it stands, as a page opening reads it."""
    return ReviewResponse.model_validate_json(client.get(REVIEW_ROUTE).text)


def until_the_review_is_on_round(client: TestClient, round_number: int) -> None:
    """Return once the review says it is writing a round.

    What the page says over its socket is taken in the order it was said,
    but not before a request that follows it; this waits for it to land.
    """
    next(reading for reading in _readings(client, REVIEW_ROUTE) if reading["round"] == round_number)


def until_the_review_holds_threads(client: TestClient, count: int) -> list[dict]:
    """Return the threads the review holds, once it holds as many as the page sent."""
    return next(reading["threads"] for reading in _readings(client, CATCH_UP_ROUTE) if len(reading["threads"]) == count)


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
        if (await client.get(REVIEW_ROUTE, headers=headers)).json()["answerer_attached"]:
            return
        await asyncio.sleep(LOOK_EVERY_SECONDS)
    failure = "no agent started waiting on the review"
    raise AssertionError(failure)


class CallerThatLeaves:
    """An agent's poll for events whose caller goes away while it waits, as a killed `wait` does.

    Played against the app directly, the way a server hands it a request:
    the test clients run the app inside the request, so cancelling one
    cancels the other, while a real server lets a handler whose caller left
    run on.
    """

    def __init__(self) -> None:
        self._asked = False
        self.gone = asyncio.Event()

    async def receive(self) -> Message:
        """The request, then nothing until the caller goes away."""
        if not self._asked:
            self._asked = True
            return {"type": HTTP_REQUEST, "body": b"", "more_body": False}
        await self.gone.wait()
        return {"type": HTTP_DISCONNECT}

    async def send(self, message: Message) -> None:
        """Whatever is answered goes nowhere: nobody is there to read it."""

    async def poll(self, app: FastAPI, wait_seconds: float) -> None:
        """Ask the review for its next event, as this caller."""
        scope = _request_scope(HTTPMethod.POST, EVENTS_ROUTE, query={"wait_seconds": wait_seconds})
        await app(scope, self.receive, self.send)


class UploadThatBreaksOff:
    """A pasted image whose browser goes away before the last of it arrives: a tab closed mid-upload.

    Played against the app directly, as `CallerThatLeaves` is: the test
    clients hand the app the whole body and never go away in the middle of it.
    """

    def __init__(self, first_part: bytes) -> None:
        self._first_part = first_part
        self._sent_first_part = False

    async def receive(self) -> Message:
        """The first part of the image, then the browser gone."""
        if not self._sent_first_part:
            self._sent_first_part = True
            return {"type": HTTP_REQUEST, "body": self._first_part, "more_body": True}
        return {"type": HTTP_DISCONNECT}

    async def send(self, message: Message) -> None:
        """Whatever is answered goes nowhere: nobody is there to read it."""

    async def upload(self, app: FastAPI) -> None:
        """Paste the image into the review, as this browser."""
        await app(_request_scope(HTTPMethod.POST, IMAGES_ROUTE), self.receive, self.send)


def _request_scope(method: HTTPMethod, route: str, query: Mapping[str, float] | None = None) -> Scope:
    """A request as a server hands it to the app, from the review's own machine."""
    return {
        "type": HTTP_SCOPE,
        "asgi": {"version": ASGI_VERSION},
        "http_version": HTTP_VERSION,
        "method": method,
        "scheme": "http",
        "path": route,
        "raw_path": route.encode(),
        "query_string": urlencode(query or {}).encode(),
        "root_path": "",
        "headers": [(b"host", LOCAL_HOST.encode())],
        "client": (LOOPBACK, ANY_PORT),
        "server": (LOOPBACK, ANY_PORT),
    }


async def review_has_ended(client: AsyncClient) -> bool:
    """Whether an agent asking the review for work is told it is over.

    While the review is open, what the reader has handed over comes out
    first, so the agent reads past it to what the review says once nothing
    is left.
    """
    while True:
        event = (await client.post(EVENTS_ROUTE, params=GLANCE_AT_EVENTS)).json()
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
    """A review a test started, and the task serving it until the review ends."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    lifetime: ReviewLifetime
    serving: asyncio.Task[None]


class ReviewServers:
    """Serves reviews on real ports for as long as a test runs, and stops them after it."""

    def __init__(self, reviews: ReviewFactory) -> None:
        self._reviews = reviews
        self._running: list[ServedReview] = []
        # The loop the servers are stopped in, and so the one each is started in
        self._loop = asyncio.get_running_loop()

    async def start(self, opening: ReviewOpening) -> RunningReview:
        return await self._serve(self._reviews.hosted(opening))

    async def start_change(self, diff_files: list[DiffFile]) -> RunningReview:
        """A review of these files as a repository's change, held still, served."""
        return await self._serve(self._reviews.hosted_change(diff_files))

    async def _serve(self, hosted: HostedReview) -> RunningReview:
        assert asyncio.get_running_loop() is self._loop, STARTED_IN_ANOTHER_LOOP
        lifetime = hosted.review.lifetime
        # The server the command line runs, so a browser test meets the same one
        server = ReviewServer(hosted.app, lifetime)
        listening = bind(ANY_PORT, may_fall_back=False)
        self._running.append(
            ServedReview(lifetime=lifetime, serving=asyncio.create_task(server.serve_until_ended(listening)))
        )

        if not await asyncio.wait_for(server.came_up(), timeout=STARTUP_SECONDS):
            failure = "the review's server stopped before it listened"
            raise AssertionError(failure)
        return RunningReview(port=listening.getsockname()[1])

    async def stop(self) -> None:
        for served in self._running:
            served.lifetime.end(EndReason.FINISHED)
            await served.serving


@contextlib.asynccontextmanager
async def review_servers(reviews: ReviewFactory) -> AsyncGenerator[ReviewServers]:
    """Serve reviews on real ports until the block is left, and stop every one of them then.

    Entered in the event loop its reviews are reached from: a server runs in
    the loop it was started in, and answers only while that loop does.
    """
    started = ReviewServers(reviews)
    try:
        yield started
    finally:
        await started.stop()
