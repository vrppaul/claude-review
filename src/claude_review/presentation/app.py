from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from claude_review.domain.models import DiffFile, ReviewMode
from claude_review.presentation.origin_guard import LocalOriginOnly, SecurityHeaders
from claude_review.presentation.routes import router
from claude_review.presentation.state import ServerState

STATIC_DIR = Path(__file__).parent.parent / "static" / "dist"


def create_app(
    diff_files: list[DiffFile],
    state: ServerState,
    mode: ReviewMode,
    title: str = "",
    root: Path | None = None,
    base: str | None = None,
) -> FastAPI:
    app = FastAPI(title="Claude Review")

    app.state.diff_files = diff_files
    app.state.server = state
    app.state.review_mode = mode
    # Names what is under review, so the UI can say so rather than only
    # listing files: which repository, and against what
    app.state.review_title = title
    # The tree that expanding a hunk's context may read from. None in modes
    # whose content did not come from a repository.
    app.state.repo_root = root
    # What the diff was taken against, so the server can retake it — with
    # whitespace ignored, or after the files change
    app.state.diff_base = base

    app.add_middleware(SecurityHeaders)
    # Outermost, so it runs first: this server answers its own page and nothing else
    app.add_middleware(LocalOriginOnly)

    app.include_router(router)

    if STATIC_DIR.exists():
        app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

    return app
