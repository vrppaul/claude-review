from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from claude_review.domain.models import DiffFile, GuideState, ReaderFiles, ReaderSettings, ReviewMode, ReviewWorkspace
from claude_review.presentation.body_limit import BodySizeLimit
from claude_review.presentation.dependencies import reader_record_service
from claude_review.presentation.origin_guard import LocalOriginOnly, SecurityHeaders
from claude_review.presentation.routes import router
from claude_review.presentation.state import ServerState

STATIC_DIR = Path(__file__).parent.parent / "static" / "dist"


def create_app(
    diff_files: list[DiffFile],
    state: ServerState,
    mode: ReviewMode,
    workspace: ReviewWorkspace,
    reader_files: ReaderFiles,
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
    # The directory this review owns: the trees it writes down and the
    # images pasted into it. It goes with the review, which is what keeps
    # both out of the repository under review.
    app.state.workspace = workspace
    # What every review on the machine remembers about its reader, kept
    # outside any one of them. One service each for the review's lifetime, so
    # changes arriving together are made one after the other.
    app.state.settings = reader_record_service(reader_files.settings, ReaderSettings)
    app.state.guide = reader_record_service(reader_files.guide, GuideState)

    app.add_middleware(BodySizeLimit)
    app.add_middleware(SecurityHeaders)
    # Outermost, so it runs first: this server answers its own page and nothing else
    app.add_middleware(LocalOriginOnly)

    app.include_router(router)

    if STATIC_DIR.exists():
        app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

    return app
