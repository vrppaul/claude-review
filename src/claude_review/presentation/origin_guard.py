"""Refuse requests that did not come from the review's own page.

The server binds to loopback with no authentication, which is safe only for
as long as loopback means "this machine, this page". Two things break that:

A page on any domain can point that domain at 127.0.0.1 — a DNS rebind — and
the browser will then treat this server as same-origin and let the page read
its responses: the whole working tree, and any file in the repository. The
name in the ``Host`` header is what the page asked for, so checking it costs
nothing and takes the rebind away.

WebSockets are worse: the same-origin policy does not apply to them at all,
so any page the developer has open can connect. That would let it read what
the server pushes, and — since the review ends when the last socket closes —
throw away an unsent review by connecting and disconnecting once.
"""

from collections.abc import Awaitable, Callable
from urllib.parse import urlsplit

from starlette.datastructures import Headers
from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp, Receive, Scope, Send

LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "[::1]", "::1"})


def is_local_host(value: str | None) -> bool:
    """Whether a Host header names this machine over loopback."""
    if not value:
        return False
    host = value.rsplit(":", 1)[0] if not value.startswith("[") else value.split("]")[0] + "]"
    return host in LOCAL_HOSTS


def is_local_origin(value: str | None) -> bool:
    """Whether an Origin header names a page served from loopback.

    A missing Origin is allowed: a command-line client sends none, and only
    browsers — the thing being defended against — always do.
    """
    if value is None:
        return True
    if value == "null":
        return False
    parsed = urlsplit(value)
    return parsed.scheme in ("http", "https") and is_local_host(parsed.netloc)


class LocalOriginOnly:
    """Middleware refusing anything that is not this machine's own page."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        allowed = is_local_host(headers.get("host")) and is_local_origin(headers.get("origin"))
        if allowed:
            await self.app(scope, receive, send)
            return

        if scope["type"] == "websocket":
            await _reject_socket(send)
        else:
            await PlainTextResponse("Not this server's page", status_code=403)(scope, receive, send)


async def _reject_socket(send: Callable[[dict], Awaitable[None]]) -> None:
    """Close the handshake before it becomes a socket."""
    await send({"type": "websocket.close", "code": 1008})
