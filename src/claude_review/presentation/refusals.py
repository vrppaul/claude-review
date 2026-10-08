"""What a refusal answers: one table from the kind of `ReviewError` to its HTTP status.

Routes raise what went wrong and never decide how it is said. Every refusal
is answered the same way, with its message as the `detail` FastAPI uses for
its own refusals, so a caller reads one shape whoever refused.
"""

from http import HTTPStatus

import structlog
from fastapi import Request
from fastapi.responses import JSONResponse

from claude_review.domain.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    RefusedError,
    TooLargeError,
)

log = structlog.get_logger()

# What each kind of refusal answers. Read along the error's own class
# hierarchy, so the most specific kind listed wins: too large is a refusal,
# and answers as too large.
REFUSAL_STATUS: dict[type, HTTPStatus] = {
    NotFoundError: HTTPStatus.NOT_FOUND,
    BadRequestError: HTTPStatus.BAD_REQUEST,
    TooLargeError: HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
    RefusedError: HTTPStatus.UNPROCESSABLE_ENTITY,
    ConflictError: HTTPStatus.CONFLICT,
}

# A `ReviewError` of no kind in the table is a fault of this side, not the asker's
UNSORTED_REFUSAL = HTTPStatus.INTERNAL_SERVER_ERROR


async def answer_refusal(request: Request, error: Exception) -> JSONResponse:
    """Tell whoever asked why the review would not do it, under the status its kind answers."""
    status = next((REFUSAL_STATUS[kind] for kind in type(error).__mro__ if kind in REFUSAL_STATUS), UNSORTED_REFUSAL)
    log.warning("request_refused", path=request.url.path, refusal=type(error).__name__, reason=str(error))
    return JSONResponse(status_code=status, content={"detail": str(error)})
