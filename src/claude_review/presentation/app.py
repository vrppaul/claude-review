from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from claude_review.domain.models import DiffFile
from claude_review.presentation.routes import router
from claude_review.presentation.schemas import ServerState
from claude_review.services.review_service import ReviewService

STATIC_DIR = Path(__file__).parent.parent / "static" / "dist"


def create_app(
    diff_files: list[DiffFile],
    state: ServerState,
) -> FastAPI:
    app = FastAPI(title="Claude Review")

    app.state.diff_files = diff_files
    app.state.server_state = state
    app.state.review_service = ReviewService()

    app.include_router(router)

    if STATIC_DIR.exists():
        app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

    return app
