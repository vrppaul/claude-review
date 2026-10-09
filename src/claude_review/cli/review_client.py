"""Calling a review served on this machine, the way its agent does.

Straight to loopback with http.client rather than through urllib: urllib
sends even 127.0.0.1 through whatever proxy the environment names, and no
proxy belongs between an agent and a review on the same machine.

Whatever goes wrong comes back as one `ReviewCallError` whose message says
what happened in a line, because these calls run in an agent's loop, where
a traceback says nothing about what to do next.
"""

import http.client
from http import HTTPMethod, HTTPStatus
from urllib.parse import quote, urlencode

from pydantic import BaseModel, TypeAdapter, ValidationError

from claude_review.domain.models import Thread
from claude_review.hosting.address import LOOPBACK
from claude_review.presentation.schemas import (
    ContextResponse,
    EventResponse,
    PointRequest,
    PointResponse,
    ProgressRequest,
    ReplyRequest,
    RoundResponse,
    SayRequest,
    ShowRequest,
    StatusRequest,
)

# How long an ordinary call may take: the review answers at once
CALL_SECONDS = 10.0
# Taking the diff again runs git over the whole tree, and a call given up on
# too early is made again by whoever made it, writing a second tree
RETAKE_SECONDS = 120.0
# How much longer than its own wait a poll for events may take to answer
WAIT_MARGIN_SECONDS = 10.0

JSON_HEADERS = {"Content-Type": "application/json"}

EVENTS_ROUTE = "/api/events"
CONTEXT_ROUTE = "/api/context"
THREADS_ROUTE = "/api/context/threads"
REPLY_ROUTE = "/api/reply"
SAY_ROUTE = "/api/say"
PROGRESS_ROUTE = "/api/progress"
STATUS_ROUTE = "/api/status"
SHOW_ROUTE = "/api/show"
POINT_ROUTE = "/api/point"
RETAKE_ROUTE = "/api/round"
# What the poll for events calls how long it may wait
WAIT_SECONDS_PARAMETER = "wait_seconds"

# The parts of a request a refused field is named under, which say nothing
# to whoever typed the command
REQUEST_PARTS = frozenset({"body", "query", "path"})

# What the review answers, read as what each answer should be. The events
# are one kind told apart by their `type`, and printed back as they came.
EVENTS = TypeAdapter[EventResponse](EventResponse)
CONTEXT_ANSWER = TypeAdapter(ContextResponse)
THREAD_ANSWER = TypeAdapter(Thread)
POINT_ANSWER = TypeAdapter(PointResponse)
RETAKE_ANSWER = TypeAdapter(RoundResponse)


class ReviewCallError(Exception):
    """Raised when a call to the review fails; the message says how, in a line."""


class FieldRefusal(BaseModel):
    """One field a request had wrong, as pydantic and FastAPI both describe it."""

    loc: tuple[str | int, ...]
    msg: str


class Refusal(BaseModel):
    """Why the review refused a request: said in words, or field by field."""

    detail: str | list[FieldRefusal]


class ReviewClient:
    """Calls one review, by the port it is served on."""

    def __init__(self, port: int) -> None:
        self._port = port

    def next_event(self, wait_seconds: float) -> EventResponse:
        """The next thing the reader hands over, or why there is none, waiting up to `wait_seconds`."""
        route = f"{EVENTS_ROUTE}?{urlencode({WAIT_SECONDS_PARAMETER: wait_seconds})}"
        return self._read(EVENTS, self._call(HTTPMethod.GET, route, timeout=wait_seconds + WAIT_MARGIN_SECONDS))

    def context(self) -> ContextResponse:
        """The review as it stands: an index of its threads, and the panel in short."""
        return self._read(CONTEXT_ANSWER, self._call(HTTPMethod.GET, CONTEXT_ROUTE))

    def thread(self, thread_id: str) -> Thread:
        """One thread in full, its images handed over."""
        route = f"{THREADS_ROUTE}/{quote(thread_id, safe='')}"
        return self._read(THREAD_ANSWER, self._call(HTTPMethod.GET, route))

    def reply(self, request: ReplyRequest) -> None:
        self._call(HTTPMethod.POST, REPLY_ROUTE, request)

    def say(self, request: SayRequest) -> None:
        self._call(HTTPMethod.POST, SAY_ROUTE, request)

    def report_progress(self, request: ProgressRequest) -> None:
        self._call(HTTPMethod.POST, PROGRESS_ROUTE, request)

    def report_status(self, request: StatusRequest) -> None:
        self._call(HTTPMethod.POST, STATUS_ROUTE, request)

    def show(self, request: ShowRequest) -> None:
        self._call(HTTPMethod.POST, SHOW_ROUTE, request)

    def point(self, request: PointRequest) -> PointResponse:
        return self._read(POINT_ANSWER, self._call(HTTPMethod.POST, POINT_ROUTE, request))

    def retake(self) -> RoundResponse:
        """Take the diff again, which the reviews on screen then reload."""
        return self._read(RETAKE_ANSWER, self._call(HTTPMethod.POST, RETAKE_ROUTE, timeout=RETAKE_SECONDS))

    def _call(
        self, method: HTTPMethod, route: str, request: BaseModel | None = None, *, timeout: float = CALL_SECONDS
    ) -> bytes:
        """Make one call, and return what the review answered once it says yes."""
        connection = http.client.HTTPConnection(LOOPBACK, self._port, timeout=timeout)
        try:
            if request is None:
                connection.request(method, route)
            else:
                connection.request(method, route, body=request.model_dump_json(), headers=JSON_HEADERS)
            response = connection.getresponse()
            answer = response.read()
        except TimeoutError as error:
            msg = "the review did not answer in time"
            raise ReviewCallError(msg) from error
        except (OSError, http.client.HTTPException) as error:
            msg = f"no review is listening on port {self._port}: {error}"
            raise ReviewCallError(msg) from error
        finally:
            connection.close()
        if response.status >= HTTPStatus.BAD_REQUEST:
            msg = f"the review refused this ({response.status}): {_reason(answer)}"
            raise ReviewCallError(msg)
        return answer

    def _read[Answer](self, kind: TypeAdapter[Answer], answer: bytes) -> Answer:
        """Read an answer as what it should be, or say that it was not."""
        try:
            return kind.validate_json(answer)
        except ValidationError as error:
            msg = f"the review on port {self._port} answered something this command cannot read: {error}"
            raise ReviewCallError(msg) from error


def fields_said_wrong(refusals: list[FieldRefusal]) -> str:
    """Name each field a request had wrong, and why, on one line."""
    return "; ".join(f"{'.'.join(str(part) for part in refusal.loc)}: {refusal.msg}" for refusal in refusals)


def _reason(answer: bytes) -> str:
    """Why the review refused, from what it answered: its words, or what was wrong with each field."""
    try:
        refusal = Refusal.model_validate_json(answer)
    except ValidationError:
        return answer.decode(errors="replace").strip()
    if isinstance(refusal.detail, str):
        return refusal.detail
    return fields_said_wrong([_as_typed(field) for field in refusal.detail])


def _as_typed(refusal: FieldRefusal) -> FieldRefusal:
    """A field the review refused, named as whoever typed the command knows it.

    The review names it under the part of the request it came in — `body`,
    `query`, `path` — which says nothing to them.
    """
    location = refusal.loc
    named = location[1:] if location and location[0] in REQUEST_PARTS else location
    return refusal.model_copy(update={"loc": named})
