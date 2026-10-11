"""The app one review is served by: its page, the routes its page and its agent call, and the guards before them."""

import asyncio
import contextlib
import os
from collections.abc import AsyncGenerator
from functools import partial
from http import HTTPMethod, HTTPStatus
from importlib.metadata import version as installed_version
from pathlib import Path
from typing import override

import structlog
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException
from starlette.responses import Response
from starlette.staticfiles import PathLike
from starlette.types import Receive, Scope, Send
from starlette.websockets import WebSocketClose

from claude_review.presentation.asgi import HTTP_SCOPE
from claude_review.presentation.body_limit import BodySizeLimit
from claude_review.presentation.broadcast import BrowserBroadcast
from claude_review.presentation.origin_guard import LocalOriginOnly
from claude_review.presentation.refusals import ALLOW_HEADER, ALLOW_SEPARATOR, answer_refusals
from claude_review.presentation.routes.api import include_api
from claude_review.presentation.security_headers import (
    POLICY_HEADER,
    SecurityHeaders,
    content_security_policy,
    inline_script_hashes,
)
from claude_review.services.reader_record_service import ReaderRecords
from claude_review.services.review.review import Review
from claude_review.services.review.review_lifetime import EndReason

log = structlog.get_logger()

# Where the page is built to; empty in a checkout whose page was never built
STATIC_DIR = Path(__file__).parent.parent / "static" / "dist"
# The page, what its build writes it in, and the folder of files its build put beside it
PAGE_NAME = "index.html"
PAGE_ENCODING = "utf-8"
ASSETS_NAME = "assets"
# Where the page is served, and where it asks for those files
PAGE_PATH = "/"
ASSETS_PATH = "/assets"
# What is asked of a file: to be fetched, or about
FILE_METHODS = frozenset({HTTPMethod.GET, HTTPMethod.HEAD})
# What the review calls itself, in its API description
API_TITLE = "Claude Review"

# How long a browser may keep what it is served, as the header says it. The
# page is asked for again whenever it is opened, so after an upgrade the
# browser runs the page the new release built, which names its new files. A
# file beside it is named by a hash of what it holds, so whatever a browser
# kept under a name is still that file: it is kept for a year, never asked
# for again.
CACHE_HEADER = "cache-control"
PAGE_CACHING = "no-cache"
SECONDS_PER_YEAR = 365 * 24 * 60 * 60
ASSET_CACHING = f"public, max-age={SECONDS_PER_YEAR}, immutable"

# The package whose release serves the review
PACKAGE_NAME = "claude-review"


def create_app(review: Review, broadcast: BrowserBroadcast, reader_records: ReaderRecords) -> FastAPI:
    """The app serving one review, opened on its content before it answers anybody.

    It serves no description of its API, nor the pages that draw one: the
    page's types are written from the routes in-process (`api_schema.py`),
    and nobody else reads a review's API.
    """
    app = FastAPI(title=API_TITLE, lifespan=partial(_opened, review), openapi_url=None, docs_url=None, redoc_url=None)

    app.state.review = review
    # Where the review tells its pages what happened, down their sockets
    app.state.broadcast = broadcast
    # What every review on the machine remembers about its reader, kept
    # outside any one of them
    app.state.settings = reader_records.settings
    app.state.guide = reader_records.guide
    # Read once: it does not change while the review runs
    app.state.release = installed_version(PACKAGE_NAME)

    # The middleware added last runs first. Outermost, the security headers
    # go on every answer, the guard's refusals too; inside them the guard, so
    # this server answers its own page and nothing else.
    app.add_middleware(BodySizeLimit)
    app.add_middleware(LocalOriginOnly, page_path=PAGE_PATH, page_files_path=ASSETS_PATH)
    app.add_middleware(SecurityHeaders)

    include_api(app)
    # Whatever a route refuses is answered here, by its kind
    answer_refusals(app)

    serve_the_page(app, STATIC_DIR)

    return app


def serve_the_page(app: FastAPI, built: Path) -> None:
    """Serve the page at the root, and the files its build put beside it — nothing else.

    Every other path, and every method a route does not take, is refused by
    the router, as it refuses them: a page served under any path no route
    claims would answer for the routes too, and a wrong method on one would
    be refused by a file server that does not know which methods it takes.
    A checkout whose page was never built serves the routes and no page.
    """
    page = built / PAGE_NAME
    if page.is_file():
        app.add_api_route(PAGE_PATH, PageFile(page), methods=["GET"], include_in_schema=False)
    assets = built / ASSETS_NAME
    if assets.is_dir():
        app.mount(ASSETS_PATH, AssetFiles(directory=assets), name=ASSETS_NAME)


class PageFile:
    """The review's page, which asks for everything else itself, served with the policy of what it may run.

    Read whole each time it is asked for, as the files beside it are, so a
    page built again is served as built: the policy names each of its inline
    scripts by its hash, and so is taken from the very bytes served.
    """

    def __init__(self, page: Path) -> None:
        self._page = page

    async def __call__(self) -> HTMLResponse:
        document = await asyncio.to_thread(self._page.read_bytes)
        policy = content_security_policy(inline_script_hashes(document.decode(PAGE_ENCODING)))
        return HTMLResponse(document, headers={POLICY_HEADER: policy, CACHE_HEADER: PAGE_CACHING})


class AssetFiles(StaticFiles):
    """The files the page's build put beside it: fetched, never opened as a socket, and kept for good.

    A socket opened here is turned away the way the router turns away one it
    has no route for, rather than reaching a file server that cannot answer it.
    Any other method is refused naming the ones a file takes, which the file
    server would leave unsaid.
    """

    @override
    def file_response(
        self, full_path: PathLike, stat_result: os.stat_result, scope: Scope, status_code: int = HTTPStatus.OK
    ) -> Response:
        served = super().file_response(full_path, stat_result, scope, status_code)
        served.headers[CACHE_HEADER] = ASSET_CACHING
        return served

    @override
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != HTTP_SCOPE:
            await WebSocketClose()(scope, receive, send)
            return
        if scope["method"] not in FILE_METHODS:
            taken = ALLOW_SEPARATOR.join(sorted(FILE_METHODS))
            raise HTTPException(HTTPStatus.METHOD_NOT_ALLOWED, headers={ALLOW_HEADER: taken})
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
