import asyncio
import time
from pathlib import Path

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic import ValidationError
from starlette.requests import ClientDisconnect

from claude_review.domain.exceptions import (
    AnchorLinesNotShownError,
    FileWindowError,
    ImageAlreadySentError,
    ImageRefusedError,
    ImageTooLargeError,
    UnknownAnchorFileError,
    UnknownImageError,
    UnknownVersionError,
)
from claude_review.domain.models import (
    Anchor,
    Comment,
    DiffFile,
    GuideState,
    LineAnchor,
    PanelCancel,
    PanelEntry,
    PanelMessage,
    ReaderSettings,
    ReviewMode,
    RoundSubmission,
    ThreadContext,
    ThreadQuestion,
    Turn,
    TurnAuthor,
)
from claude_review.presentation.dependencies import (
    anchor_service_for,
    get_anchor_service,
    get_diff_base,
    get_diff_files,
    get_guide_service,
    get_image_service,
    get_objects,
    get_release,
    get_repo_root,
    get_review_mode,
    get_review_title,
    get_settings_service,
    get_state,
    image_service_for,
)
from claude_review.presentation.schemas import (
    AnchorInput,
    AskRequest,
    CancelRequest,
    CommentInput,
    ContextResponse,
    DiffResponse,
    EventResponse,
    FileWindowResponse,
    FollowRequest,
    FollowResponse,
    GuideChange,
    GuideResponse,
    ImageLimits,
    ImageResponse,
    MessageRequest,
    PointRequest,
    PointResponse,
    ProgressRequest,
    ReplyRequest,
    RoundResponse,
    SayRequest,
    SessionHello,
    SettingsChange,
    SettingsResponse,
    ShowRequest,
    StatusRequest,
    SubmitRequest,
    SubmitResponse,
    ThreadInput,
    TurnInput,
    VersionsResponse,
)
from claude_review.presentation.state import ServerState
from claude_review.repositories.git_repository import GitRepository
from claude_review.services.anchor_service import AnchorService
from claude_review.services.diff_service import DiffService
from claude_review.services.file_window_service import FileWindowService
from claude_review.services.image_service import MAX_IMAGE_BYTES, ImageService
from claude_review.services.reader_record_service import ReaderRecordService
from claude_review.services.review_service import ReviewService
from claude_review.services.transcript_review_service import TranscriptReviewService
from claude_review.services.tree_watcher_service import TreeWatcherService
from claude_review.services.version_service import REVIEW_KEY, VersionService

log = structlog.get_logger()

router = APIRouter(prefix="/api")


@router.get("/diff")
async def get_diff(
    ignore_whitespace: bool = Query(default=False),
    base: str | None = Query(default=None, max_length=200),
    diff_files: list[DiffFile] = Depends(get_diff_files),
    mode: ReviewMode = Depends(get_review_mode),
    title: str = Depends(get_review_title),
    root: Path | None = Depends(get_repo_root),
    review_base: str | None = Depends(get_diff_base),
    objects: Path | None = Depends(get_objects),
    state: ServerState = Depends(get_state),
    release: str = Depends(get_release),
) -> DiffResponse:
    """Serve the review's content.

    Two things make this ask git rather than serve what was loaded at
    startup. Ignoring whitespace has to come from git, since only git knows
    which hunks vanish once whitespace stops counting. And a base names one
    of the versions on offer: the same working tree, read against something
    else.

    What the review holds is left alone either way. A base is a way of
    looking, not a change to what is under review — the threads are anchored
    to the diff this server loaded, and that is the one it keeps.
    """
    git = GitRepository(objects=objects)
    versions = VersionService(git_repository=git)
    taken_against = review_base

    if base is not None:
        if root is None:
            raise HTTPException(status_code=404, detail="This review is not compared against anything")
        try:
            taken_against = await versions.resolve(root, base, review_base=review_base, snapshots=state.snapshots)
        except UnknownVersionError as e:
            log.warning("version_refused", base=base, reason=str(e))
            raise HTTPException(status_code=400, detail=str(e)) from e

    if root is not None and (ignore_whitespace or base is not None):
        diff_files = await DiffService(git_repository=git).get_diff(
            root, base=taken_against, ignore_whitespace=ignore_whitespace
        )

    moved = await TreeWatcherService(git_repository=git).drift(root, state.tree) if root is not None else 0

    return DiffResponse(
        files=diff_files,
        mode=mode,
        title=title,
        phrase=versions.phrase_of(base or REVIEW_KEY, review_base=review_base) if root is not None else None,
        round=state.round,
        answerer_attached=state.answerer_attached,
        agent=state.agent,
        moved=moved,
        image_limits=ImageLimits(),
        release=release,
    )


