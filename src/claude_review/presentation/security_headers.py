"""What every answer tells the browser: what the page may run and load, who may frame it, how to read it.

The page loads nothing from anywhere else, so it can say so. This is defence
in depth behind escaping, not a substitute for it. The only scripts that run
are the page's own built files and the scripts its document carries inline,
each named by its hash, so markup injected into the page runs nothing; and it
fetches, loads and sends forms to nowhere but this server. What the policy
cannot stop is a script already running that moves the page elsewhere,
carrying what it read in the address: where a page navigates is not the
policy's to say.
"""

import base64
import hashlib
from collections.abc import Sequence
from functools import partial
from html.parser import HTMLParser
from typing import override

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from claude_review.presentation.asgi import HTTP_RESPONSE_START, HTTP_SCOPE

# The header the policy is said in
POLICY_HEADER = "content-security-policy"
# Every directive of the policy but where scripts may come from, which
# depends on the document served
DIRECTIVES = (
    "default-src 'none'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data:",
    "font-src 'self' data:",
    "connect-src 'self'",
    "base-uri 'none'",
    "form-action 'none'",
    "frame-ancestors 'none'",
)
# Where scripts may come from: this server's files, then each inline script
# of the document served, by its hash
SCRIPT_DIRECTIVE = "script-src 'self'"
DIRECTIVE_SEPARATOR = "; "
SOURCE_SEPARATOR = " "
# How the policy names a script by its hash: SHA-256 of its text, in base 64,
# the text taken as UTF-8 whatever the document is written in
SCRIPT_BY_HASH = "'sha256-{digest}'"
SCRIPT_TEXT_ENCODING = "utf-8"
# An inline script is a script element with no file to fetch
SCRIPT_TAG = "script"
FILE_ATTRIBUTE = "src"
# A browser makes every line end of a document "\n" before it reads anything
# else in it, scripts included: a carriage return and a line feed, and a
# carriage return alone
CARRIAGE_RETURN_LINE_FEED = "\r\n"
CARRIAGE_RETURN = "\r"
LINE_FEED = "\n"


def content_security_policy(script_hashes: Sequence[str]) -> str:
    """The policy of a document whose inline scripts have these hashes: they and this server's files run, no other."""
    scripts = SOURCE_SEPARATOR.join([SCRIPT_DIRECTIVE, *script_hashes])
    return DIRECTIVE_SEPARATOR.join([*DIRECTIVES, scripts])


def inline_script_hashes(document: str) -> list[str]:
    """Each script an HTML document carries inline, named by its hash as the policy names one: as a browser reads it."""
    scripts = _InlineScripts()
    scripts.feed(document.replace(CARRIAGE_RETURN_LINE_FEED, LINE_FEED).replace(CARRIAGE_RETURN, LINE_FEED))
    scripts.close()
    return [_named_by_hash(text) for text in scripts.texts]


def _named_by_hash(script: str) -> str:
    """A script's text, as the policy names it by its hash."""
    digest = hashlib.sha256(script.encode(SCRIPT_TEXT_ENCODING)).digest()
    return SCRIPT_BY_HASH.format(digest=base64.b64encode(digest).decode())


class _InlineScripts(HTMLParser):
    """The text of every script a document carries inline: all of it between the tags, as the parser hands it over."""

    def __init__(self) -> None:
        super().__init__()
        self.texts: list[str] = []
        # The parts of the inline script being read; none outside one
        self._reading: list[str] | None = None

    @override
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == SCRIPT_TAG and all(name != FILE_ATTRIBUTE for name, _ in attrs):
            self._reading = []

    @override
    def handle_data(self, data: str) -> None:
        if self._reading is not None:
            self._reading.append(data)

    @override
    def handle_endtag(self, tag: str) -> None:
        if tag == SCRIPT_TAG and self._reading is not None:
            self.texts.append("".join(self._reading))
            self._reading = None


# What every answer says unless it says its own: the page document says its
# own policy, naming its inline scripts; any other answer runs none
SECURITY_HEADERS = {
    POLICY_HEADER: content_security_policy([]),
    "x-frame-options": "DENY",
    "x-content-type-options": "nosniff",
    "referrer-policy": "no-referrer",
}


class SecurityHeaders:
    """Say on every answer what the review's page is allowed to do, and who may frame it."""

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
