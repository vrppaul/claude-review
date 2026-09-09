import asyncio
from pathlib import Path

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, WebSocket, WebSocketDisconnect

from claude_review.domain.exceptions import FileWindowError
from claude_review.domain.models import Comment, DiffFile, ReviewMode, ThreadQuestion
from claude_review.presentation.dependencies import (
    get_diff_base,
    get_diff_files,
    get_repo_root,
    get_review_mode,
    get_review_title,
    get_state,
)
from claude_review.presentation.schemas import (
    AskRequest,
    DiffResponse,
    EventResponse,
    FileWindowResponse,
    ReplyRequest,
    SubmitRequest,
    SubmitResponse,
)
from claude_review.presentation.state import ServerState
from claude_review.repositories.git_repository import GitRepository
from claude_review.services.diff_service import DiffService
from claude_review.services.file_window_service import FileWindowService
from claude_review.services.review_service import ReviewService
from claude_review.services.transcript_review_service import TranscriptReviewService

log = structlog.get_logger()

router = APIRouter(prefix="/api")


@router.get("/diff")
async def get_diff(
    request: Request,
    ignore_whitespace: bool = Query(default=False),
    diff_files: list[DiffFile] = Depends(get_diff_files),
    mode: ReviewMode = Depends(get_review_mode),
    title: str = Depends(get_review_title),
    root: Path | None = Depends(get_repo_root),
    base: str | None = Depends(get_diff_base),
) -> DiffResponse:
    """Serve the review's content.

    Retaking the diff is the one thing this does beyond serving what was
    loaded at startup: ignoring whitespace has to come from git, since only
    git knows which hunks vanish once whitespace stops counting.
    """
    if ignore_whitespace and root is not None:
        diff_files = await DiffService(git_repository=GitRepository()).get_diff(root, base=base, ignore_whitespace=True)
        # Keep submission in step: a comment is looked up against these files
        request.app.state.diff_files = diff_files

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


@router.post("/ask")
async def ask_about_thread(
    request: AskRequest,
    state: ServerState = Depends(get_state),
) -> dict[str, str]:
    """Take a question about one thread, for whoever is answering to pick up.

    The reader does not wait here: the answer arrives later, pushed down the
    session socket, so writing the review is never blocked on a reply.
    """
    state.questions.put_nowait(
        ThreadQuestion(
            thread_id=request.thread_id,
            file=request.file,
            side=request.side,
            start_line=request.start_line,
            end_line=request.end_line,
            quote=request.quote,
            body=request.body,
        )
    )
    log.info("thread_question", thread_id=request.thread_id, file=request.file)
    return {"status": "asked"}


@router.get("/events")
async def next_event(
    wait_seconds: float = Query(default=25.0, gt=0, le=600),
    state: ServerState = Depends(get_state),
) -> EventResponse:
    """Wait for the next thing the reader asks.

    A long poll rather than a socket: the caller is a command in a shell,
    and blocking until there is something to do is exactly its shape.
    Returning "timeout" lets the caller decide whether to keep waiting.
    """
    try:
        question = await asyncio.wait_for(state.questions.get(), timeout=wait_seconds)
    except TimeoutError:
        return EventResponse(type="timeout")

    if state.shutdown_event.is_set():
        return EventResponse(type="closed")
    return EventResponse(type="question", question=question)


@router.post("/reply")
async def reply_to_thread(
    request: ReplyRequest,
    state: ServerState = Depends(get_state),
) -> dict[str, str]:
    """Push an answer into a thread of a review that is still open."""
    state.push({"type": "reply", "thread_id": request.thread_id, "text": request.text})
    log.info("thread_reply", thread_id=request.thread_id)
    return {"status": "sent"}


@router.websocket("/session")
async def session(websocket: WebSocket) -> None:
    """Hold the review open for as long as the browser has it on screen.

    The socket is the signal: while one is open the review is being read,
    and when the last one closes the server winds down. It carries server
    pushes in the other direction too.
    """
    state: ServerState = websocket.app.state.server
    await websocket.accept()
    now = asyncio.get_running_loop().time()
    state.connected(now)
    outbox = state.listen()

    async def forward() -> None:
        while True:
            await websocket.send_json(await outbox.get())

    pump = asyncio.create_task(forward())
    try:
        while True:
            # Nothing is expected from the browser yet; this waits for the close
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        pump.cancel()
        state.stop_listening(outbox)
        state.disconnected(asyncio.get_running_loop().time())


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
            severity=c.severity,
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
