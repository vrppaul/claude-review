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

from functools import partial
from http import HTTPStatus
from urllib.parse import urlsplit

from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from claude_review.presentation.wire.refusal import Refusal

# Loopback names, as a Host header writes them: an IPv6 address always in brackets
LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "[::1]"})

# What a browser sends as the Origin of a page that has none of its own: a
# sandboxed frame, a file opened from disk
OPAQUE_ORIGIN = "null"

WEB_SCHEMES = frozenset({"http", "https"})

# The close code for a handshake refused on policy grounds (RFC 6455, 7.4.1)
POLICY_VIOLATION = 1008
# What a request from anywhere but this server's own page is told
NOT_ITS_PAGE = "Not this server's page"


def is_local_host(value: str | None) -> bool:
    """Whether a Host header names this machine over loopback."""
    if not value:
        return False
    host = value.split("]")[0] + "]" if value.startswith("[") else value.rsplit(":", 1)[0]
    return host in LOCAL_HOSTS


def is_own_page(origin: str | None, host: str) -> bool:
    """Whether a request comes from the page this server serves, or from no page at all.

    Same origin means the same port too. Loopback is not one page: a dev
    server, a notebook, anything a package starts is another origin on the
    same machine, and its page must not read this one or end it.

    A missing Origin is allowed: a command-line client sends none, and only
    browsers — the thing being defended against — always do.
    """
    if origin is None:
        return True
    if origin == OPAQUE_ORIGIN:
        return False
    parsed = urlsplit(origin)
    return parsed.scheme in WEB_SCHEMES and parsed.netloc.lower() == host.lower()


# The page loads nothing from anywhere else, so it can say so. This is
# defence in depth behind escaping, not a substitute for it: the inline
# script that applies the theme before first paint needs 'unsafe-inline',
# which leaves script injection possible — but not exfiltration, since
# connect-src and img-src stay on this origin.
SECURITY_HEADERS = {
    "content-security-policy": (
        "default-src 'none'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self' data:; "
        "connect-src 'self'; "
        "base-uri 'none'; "
        "form-action 'none'; "
        "frame-ancestors 'none'"
    ),
    "x-frame-options": "DENY",
    "x-content-type-options": "nosniff",
    "referrer-policy": "no-referrer",
}


class SecurityHeaders:
    """Say what the review's page is allowed to do, and who may frame it."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        await self.app(scope, receive, partial(_send_with_security_headers, send=send))


async def _send_with_security_headers(message: Message, *, send: Send) -> None:
    """Send a message on, the start of a response carrying the page's security headers unless it set its own."""
    if message["type"] == "http.response.start":
        headers = MutableHeaders(scope=message)
        for name, value in SECURITY_HEADERS.items():
            headers.setdefault(name, value)
    await send(message)


class LocalOriginOnly:
    """Middleware refusing anything that is not this machine's own page."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        host = headers.get("host")
        allowed = host is not None and is_local_host(host) and is_own_page(headers.get("origin"), host)
        if allowed:
            await self.app(scope, receive, send)
            return

        if scope["type"] == "websocket":
            await _reject_socket(send)
        else:
            refused = Refusal(detail=NOT_ITS_PAGE)
            await JSONResponse(refused.model_dump(), status_code=HTTPStatus.FORBIDDEN)(scope, receive, send)


async def _reject_socket(send: Send) -> None:
    """Close the handshake before it becomes a socket."""
    await send({"type": "websocket.close", "code": POLICY_VIOLATION})
