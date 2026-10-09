"""The app one review is served by: its page, the routes its page and its agent call, and the guards before them."""

import contextlib
from collections.abc import AsyncGenerator
from functools import partial
from importlib.metadata import version as installed_version
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from claude_review.domain.models import GuideState, ReaderFiles, ReaderSettings
from claude_review.presentation.body_limit import BodySizeLimit
from claude_review.presentation.broadcast import BrowserBroadcast
from claude_review.presentation.origin_guard import LocalOriginOnly, SecurityHeaders
from claude_review.presentation.refusals import answer_refusals
from claude_review.presentation.routes.api import include_api
from claude_review.repositories.json_record_store import JsonRecordStore
from claude_review.services.reader_record_service import ReaderRecordService
from claude_review.services.review.review import Review

STATIC_DIR = Path(__file__).parent.parent / "static" / "dist"

# What the review calls itself, in its API description
API_TITLE = "Claude Review"

# The package whose release serves the review
PACKAGE_NAME = "claude-review"


def create_app(review: Review, broadcast: BrowserBroadcast, reader_files: ReaderFiles) -> FastAPI:
    """The app serving one review, opened on its content before it answers anybody."""
    app = FastAPI(title=API_TITLE, lifespan=partial(_opened, review))

    app.state.review = review
    # Where the review tells its pages what happened, down their sockets
    app.state.broadcast = broadcast
    # What every review on the machine remembers about its reader, kept
    # outside any one of them. One service each for the review's lifetime, so
    # changes arriving together are made one after the other.
    app.state.settings = _kept_record(reader_files.settings, ReaderSettings)
    app.state.guide = _kept_record(reader_files.guide, GuideState)
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
        app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

    return app


@contextlib.asynccontextmanager
async def _opened(review: Review, _app: FastAPI) -> AsyncGenerator[None]:
    """Open the review on its content before the app answers anything, whoever serves it."""
    await review.open()
    yield


def _kept_record[Record: BaseModel](path: Path, record_type: type[Record]) -> ReaderRecordService[Record]:
    """One record about the reader, kept in its file, for as long as the review runs."""
    return ReaderRecordService(JsonRecordStore(path, record_type), record_type)