@router.get("/versions")
async def offered_versions(
    root: Path | None = Depends(get_repo_root),
    review_base: str | None = Depends(get_diff_base),
    objects: Path | None = Depends(get_objects),
    state: ServerState = Depends(get_state),
) -> VersionsResponse:
    """Say what the working tree can be compared against.

    A review of files or a transcript is compared against nothing at all, and
    says so with an empty list rather than an error: there is no failure
    here, only nothing to choose between.
    """
    if root is None:
        return VersionsResponse(versions=[])

    versions = VersionService(git_repository=GitRepository(objects=objects))
    return VersionsResponse(versions=await versions.offer(root, review_base=review_base, snapshots=state.snapshots))


@router.get("/settings")
async def reader_settings(
    settings: ReaderRecordService[ReaderSettings] = Depends(get_settings_service),
) -> SettingsResponse:
    """Say how this reader reads, as chosen in any review on this machine."""
    kept = await settings.read()
    return SettingsResponse(settings=kept or ReaderSettings(), stored=kept is not None)


@router.put("/settings")
async def change_reader_settings(
    request: SettingsChange,
    settings: ReaderRecordService[ReaderSettings] = Depends(get_settings_service),
) -> ReaderSettings:
    """Keep a choice the reader made, for this review and every later one."""
    # A choice sent as null is a choice not sent
    changed = await settings.change(request.model_dump(exclude_none=True))
    log.info("settings_changed", changed=sorted(request.model_fields_set))
    return changed


@router.get("/guide")
async def guide_state(guide: ReaderRecordService[GuideState] = Depends(get_guide_service)) -> GuideResponse:
    """Say how far this reader has been shown around, in any review on this machine."""
    kept = await guide.read()
    return GuideResponse(guide=kept or GuideState(), stored=kept is not None)


@router.put("/guide")
async def change_guide_state(
    request: GuideChange,
    guide: ReaderRecordService[GuideState] = Depends(get_guide_service),
) -> GuideState:
    """Remember what the reader has now been shown."""
    return await guide.change(request.model_dump(exclude_unset=True))


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
        window = await FileWindowService(GitRepository()).read_window(
            root, path, start, end, in_review=frozenset(file.path for file in diff_files)
        )
    except FileWindowError as e:
        log.warning("file_window_refused", path=path, reason=str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e

    return FileWindowResponse(start=window.start, lines=window.lines, total=window.total)


@router.post("/ask")
async def ask_about_thread(
    request: AskRequest,
    state: ServerState = Depends(get_state),
    image_service: ImageService = Depends(get_image_service),
    anchors: AnchorService = Depends(get_anchor_service),
) -> dict[str, str]:
    """Take a question about one thread, for whoever is answering to pick up.

    The reader does not wait here: the answer arrives later, pushed down the
    session socket, so writing the review is never blocked on a reply.
    """
    # Pasted a moment ago, so one this review does not keep is a fault to
    # report; only the turns before it may have outlived a restart
    try:
        image_service.require(request.images)
    except UnknownImageError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    anchor = _to_anchor(request.anchor)
    where = anchors.where(anchor)
    state.events.put_nowait(
        ThreadQuestion(
            thread_id=request.thread_id,
            question_id=request.question_id,
            anchor=anchor,
            where=where,
            body=request.body,
            images=image_service.hand_over(request.images).paths,
            history=[_to_turn(turn, image_service) for turn in request.history],
            severity=request.severity,
            resolved=request.resolved,
            raised_by=request.raised_by,
        )
    )
    log.info("thread_question", thread_id=request.thread_id, where=where)
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
    image_service: ImageService = Depends(get_image_service),
    anchors: AnchorService = Depends(get_anchor_service),
) -> dict[str, str]:
    """Take what the reader typed in the panel, for the agent to pick up.

    Everything typed there goes now — the panel has no "add to review",
    because a message about the plan or the tests belongs to no thread and
    has nothing to wait for.
    """
    # Pasted a moment ago, so an image this review does not keep is a fault
    # to report, not a screenshot to leave out quietly. Checked before any
    # is handed over, so a refused message leaves none of them kept for good.
    try:
        image_service.require(request.images)
    except UnknownImageError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    handed = image_service.hand_over(request.images).paths

    state.events.put_nowait(
        PanelMessage(
            message_id=request.message_id,
            text=request.text,
            threads=[_to_thread(thread, image_service, anchors) for thread in request.threads],
            images=handed,
        )
    )
    state.panel.append(
        PanelEntry(
            message_id=request.message_id,
            author=TurnAuthor.READER,
            text=request.text,
            at=int(time.time() * 1000),
            images=handed,
        )
    )
    log.info("panel_message", message_id=request.message_id, threads=len(request.threads), images=len(handed))
    return {"status": "sent"}


