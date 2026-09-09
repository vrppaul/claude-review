import asyncio
from pathlib import Path

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query

from claude_review.domain.exceptions import FileWindowError
from claude_review.domain.models import Comment, DiffFile, ReviewMode
from claude_review.presentation.dependencies import (
    get_diff_files,
    get_repo_root,
    get_review_mode,
    get_review_title,
    get_state,
)
from claude_review.presentation.schemas import (
    DiffResponse,
    FileWindowResponse,
    SubmitRequest,
    SubmitResponse,
)
from claude_review.presentation.state import ServerState
from claude_review.services.file_window_service import FileWindowService
from claude_review.services.review_service import ReviewService
from claude_review.services.transcript_review_service import TranscriptReviewService

log = structlog.get_logger()

router = APIRouter(prefix="/api")


@router.get("/diff")
async def get_diff(
    diff_files: list[DiffFile] = Depends(get_diff_files),
    mode: ReviewMode = Depends(get_review_mode),
    title: str = Depends(get_review_title),
) -> DiffResponse:
    return DiffResponse(files=diff_files, mode=mode, title=title)


@router.get("/file-window")
async def get_file_window(
    path: str = Query(min_length=1),
    start: int = Query(ge=1),
    end: int = Query(ge=1),
    root: Path | None = Depends(get_repo_root),
) -> FileWindowResponse:
    """Serve lines a hunk left out, so the reader can widen its context."""
    if root is None:
        raise HTTPException(status_code=404, detail="No repository to read from")

    try:
        window = FileWindowService().read_window(root, path, start, end)
    except FileWindowError as e:
        log.warning("file_window_refused", path=path, reason=str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e

    return FileWindowResponse(start=window.start, lines=window.lines, total=window.total)


@router.post("/heartbeat")
async def heartbeat(state: ServerState = Depends(get_state)) -> dict[str, str]:
    state.last_heartbeat = asyncio.get_running_loop().time()
    return {"status": "ok"}


@router.post("/submit")
async def submit_review(
    request: SubmitRequest,
    state: ServerState = Depends(get_state),
    mode: ReviewMode = Depends(get_review_mode),
    diff_files: list[DiffFile] = Depends(get_diff_files),
) -> SubmitResponse:
    if state.shutdown_event.is_set():
        raise HTTPException(status_code=409, detail="Review already submitted")

    comments = [
        Comment(
            file=c.file,
            side=c.side,
            start_line=c.start_line,
            end_line=c.end_line,
            body=c.body,
        )
        for c in request.comments
    ]

    if mode == ReviewMode.TRANSCRIPT:
        result = TranscriptReviewService().format_review(comments, request.body, diff_files)
    else:
        result = ReviewService().format_review(comments, body=request.body)

    state.result = result.markdown
    state.shutdown_event.set()
    log.info("review_submitted", comment_count=result.comment_count)

    return SubmitResponse(
        markdown=result.markdown,
        comment_count=result.comment_count,
    )
