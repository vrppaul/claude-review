import asyncio
import time
from pathlib import Path

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from claude_review.domain.exceptions import FileWindowError
from claude_review.domain.models import (
    Comment,
    DiffFile,
    LineSide,
    PanelCancel,
    PanelEntry,
    PanelMessage,
    ReviewMode,
    RoundSubmission,
    ThreadContext,
    ThreadQuestion,
    Turn,
    TurnAuthor,
)
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
    CancelRequest,
    CommentInput,
    ContextResponse,
    DiffResponse,
    EventResponse,
    FileWindowResponse,
    MessageRequest,
    PointRequest,
    PointResponse,
    ProgressRequest,
    ReplyRequest,
    RoundResponse,
    SayRequest,
    SessionHello,
    ShowRequest,
    StatusRequest,
    SubmitRequest,
    SubmitResponse,
    ThreadInput,
)
from claude_review.presentation.state import ServerState
from claude_review.repositories.git_repository import GitRepository
from claude_review.services.diff_service import DiffService
from claude_review.services.file_window_service import FileWindowService
from claude_review.services.review_service import ReviewService
from claude_review.services.transcript_review_service import TranscriptReviewService
from claude_review.services.tree_watcher_service import TreeWatcherService

log = structlog.get_logger()

router = APIRouter(prefix="/api")


@router.get("/diff")
async def get_diff(
    ignore_whitespace: bool = Query(default=False),
    diff_files: list[DiffFile] = Depends(get_diff_files),
    mode: ReviewMode = Depends(get_review_mode),
    title: str = Depends(get_review_title),
    root: Path | None = Depends(get_repo_root),
    base: str | None = Depends(get_diff_base),
    state: ServerState = Depends(get_state),
) -> DiffResponse:
    """Serve the review's content.

    Retaking the diff is the one thing this does beyond serving what was
    loaded at startup: ignoring whitespace has to come from git, since only
    git knows which hunks vanish once whitespace stops counting.
    """
    if ignore_whitespace and root is not None:
        diff_files = await DiffService(git_repository=GitRepository()).get_diff(root, base=base, ignore_whitespace=True)

    return DiffResponse(
        files=diff_files,
        mode=mode,
        title=title,
        round=state.round,
        answerer_attached=state.answerer_attached,
        agent=state.agent,
    )


@router.get("/context")
async def review_context(
    thread: str | None = Query(default=None, max_length=200),
    state: ServerState = Depends(get_state),
    title: str = Depends(get_review_title),
    diff_files: list[DiffFile] = Depends(get_diff_files),
) -> ContextResponse:
    """Say what this review holds, for an agent that has just arrived.

    An agent restarted mid-review knows nothing: `events` hands over what
    happens next, never what already happened. Everything here has passed
    through this server, so it can say what was asked, what was answered and
    what is still open — as an index, because handing over the whole review
    unasked is how a catch-up costs more than the work.

    Naming a thread returns that one alone, in full.
    """
    threads = [t for t in state.threads if thread is None or t.thread_id == thread]
    return ContextResponse(
        title=title,
        round=state.round,
        file_count=len(diff_files),
        answerer_attached=state.answerer_attached,
        agent=state.agent,
        threads=threads,
        panel=[] if thread is not None else state.panel,
    )


@router.get("/file-window")
async def get_file_window(
    path: str = Query(min_length=1),
    start: int = Query(ge=1),
    end: int = Query(ge=1),
    root: Path | None = Depends(get_repo_root),
    diff_files: list[DiffFile] = Depends(get_diff_files),
) -> FileWindowResponse:
    """Serve lines a hunk left out, so the reader can widen its context."""
    if root is None:
        raise HTTPException(status_code=404, detail="No repository to read from")

    try:
        window = await FileWindowService().read_window(root, path, start, end, allowed=[f.path for f in diff_files])
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
    state.events.put_nowait(
        ThreadQuestion(
            thread_id=request.thread_id,
            question_id=request.question_id,
            file=request.file,
            side=request.side,
            start_line=request.start_line,
            end_line=request.end_line,
            quote=request.quote,
            body=request.body,
            history=[Turn(author=t.author, body=t.body, round=t.round) for t in request.history],
        )
    )
    log.info("thread_question", thread_id=request.thread_id, file=request.file)
    return {"status": "asked"}