@router.post("/images")
async def keep_an_image(
    http_request: Request,
    image_service: ImageService = Depends(get_image_service),
) -> ImageResponse:
    """Keep an image the reader is about to send, and say what it is called.

    Taken on its own, before the message: the reader sees it attached while
    still writing, and the message then carries an id rather than the bytes.
    The body is the image itself rather than a form, so there is nothing to
    parse.
    """
    content = await _read_capped(http_request, limit=MAX_IMAGE_BYTES)
    try:
        stored = await image_service.keep(content)
    except ImageRefusedError as e:
        log.warning("image_refused", reason=str(e))
        status = 413 if isinstance(e, ImageTooLargeError) else 422
        raise HTTPException(status_code=status, detail=str(e)) from e

    log.info("image_kept", image_id=stored.image_id, size=stored.size)
    return ImageResponse(image_id=stored.image_id)


async def _read_capped(http_request: Request, *, limit: int) -> bytes:
    """Read a body, stopping as soon as it runs past the limit.

    Past it is enough to know it is too big, and the rest is never held.

    Raises:
        HTTPException: if the browser went away mid-upload.
    """
    received = bytearray()
    try:
        async for chunk in http_request.stream():
            received.extend(chunk)
            if len(received) > limit:
                break
    except ClientDisconnect as e:
        raise HTTPException(status_code=400, detail="The upload was cut off") from e
    return bytes(received)


@router.get("/images/{image_id}")
async def serve_an_image(
    image_id: str,
    image_service: ImageService = Depends(get_image_service),
) -> FileResponse:
    """Hand back an image this review keeps, to be drawn in the panel."""
    stored = image_service.find(image_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="No such image in this review")
    return FileResponse(stored.path, media_type=stored.media_type)


@router.delete("/images/{image_id}")
async def discard_an_image(
    image_id: str,
    image_service: ImageService = Depends(get_image_service),
) -> dict[str, str]:
    """Drop an image the reader took off the message before sending it.

    One that went out with a message stays: the agent may still be about to
    open it, and nothing on this side knows when it has.
    """
    try:
        await image_service.discard(image_id)
    except UnknownImageError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ImageAlreadySentError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e

    log.info("image_discarded", image_id=image_id)
    return {"status": "discarded"}


def _hand_over_kept(image_ids: list[str], image_service: ImageService) -> list[Path]:
    """Hand over the images a thread names that this review still keeps.

    A thread outlives a restart of the server in the reader's draft, and the
    screenshots in it do not: one that is gone drops out, rather than holding
    up the question or the round it travels in — but not without a trace.
    """
    handover = image_service.hand_over(image_ids)
    if handover.missing:
        log.info("images_dropped", missing=handover.missing)
    return handover.paths


def _to_turn(turn: TurnInput, image_service: ImageService) -> Turn:
    return Turn(
        author=turn.author,
        body=turn.body,
        round=turn.round,
        images=_hand_over_kept(turn.images, image_service),
    )


def _to_thread(thread: ThreadInput, image_service: ImageService, anchors: AnchorService) -> ThreadContext:
    """Take a thread a message points at off the wire, turns and all."""
    anchor = _to_anchor(thread.anchor)
    return ThreadContext(
        thread_id=thread.thread_id,
        anchor=anchor,
        where=anchors.where(anchor),
        body=thread.body,
        images=_hand_over_kept(thread.images, image_service),
        history=[_to_turn(turn, image_service) for turn in thread.history],
        severity=thread.severity,
        resolved=thread.resolved,
        raised_by=thread.raised_by,
    )


def _to_anchor(anchor: AnchorInput) -> Anchor:
    """Take what a thread hangs on off the wire."""
    return LineAnchor.model_validate(anchor.model_dump())


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
    anchors: AnchorService = Depends(get_anchor_service),
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
    asked_for = LineAnchor(
        file=request.file, side=request.side, start_line=request.start_line, end_line=request.end_line
    )
    try:
        # Quoted here, from the diff the anchor will be followed through: the
        # lines are what let the thread find its code again when it moves
        anchor = anchors.quote(asked_for)
    except UnknownAnchorFileError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except AnchorLinesNotShownError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    thread_id = state.raise_id()
    state.push(
        {
            "type": "point",
            "thread_id": thread_id,
            "anchor": anchor.model_dump(mode="json"),
            "body": request.body,
            "severity": str(request.severity),
        }
    )
    log.info("thread_raised", thread_id=thread_id, where=anchors.where(anchor))
    return PointResponse(thread_id=thread_id)


