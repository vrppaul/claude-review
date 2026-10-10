"""What a refusal answers: one table from the kind of `ReviewError` to its HTTP status.

Routes raise what went wrong and never decide how it is said. Every refusal
is answered the same way, with its message as the `detail` FastAPI uses for
its own refusals, so a caller reads one shape whoever refused.

The same tables say, in the API's description, how each route may refuse:
a route names the kinds it raises and what it takes in, and is described
with their statuses and no others, those it may be refused for what it
takes in said to be so.

A request whose caller went away before it had sent all of it is no refusal:
nobody is left to answer, and nothing went wrong on either side.
"""

from collections.abc import Set
from enum import StrEnum, auto
from functools import partial
from http import HTTPStatus

import structlog
from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException
from starlette.requests import ClientDisconnect
from starlette.routing import Match, Route

from claude_review.domain.exceptions import (
    ConflictError,
    InvalidRequestError,
    NotFoundError,
    RefusedError,
    ReviewError,
    TooLargeError,
)
from claude_review.presentation.body_limit import TOO_LARGE_STATUS
from claude_review.presentation.wire.refusal import Refusal

log = structlog.get_logger()


# What each kind of refusal answers. Starlette answers an error with the
# handler of the nearest kind along its class hierarchy, so too large — a
# refusal of its own — answers as too large. A bare `ReviewError` is none of
# these, and goes unanswered here: it is a fault of this side, and the server
# says so as it says any other.
REFUSAL_STATUS: dict[type[ReviewError], HTTPStatus] = {
    NotFoundError: HTTPStatus.NOT_FOUND,
    InvalidRequestError: HTTPStatus.BAD_REQUEST,
    TooLargeError: HTTPStatus.CONTENT_TOO_LARGE,
    RefusedError: HTTPStatus.UNPROCESSABLE_CONTENT,
    ConflictError: HTTPStatus.CONFLICT,
}


class Takes(StrEnum):
    """What a route takes in, and so what it may be refused for it: by FastAPI on the way, or as the body is read."""

    NOTHING = auto()
    # A query or a path, checked against the route's parameters
    PARAMETERS = auto()
    # A JSON body, read and checked against the route's model
    JSON_BODY = auto()
    # A body read as it comes, never parsed: only its size is refused
    RAW_BODY = auto()


# FastAPI's own answer to a body it cannot read as JSON at all — bytes that
# are not even text — and to a parameter or a field it found wrong
UNREADABLE_BODY = HTTPStatus.BAD_REQUEST
WRONG_INPUT = HTTPStatus.UNPROCESSABLE_CONTENT
# What a route may be refused for what it takes in
REFUSED_FOR_INPUT: dict[Takes, frozenset[HTTPStatus]] = {
    Takes.NOTHING: frozenset(),
    Takes.PARAMETERS: frozenset({WRONG_INPUT}),
    Takes.JSON_BODY: frozenset({UNREADABLE_BODY, WRONG_INPUT, TOO_LARGE_STATUS}),
    Takes.RAW_BODY: frozenset({TOO_LARGE_STATUS}),
}
# What FastAPI reads an answer a route documents by: the model it is said
# in, and the words it is described with
RESPONSE_MODEL = "model"
RESPONSE_DESCRIPTION = "description"
# The OpenAPI extension that marks a refusal a route may give for what it
# takes in: said where a reader of the API sees it, and where a test can hold
# it to what the route's description says it takes
INPUT_REFUSAL_EXTENSION = "x-refused-for-its-input"
# The header a refusal of a method names the methods a path does take in
ALLOW_HEADER = "Allow"
ALLOW_SEPARATOR = ", "


# What a request whose caller went away is answered with. Nobody reads it; the
# server still owes the request an answer.
CUT_OFF_STATUS = HTTPStatus.BAD_REQUEST


def refusals(*kinds: type[ReviewError], takes: Takes) -> dict[int | str, dict[str, object]]:
    """What a route may answer instead of doing what it was asked: what it raises, and what it is refused on the way.

    A route names the kinds of refusal it raises and what it takes in; the
    status of each comes from the tables, so a route never restates one.
    """
    return documented({status_of(kind) for kind in kinds}, for_input=REFUSED_FOR_INPUT[takes])


