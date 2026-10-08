"""What a refusal answers: one table from the kind of `ReviewError` to its HTTP status.

Routes raise what went wrong and never decide how it is said. Every refusal
is answered the same way, with its message as the `detail` FastAPI uses for
its own refusals, so a caller reads one shape whoever refused.
"""

from functools import partial
from http import HTTPStatus

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from claude_review.domain.exceptions import (
    ConflictError,
    InvalidRequestError,
    NotFoundError,
    RefusedError,
    ReviewError,
    TooLargeError,
)

log = structlog.get_logger()


class UploadCutOffError(InvalidRequestError):
    """Raised when the browser went away in the middle of an upload: a refusal HTTP itself causes."""


# What each kind of refusal answers. Starlette answers an error with the
# handler of the nearest kind along its class hierarchy, so too large — a
# refusal of its own — answers as too large. A bare `ReviewError` is none of
# these, and goes unanswered here: it is a fault of this side, and the server
# says so as it says any other.
REFUSAL_STATUS: dict[type[ReviewError], HTTPStatus] = {
    NotFoundError: HTTPStatus.NOT_FOUND,
    InvalidRequestError: HTTPStatus.BAD_REQUEST,
    TooLargeError: HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
    RefusedError: HTTPStatus.UNPROCESSABLE_ENTITY,
    ConflictError: HTTPStatus.CONFLICT,
}


def answer_refusals(app: FastAPI) -> None:
    """Have the app answer every kind of refusal with its status."""
    for kind, status in REFUSAL_STATUS.items():
        app.add_exception_handler(kind, partial(answer_refusal, status=status))


async def answer_refusal(request: Request, error: Exception, *, status: HTTPStatus) -> JSONResponse:
    """Tell whoever asked why the review would not do it."""
    log.warning("request_refused", path=request.url.path, refusal=type(error).__name__, reason=str(error))
    return JSONResponse(status_code=status, content={"detail": str(error)})
