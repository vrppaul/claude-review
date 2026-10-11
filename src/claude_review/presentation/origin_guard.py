"""Refuse requests that did not come from the review's own page.

The server binds to loopback with no authentication, which is safe only for
as long as loopback means "this machine, this page". `admits` is the whole
rule; this says what breaks that promise without it.

A page on any domain can point that domain at 127.0.0.1 — a DNS rebind — and
the browser will then treat this server as same-origin and let the page read
its responses: the whole working tree, and any file in the repository.

WebSockets are worse: the same-origin policy does not apply to them at all,
so any page the developer has open can connect. That would let it read what
the server pushes, and — since the review ends when the last socket closes —
throw away an unsent review by connecting and disconnecting once.

And a page needs no answer to do harm. One on another port of this machine
asks with an image or a `no-cors` fetch, which carries no Origin: it cannot
read the answer, but whatever the request does is done — and a request held
open, as the agent's poll is, holds one of the few connections the browser
keeps to this server, until the review's own page cannot load.
"""

from functools import partial
from http import HTTPStatus
from urllib.parse import urlsplit

from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from claude_review.presentation.asgi import HTTP_RESPONSE_START, HTTP_SCOPE, WEBSOCKET_CLOSE, WEBSOCKET_SCOPE
from claude_review.presentation.wire.refusal import Refusal

# Loopback names, as a Host header writes them: an IPv6 address always in brackets
LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "[::1]"})
# How a Host header sets an IPv6 address apart from the port after it, and a name from its port
IPV6_OPENS = "["
IPV6_CLOSES = "]"
PORT_SEPARATOR = ":"
# The headers that say which host a request asked for, which page sent it,
# and where the browser says it comes from (Fetch Metadata)
HOST_HEADER = "host"
ORIGIN_HEADER = "origin"
FETCH_SITE_HEADER = "sec-fetch-site"

# Where a browser says a request comes from, when it is the review's own: its
# page (`same-origin`), or no page at all (`none`: an address typed, a
# bookmark). A page on another port of this machine is `same-site`, one
# anywhere else `cross-site`.
OWN_FETCH_SITES = frozenset({"same-origin", "none"})

# What parts a folder from what is under it, in a path asked for
PATH_SEPARATOR = "/"

# What a browser sends as the Origin of a page that has none of its own: a
# sandboxed frame, a file opened from disk
OPAQUE_ORIGIN = "null"

WEB_SCHEMES = frozenset({"http", "https"})

# The close code for a handshake refused on policy grounds (RFC 6455, 7.4.1)
POLICY_VIOLATION = 1008
# What a request from anywhere but this server's own page is answered with, and told
NOT_ITS_PAGE_STATUS = HTTPStatus.FORBIDDEN
NOT_ITS_PAGE_DETAIL = "Not this server's page"


def is_local_host(value: str | None) -> bool:
    """Whether a Host header names this machine over loopback."""
    if not value:
        return False
    if value.startswith(IPV6_OPENS):
        address, _, _ = value.partition(IPV6_CLOSES)
        host = address + IPV6_CLOSES
    else:
        # The port is what follows the last separator; a name with none has no port
        name, separator, _ = value.rpartition(PORT_SEPARATOR)
        host = name if separator else value
    return host in LOCAL_HOSTS


def admits(*, host: str | None, origin: str | None, fetch_site: str | None, opens_the_page: bool) -> bool:
    """Whether a request may reach the review: the guard's whole rule, from three headers, each read once.

    - ``Host`` names this machine over loopback. A rebound domain sends the
      name the page asked for, which is not one of this machine's.
    - ``Origin``, when sent, is this server's own: the same scheme, host and
      port. Loopback is not one page: a dev server, a notebook, anything a
      package starts is another origin on this machine, and its page must not
      read this one or end it. A browser sends Origin with every write and
      every socket; a command-line client sends none.
    - ``Sec-Fetch-Site``, when sent, says the request comes from the review's
      own page or from no page. This is what gives away a read another page
      makes without CORS, which sends no Origin. The page itself and the files
      its build put beside it are not held to it: a link from another site
      opens the page, and they hold nothing of the review.

    A request without Fetch Metadata — the agent's commands, curl, a browser
    too old to send it — is judged by Host and Origin alone.
    """
    return (
        host is not None
        and is_local_host(host)
        and is_own_page(origin, host)
        and (opens_the_page or fetch_site is None or fetch_site in OWN_FETCH_SITES)
    )


def is_own_page(origin: str | None, host: str) -> bool:
    """Whether a request comes from the page this server serves, or names no page at all."""
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
        if scope["type"] != HTTP_SCOPE:
            await self.app(scope, receive, send)
            return
        await self.app(scope, receive, partial(_send_with_security_headers, send=send))


async def _send_with_security_headers(message: Message, *, send: Send) -> None:
    """Send a message on, the start of a response carrying the page's security headers unless it set its own."""
    if message["type"] == HTTP_RESPONSE_START:
        headers = MutableHeaders(scope=message)
        for name, value in SECURITY_HEADERS.items():
            headers.setdefault(name, value)
    await send(message)


class LocalOriginOnly:
    """Middleware refusing anything that is not this machine's own page.

    It is told where the page and the files beside it are served, which a
    link from another site may open.
    """

    def __init__(self, app: ASGIApp, *, page_path: str, page_files_path: str) -> None:
        self.app = app
        self._page_path = page_path
        self._page_files_path = page_files_path

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in (HTTP_SCOPE, WEBSOCKET_SCOPE):
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        allowed = admits(
            host=headers.get(HOST_HEADER),
            origin=headers.get(ORIGIN_HEADER),
            fetch_site=headers.get(FETCH_SITE_HEADER),
            opens_the_page=self._opens_the_page(scope["path"]),
        )
        if allowed:
            await self.app(scope, receive, send)
            return

        if scope["type"] == WEBSOCKET_SCOPE:
            await _reject_socket(send)
        else:
            refused = Refusal(detail=NOT_ITS_PAGE_DETAIL)
            await JSONResponse(refused.model_dump(), status_code=NOT_ITS_PAGE_STATUS)(scope, receive, send)

    def _opens_the_page(self, path: str) -> bool:
        """Whether a request asks for the page itself, or a file its build put beside it."""
        return path == self._page_path or path.startswith(self._page_files_path + PATH_SEPARATOR)


async def _reject_socket(send: Send) -> None:
    """Close the handshake before it becomes a socket."""
    await send({"type": WEBSOCKET_CLOSE, "code": POLICY_VIOLATION})