@router.get("/events")
async def next_event(
    wait_seconds: float = Query(default=25.0, gt=0, le=600),
    state: ServerState = Depends(get_state),
) -> EventResponse:
    """Wait for the next thing the reader hands over.

    A long poll rather than a socket: the caller is a command in a shell,
    and blocking until there is something to do is exactly its shape.
    Returning "timeout" lets the caller decide whether to keep waiting.
    """
    # Asking at all is what says an agent is there, which is what makes
    # rounds worth offering in the review
    state.attach_answerer()

    if state.shutdown_event.is_set():
        return EventResponse(type="closed")

    taken = asyncio.ensure_future(state.events.get())
    closed = asyncio.ensure_future(state.shutdown_event.wait())
    try:
        done, _ = await asyncio.wait({taken, closed}, timeout=wait_seconds, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for pending in (taken, closed):
            if not pending.done():
                pending.cancel()

    # What was handed over outranks the review ending: a round sent as the
    # last act would otherwise be dropped for the shutdown that followed it
    if taken in done:
        return _envelope(taken.result())
    if closed in done:
        return EventResponse(type="closed")
    return EventResponse(type="timeout")


def _envelope(event: ThreadQuestion | RoundSubmission | PanelMessage | PanelCancel) -> EventResponse:
    """Name what came off the queue, so the loop can tell the kinds apart."""
    match event:
        case RoundSubmission():
            return EventResponse(type="round", round=event)
        case PanelMessage():
            return EventResponse(type="message", message=event)
        case PanelCancel():
            return EventResponse(type="cancel", cancel=event)
        case _:
            return EventResponse(type="question", question=event)


@router.post("/reply")
async def reply_to_thread(
    request: ReplyRequest,
    state: ServerState = Depends(get_state),
) -> dict[str, str]:
    """Push an answer into a thread of a review that is still open."""
    state.push(
        {
            "type": "reply",
            "thread_id": request.thread_id,
            "question_id": request.question_id,
            "text": request.text,
        }
    )
    log.info("thread_reply", thread_id=request.thread_id, question_id=request.question_id)
    return {"status": "sent"}


@router.post("/message")
async def take_panel_message(
    request: MessageRequest,
    state: ServerState = Depends(get_state),
) -> dict[str, str]:
    """Take what the reader typed in the panel, for the agent to pick up.

    Everything typed there goes now — the panel has no "add to review",
    because a message about the plan or the tests belongs to no thread and
    has nothing to wait for.
    """
    state.events.put_nowait(
        PanelMessage(
            message_id=request.message_id,
            text=request.text,
            threads=[_to_thread(t) for t in request.threads],
        )
    )
    state.panel.append(
        PanelEntry(
            message_id=request.message_id,
            author=TurnAuthor.READER,
            text=request.text,
            at=int(time.time() * 1000),
        )
    )
    log.info("panel_message", message_id=request.message_id, threads=len(request.threads))
    return {"status": "sent"}


def _to_thread(thread: ThreadInput) -> ThreadContext:
    """Take a thread a message points at off the wire, turns and all."""
    return ThreadContext(
        thread_id=thread.thread_id,
        file=thread.file,
        side=thread.side,
        start_line=thread.start_line,
        end_line=thread.end_line,
        quote=thread.quote,
        body=thread.body,
        history=[Turn(author=t.author, body=t.body, round=t.round) for t in thread.history],
        severity=thread.severity,
        resolved=thread.resolved,
        outdated=thread.outdated,
        raised_by=thread.raised_by,
    )


def _refuse_a_thread_hung_on_nothing(request: PointRequest, diff_files: list[DiffFile]) -> None:
    """Check that the lines a thread is about are on screen to be read.

    Raises:
        HTTPException: if the file is not under review, or those lines of it
            are not among the ones the diff shows.
    """
    shown = next((f for f in diff_files if f.path == request.file), None)
    if shown is None:
        listed = ", ".join(f.path for f in diff_files[:5])
        msg = f"{request.file} is not in this review. It has: {listed}"
        raise HTTPException(status_code=404, detail=msg)

    wanted = request.side
    on_screen = {
        line.old_no if wanted == LineSide.OLD else line.new_no
        for hunk in shown.hunks
        for line in hunk.lines
        if (line.old_no if wanted == LineSide.OLD else line.new_no) is not None
    }
    missing = [no for no in range(request.start_line, request.end_line + 1) if no not in on_screen]
    if missing:
        side = "removed" if wanted == LineSide.OLD else "new"
        msg = f"{request.file} does not show {side} line{'s' if len(missing) > 1 else ''} {_span(missing)}"
        raise HTTPException(status_code=422, detail=msg)


def _span(numbers: list[int]) -> str:
    """Name the missing lines the way a person would: "12", or "12-19"."""
    return str(numbers[0]) if len(numbers) == 1 else f"{numbers[0]}-{numbers[-1]}"


@router.post("/say")
async def say_in_panel(
    request: SayRequest,
    state: ServerState = Depends(get_state),
) -> dict[str, str]:
    """Push what the agent has to say into a review still open.

    An answer names the message it answers. A message that names nothing is
    the agent speaking first, which is worth as much: work finished while
    the reader was reading is news they would otherwise have to ask for.
    """
    state.push(
        {
            "type": "chat",
            "message_id": request.message_id,
            "text": request.text,
            "files": request.files,
        }
    )
    state.panel.append(
        PanelEntry(
            message_id=request.message_id,
            author=TurnAuthor.AUTHOR,
            text=request.text,
            at=int(time.time() * 1000),
        )
    )
    log.info("panel_answer", message_id=request.message_id, unprompted=request.message_id is None)
    return {"status": "sent"}


@router.post("/progress")
async def report_progress(
    request: ProgressRequest,
    state: ServerState = Depends(get_state),
) -> dict[str, str]:
    """Say what is being done, while it is being done.

    Waiting says only that something is happening. This says what: which
    files are being touched and what is being made of them. It replaces
    whatever was showing — the state of the work, not a log of it — and an
    empty one takes the line away.
    """
    state.push(
        {
            "type": "progress",
            "message_id": request.message_id,
            "text": request.text,
            "files": request.files,
            "steps": [step.model_dump() for step in request.steps],
        }
    )
    return {"status": "noted"}


@router.post("/show")
async def show_a_file(
    request: ShowRequest,
    state: ServerState = Depends(get_state),
) -> dict[str, str]:
    """Take the reader to a file, and mark it for a moment when they arrive.

    The only thing here that moves somebody else's screen, so it is only
    ever sent when they asked to be taken somewhere.
    """
    state.push({"type": "show", "file": request.file})
    log.info("file_shown", file=request.file)
    return {"status": "shown"}


@router.post("/point")
async def raise_a_thread(
    request: PointRequest,
    state: ServerState = Depends(get_state),
    diff_files: list[DiffFile] = Depends(get_diff_files),
) -> PointResponse:
    """Put a thread on a line, from the side that wrote the change.

    "Here I did it differently from what you asked" belongs on the line it
    is about, not in a paragraph somewhere else. What arrives is an ordinary
    thread: the reader answers it, settles it or removes it. It is drawn as
    the author's, though, and it is never counted as the reader's own work.

    The anchor is checked against the diff on screen, because a thread hung
    where nothing is shows the reader an empty quote and goes outdated on
    the next retake — and whoever raised it has no way of knowing.
    """
    _refuse_a_thread_hung_on_nothing(request, diff_files)
    thread_id = state.raise_id()
    state.push(
        {
            "type": "point",
            "thread_id": thread_id,
            "file": request.file,
            "side": str(request.side),
            "start_line": request.start_line,
            "end_line": request.end_line,
            "body": request.body,
            "severity": str(request.severity),
        }
    )
    log.info("thread_raised", thread_id=thread_id, file=request.file)
    return PointResponse(thread_id=thread_id)


@router.post("/cancel")
async def cancel_panel_message(
    request: CancelRequest,
    state: ServerState = Depends(get_state),
) -> dict[str, str]:
    """Take back a message the agent has not answered yet.

    A request rather than a kill: it joins the queue behind whatever else is
    waiting, and the agent decides what to do about it. Nothing here can
    reach into another process and stop it mid-thought.
    """
    state.events.put_nowait(PanelCancel(message_id=request.message_id))
    log.info("panel_cancelled", message_id=request.message_id)
    return {"status": "cancelled"}


@router.post("/status")
async def report_status(
    request: StatusRequest,
    state: ServerState = Depends(get_state),
) -> dict[str, str]:
    """Take what the agent says about itself, and pass it on unchanged.

    Which model, and how much of its context is spent: neither can be
    measured from here, so both are quoted with the time they were said.
    """
    now = int(time.time() * 1000)
    if request.model is not None:
        state.agent.model = request.model
    if request.context is not None:
        state.agent.context = request.context
    state.agent.at = now

    state.push({"type": "status", "model": state.agent.model, "context": state.agent.context, "at": now})
    log.info("agent_status", model=state.agent.model, context=state.agent.context)
    return {"status": "noted"}


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
            # The browser says where the review had got to, and otherwise
            # this waits for the close
            _catch_up(state, await websocket.receive_text())
    except WebSocketDisconnect:
        pass
    finally:
        pump.cancel()
        state.stop_listening(outbox)
        state.disconnected(asyncio.get_running_loop().time())


def _catch_up(state: ServerState, said: str) -> None:
    """Take what the browser knows and this server does not.

    Two things. The round: a server restarted mid-review comes back
    believing it is round one and would number the next round wrongly for
    everyone reading it — so the browser says where it had got to, and never
    downwards, because one reader opening fresh must not drag the review
    back to the beginning. And the threads: they are unsent work, held in
    that browser, and an agent attaching later has no other way to learn
    they exist.
    """
    try:
        heard = SessionHello.model_validate_json(said)
    except ValidationError:
        # The socket is a lifeline first; nonsense on it is not worth
        # dropping a review over
        return

    if heard.round is not None and heard.round > state.round:
        log.info("round_caught_up", was=state.round, now=heard.round)
        state.round = heard.round

    if heard.threads:
        state.threads = [_to_thread(t) for t in heard.threads]


@router.post("/submit")
async def submit_review(
    request: SubmitRequest,
    state: ServerState = Depends(get_state),
    mode: ReviewMode = Depends(get_review_mode),
    diff_files: list[DiffFile] = Depends(get_diff_files),
) -> SubmitResponse:
    """Send what has been written, and either end the review or carry on.

    Ending is the plain case: one send, and the agent reads the result on
    stdout. A round keeps the review open instead — the threads stay on
    screen, so an answer has somewhere to come back to.
    """
    if state.shutdown_event.is_set():
        raise HTTPException(status_code=409, detail="Review already submitted")

    comments = [_to_comment(c) for c in request.comments]
    sent_round = state.round

    if mode == ReviewMode.TRANSCRIPT:
        result = TranscriptReviewService().format_review(comments, request.body, diff_files, round_number=sent_round)
    else:
        result = ReviewService().format_review(comments, body=request.body, round_number=sent_round)

    state.result = result.markdown
    state.events.put_nowait(
        RoundSubmission(number=sent_round, markdown=result.markdown, comment_count=result.comment_count)
    )

    if request.end:
        state.shutdown_event.set()
    else:
        state.round += 1
        state.push({"type": "round", "number": state.round})

    log.info("review_submitted", comment_count=result.comment_count, round=sent_round, ended=request.end)

    return SubmitResponse(
        markdown=result.markdown,
        comment_count=result.comment_count,
        round=sent_round,
        ended=request.end,
    )


def _to_comment(comment: CommentInput) -> Comment:
    """Take a thread off the wire, turns and all."""
    return Comment(
        file=comment.file,
        side=comment.side,
        severity=comment.severity,
        start_line=comment.start_line,
        end_line=comment.end_line,
        body=comment.body,
        turns=[Turn(author=t.author, body=t.body, round=t.round) for t in comment.turns],
        raised_by=comment.raised_by,
        resolved=comment.resolved,
        outdated=comment.outdated,
        quote=comment.quote,
    )


@router.post("/round")
async def retake_diff(
    http_request: Request,
    state: ServerState = Depends(get_state),
    root: Path | None = Depends(get_repo_root),
    base: str | None = Depends(get_diff_base),
) -> RoundResponse:
    """Take the diff again, after the work a round asked for.

    The reviews on screen are told to reload it rather than being handed the
    files: a browser has its own view of the diff — which files are folded,
    whether whitespace counts — and asking it to fetch keeps that one path.
    """
    if root is None:
        raise HTTPException(status_code=404, detail="No repository to retake the diff from")

    git = GitRepository()
    files = await DiffService(git_repository=git).get_diff(root, base=base)
    http_request.app.state.diff_files = files
    # Read after the diff, not before: a file saved in between then belongs to
    # the tree the diff was taken at, and the reader is not told about a
    # change that is already on their screen.
    state.tree = await TreeWatcherService(git_repository=git).read(root)
    state.push({"type": "diff", "round": state.round})
    log.info("diff_retaken", file_count=len(files), round=state.round)

    return RoundResponse(file_count=len(files), round=state.round)


@router.post("/end")
async def end_review(state: ServerState = Depends(get_state)) -> dict[str, str]:
    """End a review that has been kept open for rounds."""
    state.shutdown_event.set()
    log.info("review_ended", round=state.round)
    return {"status": "ended"}
