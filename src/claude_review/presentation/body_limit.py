"""Refuse a request body larger than anything the review is ever sent.

Every list and string a request carries has its own cap, but those are
checked once the body has been read and parsed in full. The body itself is
capped here, as it arrives: by the length it announces, and by what has
actually come when it announces none.
"""

from fastapi import HTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from claude_review.services.image_service import MAX_IMAGE_BYTES

# The largest thing sent is a pasted image, uploaded as the body itself. A
# round of several hundred threads is a fraction of that.
MAX_REQUEST_BYTES = MAX_IMAGE_BYTES + 1024 * 1024

TOO_LARGE = 413
TOO_LARGE_DETAIL = "The request is larger than anything this review takes"


class BodySizeLimit:
    """Middleware capping the size of every HTTP request body."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        await self.app(scope, CountedReceive(receive, _announced_length(scope)), send)


class CountedReceive:
    """The request's body as it arrives, refused the moment it grows too large.

    Raised as an HTTP error from inside the read, so whatever is reading the
    body answers 413 rather than parsing what has come so far.
    """

    def __init__(self, receive: Receive, announced: int | None) -> None:
        self._receive = receive
        self._announced = announced
        self._received = 0

    async def __call__(self) -> Message:
        if self._announced is not None and self._announced > MAX_REQUEST_BYTES:
            raise HTTPException(status_code=TOO_LARGE, detail=TOO_LARGE_DETAIL)
        message = await self._receive()
        if message["type"] == "http.request":
            self._received += len(message.get("body", b""))
            if self._received > MAX_REQUEST_BYTES:
                raise HTTPException(status_code=TOO_LARGE, detail=TOO_LARGE_DETAIL)
        return message


def _announced_length(scope: Scope) -> int | None:
    """The length the request says its body has, if it says one that can be read."""
    for name, value in scope["headers"]:
        if name == b"content-length":
            return int(value) if value.isdigit() else None
    return None
