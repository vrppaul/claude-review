"""Calling a review served on this machine, the way its agent does.

Straight to loopback with http.client rather than through urllib: urllib
sends even 127.0.0.1 through whatever proxy the environment names, and no
proxy belongs between an agent and a review on the same machine.

What goes wrong in a call — no review on the port, no answer in time, a
refusal, an answer it cannot read — comes back as one `ReviewCallError`
whose message says so in a line, because these calls run in an agent's
loop, where a traceback says nothing about what to do next. A request is
sent as UTF-8 bytes, so nothing the agent can type fails on the way out.
"""

import http.client
from http import HTTPMethod, HTTPStatus
from urllib.parse import quote, urlencode

from pydantic import BaseModel, TypeAdapter, ValidationError

from claude_review.hosting.address import LOOPBACK
from claude_review.presentation.wire.agent import (
    CatchUpResponse,
    EventResponse,
    ProgressRequest,
    ReplyRequest,
    SayRequest,
    ShowRequest,
    StatusRequest,
)
from claude_review.presentation.wire.content import RetakeResponse
from claude_review.presentation.wire.refusal import FieldRefusal, Refusal
from claude_review.presentation.wire.story import StoryRequest, StoryTakenResponse
from claude_review.presentation.wire.threads import PointRequest, PointResponse, Thread

# How long an ordinary call may take: the review answers at once
CALL_SECONDS = 10.0
# Taking the diff again runs git over the whole tree, and a call given up on
# too early is made again by whoever made it, writing a second tree
RETAKE_SECONDS = 120.0
# How much longer than its own wait a poll for events may take to answer
WAIT_MARGIN_SECONDS = 10.0

# What a request's JSON is written in, as JSON always is (RFC 8259). Handed
# text, http.client writes it in Latin-1, which has no Cyrillic, no dash, no
# emoji: the body goes as bytes.
BODY_ENCODING = "utf-8"
JSON_HEADERS = {"Content-Type": "application/json"}

EVENTS_ROUTE = "/api/events"
CATCH_UP_ROUTE = "/api/catch-up"
THREADS_ROUTE = "/api/catch-up/threads"
REPLY_ROUTE = "/api/reply"
SAY_ROUTE = "/api/say"
PROGRESS_ROUTE = "/api/progress"
STATUS_ROUTE = "/api/status"
SHOW_ROUTE = "/api/show"
POINT_ROUTE = "/api/point"
RETAKE_ROUTE = "/api/retake"
STORY_ROUTE = "/api/story"
# What the poll for events calls how long it may wait
WAIT_SECONDS_PARAMETER = "wait_seconds"

# The parts of a request a refused field is named under, which say nothing
# to whoever typed the command
REQUEST_PARTS = frozenset({"body", "query", "path"})
# How a refusal names a field inside another — `anchor.file` — and joins the
# reasons for several
FIELD_PATH_SEPARATOR = "."
REASON_SEPARATOR = "; "

# What the review answers, read as what each answer should be. The events
# are one kind told apart by their `type`, and printed back as they came.
EVENTS = TypeAdapter[EventResponse](EventResponse)
CATCH_UP_ANSWER = TypeAdapter(CatchUpResponse)
THREAD_ANSWER = TypeAdapter(Thread)
POINT_ANSWER = TypeAdapter(PointResponse)
RETAKE_ANSWER = TypeAdapter(RetakeResponse)
STORY_ANSWER = TypeAdapter(StoryTakenResponse)


class ReviewCallError(Exception):
    """Raised when a call to the review fails; the message says how, in a line."""


class ReviewClient:
    """Calls one review, by the port it is served on."""

    def __init__(self, port: int) -> None:
        self._port = port

    def next_event(self, wait_seconds: float) -> EventResponse:
        """The next thing the reader hands over, or why there is none, waiting up to `wait_seconds`."""
        route = f"{EVENTS_ROUTE}?{urlencode({WAIT_SECONDS_PARAMETER: wait_seconds})}"
        return self._read(EVENTS, self._call(HTTPMethod.POST, route, timeout=wait_seconds + WAIT_MARGIN_SECONDS))

    def catch_up(self) -> CatchUpResponse:
        """The review as it stands: an index of its threads, and the panel in short."""
        return self._read(CATCH_UP_ANSWER, self._call(HTTPMethod.GET, CATCH_UP_ROUTE))

    def thread(self, thread_id: str) -> Thread:
        """One thread in full, its images handed over."""
        route = f"{THREADS_ROUTE}/{quote(thread_id, safe='')}"
        return self._read(THREAD_ANSWER, self._call(HTTPMethod.POST, route))

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

    def retake(self) -> RetakeResponse:
        """Take the diff again, which the reviews on screen then reload."""
        return self._read(RETAKE_ANSWER, self._call(HTTPMethod.POST, RETAKE_ROUTE, timeout=RETAKE_SECONDS))

    def tell_story(self, request: StoryRequest) -> StoryTakenResponse:
        """Tell the change as a story, in place of any told before, and read what the review made of it."""
        return self._read(STORY_ANSWER, self._call(HTTPMethod.PUT, STORY_ROUTE, request))

    def _call(
        self, method: HTTPMethod, route: str, request: BaseModel | None = None, *, timeout: float = CALL_SECONDS
    ) -> bytes:
        """Make one call, and return what the review answered once it says yes."""
        connection = http.client.HTTPConnection(LOOPBACK, self._port, timeout=timeout)
        try:
            if request is None:
                connection.request(method, route)
            else:
                body = request.model_dump_json().encode(BODY_ENCODING)
                connection.request(method, route, body=body, headers=JSON_HEADERS)
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
    """Name each field that was wrong, and why, on one line."""
    return REASON_SEPARATOR.join(_field_said_wrong(refusal) for refusal in refusals)


def _field_said_wrong(refusal: FieldRefusal) -> str:
    """One field and what is wrong with it; what is wrong with the whole of what was sent has no field to name."""
    field = FIELD_PATH_SEPARATOR.join(str(part) for part in refusal.loc)
    return f"{field}: {refusal.msg}" if field else refusal.msg


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
