"""The app one review is served by: its page, the routes its page and its agent call, and the guards before them."""

import contextlib
from collections.abc import AsyncGenerator
from functools import partial
from importlib.metadata import version as installed_version
from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

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
# The page, and the files its build put beside it, where it asks for them
PAGE_FILE = STATIC_DIR / "index.html"
ASSETS_DIR = STATIC_DIR / "assets"
ASSETS_PATH = "/assets"

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
        serve_the_page(app)

    return app


def serve_the_page(app: FastAPI) -> None:
    """Serve the page at the root, and the files its build put beside it — nothing else.

    Every other path, and every method a route does not take, is refused by
    the router, as it refuses them: a page served under any path no route
    claims would answer for the routes too, and a wrong method on one would
    be refused by a file server that does not know which methods it takes.
    """
    app.add_api_route("/", the_page, methods=["GET"], include_in_schema=False)
    app.mount(ASSETS_PATH, StaticFiles(directory=ASSETS_DIR), name="assets")


async def the_page() -> FileResponse:
    """The review's page, which asks for everything else itself."""
    return FileResponse(PAGE_FILE)


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
