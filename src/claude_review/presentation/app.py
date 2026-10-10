"""The app one review is served by: its page, the routes its page and its agent call, and the guards before them."""

import contextlib
from collections.abc import AsyncGenerator
from functools import partial
from importlib.metadata import version as installed_version
from pathlib import Path
from typing import override

import structlog
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.types import Receive, Scope, Send
from starlette.websockets import WebSocketClose

from claude_review.presentation.body_limit import BodySizeLimit
from claude_review.presentation.broadcast import BrowserBroadcast
from claude_review.presentation.origin_guard import LocalOriginOnly, SecurityHeaders
from claude_review.presentation.refusals import answer_refusals
from claude_review.presentation.routes.api import include_api
from claude_review.services.reader_record_service import ReaderRecords
from claude_review.services.review.review import Review
from claude_review.services.review.review_lifetime import EndReason

log = structlog.get_logger()

STATIC_DIR = Path(__file__).parent.parent / "static" / "dist"

# What the review calls itself, in its API description
API_TITLE = "Claude Review"

# The package whose release serves the review
PACKAGE_NAME = "claude-review"


def create_app(review: Review, broadcast: BrowserBroadcast, reader_records: ReaderRecords) -> FastAPI:
    """The app serving one review, opened on its content before it answers anybody."""
    app = FastAPI(title=API_TITLE, lifespan=partial(_opened, review))

    app.state.review = review
    # Where the review tells its pages what happened, down their sockets
    app.state.broadcast = broadcast
    # What every review on the machine remembers about its reader, kept
    # outside any one of them
    app.state.settings = reader_records.settings
    app.state.guide = reader_records.guide
    # Read once: it does not change while the review runs
    app.state.release = installed_version(PACKAGE_NAME)

    app.add_middleware(BodySizeLimit)
    app.add_middleware(SecurityHeaders)
    # Outermost, so it runs first: this server answers its own page and nothing else
    app.add_middleware(LocalOriginOnly)

    include_api(app)
    # Whatever a route refuses is answered here, by its kind
    answer_refusals(app)

    if STATIC_DIR.exists():
        app.mount("/", PageFiles(directory=STATIC_DIR, html=True), name="static")

    return app


class PageFiles(StaticFiles):
    """The page's own files, served under every path no route claims.

    Files are fetched, never opened as sockets: a socket opened anywhere but
    the review's own is turned away the way a router turns away one it has
    no route for, rather than reaching a file server that cannot answer it.
    """

    @override
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "websocket":
            await WebSocketClose()(scope, receive, send)
            return
        await super().__call__(scope, receive, send)


@contextlib.asynccontextmanager
async def _opened(review: Review, _app: FastAPI) -> AsyncGenerator[None]:
    """Open the review on its content before the app answers anything, whoever serves it.

    A review that cannot open is over, as a fault, and says why: whoever
    serves the app sees only that it never started.
    """
    try:
        await review.open()
    except Exception:
        log.critical("review_opening_failed", exc_info=True)
        review.lifetime.end(EndReason.FAULT)
        raise
    yield