@router.post("/anchors/follow")
async def follow_anchors(
    request: FollowRequest,
    anchors: AnchorService = Depends(get_anchor_service),
) -> FollowResponse:
    """Say where each anchor is in the review's diff as it now stands.

    The browser holds the threads and the server holds the diff, so after a
    round the threads come here to be moved: one whose lines survived follows
    them, one whose lines are gone is marked outdated and keeps its quote.
    The rule lives here, once, for everything that hangs on the diff.
    """
    return FollowResponse(anchors=[anchors.follow(_to_anchor(anchor)) for anchor in request.anchors])


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
    image_service = image_service_for(websocket.app)
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
            # Anchors are read against the diff as it is when the message
            # arrives: a round retakes it while the socket stays open
            _catch_up(state, image_service, anchor_service_for(websocket.app), await websocket.receive_text())
    except WebSocketDisconnect:
        pass
    finally:
        pump.cancel()
        state.stop_listening(outbox)
        state.disconnected(asyncio.get_running_loop().time())


def _catch_up(state: ServerState, image_service: ImageService, anchors: AnchorService, said: str) -> None:
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

    if heard.threads is not None:
        state.hold_threads([_to_thread(thread, image_service, anchors) for thread in heard.threads])


@router.post("/submit")
async def submit_review(
    request: SubmitRequest,
    state: ServerState = Depends(get_state),
    mode: ReviewMode = Depends(get_review_mode),
    diff_files: list[DiffFile] = Depends(get_diff_files),
    image_service: ImageService = Depends(get_image_service),
    anchors: AnchorService = Depends(get_anchor_service),
) -> SubmitResponse:
    """Send what has been written, and either end the review or carry on.

    Ending is the plain case: one send, and the agent reads the result on
    stdout. A round keeps the review open instead — the threads stay on
    screen, so an answer has somewhere to come back to.
    """
    if state.shutdown_event.is_set():
        raise HTTPException(status_code=409, detail="Review already submitted")

    comments = [_to_comment(comment, image_service) for comment in request.comments]
    sent_round = state.round

    if mode == ReviewMode.TRANSCRIPT:
        result = TranscriptReviewService().format_review(comments, request.body, diff_files, round_number=sent_round)
    else:
        result = ReviewService(anchors).format_review(comments, body=request.body, round_number=sent_round)

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


def _to_comment(comment: CommentInput, image_service: ImageService) -> Comment:
    """Take a thread off the wire, turns and all."""
    return Comment(
        anchor=_to_anchor(comment.anchor),
        severity=comment.severity,
        body=comment.body,
        images=_hand_over_kept(comment.images, image_service),
        turns=[_to_turn(turn, image_service) for turn in comment.turns],
        raised_by=comment.raised_by,
        resolved=comment.resolved,
    )


@router.post("/round")
async def retake_diff(
    http_request: Request,
    state: ServerState = Depends(get_state),
    root: Path | None = Depends(get_repo_root),
    base: str | None = Depends(get_diff_base),
    objects: Path | None = Depends(get_objects),
) -> RoundResponse:
    """Take the diff again, after the work a round asked for.

    The reviews on screen are told to reload it rather than being handed the
    files: a browser has its own view of the diff — which files are folded,
    whether whitespace counts — and asking it to fetch keeps that one path.

    They are also told which files moved, which is not a nicety: a file the
    reader had ticked off keeps its tick through a retake, so without this
    they walk past code the agent rewrote under them.
    """
    if root is None:
        raise HTTPException(status_code=404, detail="No repository to retake the diff from")

    git = GitRepository(objects=objects)
    versions = VersionService(git_repository=git)
    # One retake at a time, each about one round: a round sent while git is
    # working must not tag this retake's mark with the round after it
    async with state.retaking:
        round_number = state.round
        # Asked before the new tree is written down, while the last mark is
        # still the one the diff on screen was taken at
        read_at = versions.began(state.snapshots, round_number)
        changed = await versions.changed_since(root, read_at)

        files = await DiffService(git_repository=git).get_diff(root, base=base)
        http_request.app.state.diff_files = files
        # Read after the diff, not before: a file saved in between then belongs
        # to the tree the diff was taken at, and the reader is not told about a
        # change that is already on their screen.
        state.tree = await TreeWatcherService(git_repository=git).read(root)
        if (mark := await versions.take(root, round_number=round_number)) is not None:
            state.snapshots.append(mark)

    since = read_at.round if read_at is not None else None
    state.push({"type": "diff", "round": round_number, "changed": changed, "since": since})
    log.info("diff_retaken", file_count=len(files), round=round_number, changed=len(changed or []))

    return RoundResponse(file_count=len(files), round=round_number, changed=changed, since=since)


@router.post("/end")
async def end_review(state: ServerState = Depends(get_state)) -> dict[str, str]:
    """End a review that has been kept open for rounds."""
    state.shutdown_event.set()
    log.info("review_ended", round=state.round)
    return {"status": "ended"}
