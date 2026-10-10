"""What a refusal answers: one table from the kind of `ReviewError` to its HTTP status.

Routes raise what went wrong and never decide how it is said. Every refusal
is answered the same way, with its message as the `detail` FastAPI uses for
its own refusals, so a caller reads one shape whoever refused.

A request whose caller went away before it had sent all of it is no refusal:
nobody is left to answer, and nothing went wrong on either side.
"""

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


# What a request is turned away with when it is not from this server's own
# page: the origin guard's refusal, which any route may answer
NOT_THIS_PAGE = HTTPStatus.FORBIDDEN
# The header a refusal of a method names the methods a path does take in
ALLOW_HEADER = "Allow"
ALLOW_SEPARATOR = ", "


# What a request whose caller went away is answered with. Nobody reads it; the
# server still owes the request an answer.
CUT_OFF_STATUS = HTTPStatus.BAD_REQUEST


def documented_refusals() -> dict[int | str, dict[str, object]]:
    """What any route may answer instead of doing what it was asked, as the API describes it.

    Every refusal is said the same way, whichever route refused, so every
    route says it may answer each of them — FastAPI's own refusal of what a
    request had wrong, under 422, among them.
    """
    statuses = [*REFUSAL_STATUS.values(), NOT_THIS_PAGE]
    return {status: {"model": Refusal, "description": status.phrase} for status in statuses}


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
    be read.
    """
    match error:
        case HTTPException(status_code=HTTPStatus.METHOD_NOT_ALLOWED):
            taken = ALLOW_SEPARATOR.join(sorted(methods_taken_at(request)))
            return await http_exception_handler(
                request, HTTPException(error.status_code, error.detail, headers={ALLOW_HEADER: taken})
            )
        case HTTPException():
            return await http_exception_handler(request, error)
        case _:
            raise error


def methods_taken_at(request: Request) -> set[str]:
    """Every method some route takes at the path asked for."""
    taken: set[str] = set()
    for route in request.app.routes:
        if isinstance(route, Route) and route.methods and route.matches(request.scope)[0] == Match.PARTIAL:
            taken |= route.methods
    return taken


async def drop_cut_off_request(request: Request, _error: Exception) -> Response:
    """Let a request go whose caller left mid-way: a tab closed while an image was still uploading."""
    log.info("request_cut_off", path=request.url.path)
    return Response(status_code=CUT_OFF_STATUS)