def documented(
    statuses: Set[HTTPStatus], *, for_input: Set[HTTPStatus] = frozenset()
) -> dict[int | str, dict[str, object]]:
    """Statuses a route may answer with, as the API describes them: each a refusal, said as every refusal is.

    Those a route may give for what it takes in say so. In order, so the API is
    described the same way every time it is written.
    """
    return {status: _refusal(status, for_input=status in for_input) for status in sorted({*statuses, *for_input})}


def _refusal(status: HTTPStatus, *, for_input: bool) -> dict[str, object]:
    """One status a route may refuse with, as the API describes it."""
    described: dict[str, object] = {RESPONSE_MODEL: Refusal, RESPONSE_DESCRIPTION: status.phrase}
    if for_input:
        described[INPUT_REFUSAL_EXTENSION] = True
    return described


def status_of(kind: type[ReviewError]) -> HTTPStatus:
    """The status a kind of refusal is answered with: that of the nearest kind the table names, as Starlette picks it.

    Raises:
        ValueError: if the table names no kind it is, which would make it no refusal at all.
    """
    nearest = min((named for named in REFUSAL_STATUS if issubclass(kind, named)), key=kind.__mro__.index, default=None)
    if nearest is None:
        msg = f"{kind.__name__} is answered with no status: it is no refusal"
        raise ValueError(msg)
    return REFUSAL_STATUS[nearest]


def answer_refusals(app: FastAPI) -> None:
    """Have the app answer every kind of refusal with its status, and drop a request cut off."""
    for kind, status in REFUSAL_STATUS.items():
        app.add_exception_handler(kind, partial(answer_refusal, status=status))
    app.add_exception_handler(ClientDisconnect, drop_cut_off_request)
    app.add_exception_handler(HTTPException, answer_with_every_method)


async def answer_refusal(request: Request, error: Exception, *, status: HTTPStatus) -> JSONResponse:
    """Tell whoever asked why the review would not do it."""
    log.warning("request_refused", path=request.url.path, refusal=type(error).__name__, reason=str(error))
    return JSONResponse(status_code=status, content=Refusal(detail=str(error)).model_dump())


async def answer_with_every_method(request: Request, error: Exception) -> Response:
    """Answer a refusal the router made itself; one of a method names every method taken at the path.

    The router names only the methods of the first route it found at the
    path, so a path one route reads and another writes would say it can only
    be read. What refused names what it takes, and so does every route at
    the path: the page's files, which no route serves, say so themselves.
    """
    match error:
        case HTTPException(status_code=HTTPStatus.METHOD_NOT_ALLOWED):
            taken = ALLOW_SEPARATOR.join(sorted(methods_named_by(error) | methods_taken_at(request)))
            return await http_exception_handler(
                request, HTTPException(error.status_code, error.detail, headers={ALLOW_HEADER: taken})
            )
        case HTTPException():
            return await http_exception_handler(request, error)
        case _:
            raise error


def methods_named_by(error: HTTPException) -> set[str]:
    """The methods a refusal of a method already names in its own Allow header, if it has one."""
    named = (error.headers or {}).get(ALLOW_HEADER)
    return set(named.split(ALLOW_SEPARATOR)) if named else set()


def methods_taken_at(request: Request) -> set[str]:
    """Every method some route takes at the path asked for."""
    taken: set[str] = set()
    for route in request.app.routes:
        if not isinstance(route, Route) or not route.methods:
            continue
        # A route whose path matches and whose methods do not matches in part
        matched, _ = route.matches(request.scope)
        if matched == Match.PARTIAL:
            taken |= route.methods
    return taken


async def drop_cut_off_request(request: Request, _error: Exception) -> Response:
    """Let a request go whose caller left mid-way: a tab closed while an image was still uploading."""
    log.info("request_cut_off", path=request.url.path)
    return Response(status_code=CUT_OFF_STATUS)
