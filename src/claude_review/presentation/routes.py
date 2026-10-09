import asyncio
from http import HTTPStatus
from pathlib import Path
from typing import assert_never

import structlog
from fastapi import APIRouter, Depends, Path as PathParameter, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic import ValidationError
from starlette.requests import ClientDisconnect

from claude_review.domain.exceptions import (
    NoRepositoryError,
    QuestionNotInThreadError,
    ReviewEndedError,
    UnknownThreadError,
)
from claude_review.domain.models import (
    AgentEvent,
    AgentStatus,
    DiffFile,
    GuideState,
    PanelCancel,
    PanelEntry,
    PanelMessage,
    ReaderSettings,
    ReviewMode,
    RoundSubmission,
    Thread,
    ThreadQuestion,
    Turn,
    TurnAuthor,
)
from claude_review.domain.protocols import Clock
from claude_review.presentation.dependencies import (
    get_anchor_service,
    get_clock,
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
)
from claude_review.presentation.refusals import UploadCutOffError
from claude_review.presentation.schemas import (
    DEFAULT_WAIT_SECONDS,
    MAX_ID_LENGTH,
    MAX_WAIT_SECONDS,
    SAFE_ID,
    AgentWork,
    AskRequest,
    CancelEvent,
    CancelRequest,
    ChatPush,
    ClosedEvent,
    ContextResponse,
    DiffPush,
    DiffResponse,
    EventResponse,
    FileWindowResponse,
    FollowRequest,
    FollowResponse,
    GuideChange,
    GuideResponse,
    HeldThreads,
    ImageResponse,
    MessageEvent,
    MessageRequest,
    PointPush,
    PointRequest,
    PointResponse,
    ProgressRequest,
    QuestionEvent,
    ReceivedHello,
    ReplyPush,
    ReplyRequest,
    RoundEvent,
    RoundPush,
    RoundResponse,
    SayRequest,
    SaysSomething,
    SendLimits,
    ServerPush,
    SettingsChange,
    SettingsResponse,
    ShowPush,
    ShowRequest,
    StatusPush,
    StatusRequest,
    SubmitRequest,
    SubmitResponse,
    ThreadInput,
    ThreadSummary,
    TimeoutEvent,
    TurnInput,
    VersionsResponse,
)
from claude_review.presentation.state import ServerState
from claude_review.repositories.git_repository import GitRepository
from claude_review.services.agent_inbox import Silence
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
    base: str | None = Query(default=None, max_length=MAX_ID_LENGTH),
    diff_files: list[DiffFile] = Depends(get_diff_files),
    mode: ReviewMode = Depends(get_review_mode),
    title: str = Depends(get_review_title),
    root: Path | None = Depends(get_repo_root),
    review_base: str | None = Depends(get_diff_base),
    objects: Path | None = Depends(get_objects),
    state: ServerState = Depends(get_state),
    release: str = Depends(get_release),
    clock: Clock = Depends(get_clock),
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
    versions = VersionService(git_repository=git, clock=clock)
    taken_against = review_base

    if base is not None:
        if root is None:
            msg = "This review is not compared against anything"
            raise NoRepositoryError(msg)
        taken_against = await versions.resolve(root, base, review_base=review_base, snapshots=state.snapshots)

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
        limits=SendLimits(),
        release=release,
    )


@router.get("/versions")
async def offered_versions(
    root: Path | None = Depends(get_repo_root),
    review_base: str | None = Depends(get_diff_base),
    objects: Path | None = Depends(get_objects),
    state: ServerState = Depends(get_state),
    clock: Clock = Depends(get_clock),
) -> VersionsResponse:
    """Say what the working tree can be compared against.

    A review of files or a transcript is compared against nothing at all, and
    says so with an empty list rather than an error: there is no failure
    here, only nothing to choose between.
    """
    if root is None:
        return VersionsResponse(versions=[])

    versions = VersionService(git_repository=GitRepository(objects=objects), clock=clock)
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
    state: ServerState = Depends(get_state),
    title: str = Depends(get_review_title),
    diff_files: list[DiffFile] = Depends(get_diff_files),
) -> ContextResponse:
    """Say what this review holds, for an agent that has just arrived.

    An agent restarted mid-review knows nothing: `events` hands over what
    happens next, never what already happened. Everything here has passed
    through this server, so it can say what was asked, what was answered and
    what is still open — as an index, because handing over the whole review
    unasked is how a catch-up costs more than the work. A thread is read in
    full from its own route.
    """
    return ContextResponse(
        title=title,
        round=state.round,
        file_count=len(diff_files),
        answerer_attached=state.answerer_attached,
        agent=state.agent,
        threads=[ThreadSummary.of(held) for held in state.threads],
        panel=state.panel,
    )


@router.get("/context/threads/{thread_id}")
async def read_thread(
    thread_id: str = PathParameter(max_length=MAX_ID_LENGTH, pattern=SAFE_ID),
    state: ServerState = Depends(get_state),
    image_service: ImageService = Depends(get_image_service),
) -> Thread:
    """Hand over one thread the review holds, in full: every turn, its lines, its images.

    Read, so handed over: the agent may open its images from now on, and
    the reader can no longer take them off.
    """
    held = next((thread for thread in state.threads if thread.thread_id == thread_id), None)
    if held is None:
        msg = f"No thread {thread_id} in this review"
        raise UnknownThreadError(msg)
    return _hand_over_thread(held, image_service)


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
        msg = "No repository to read from"
        raise NoRepositoryError(msg)

    window = await FileWindowService(GitRepository()).read_window(
        root, path, start, end, in_review=frozenset(file.path for file in diff_files)
    )

    return FileWindowResponse(start=window.start, lines=window.lines, total=window.total)


@router.post("/ask", status_code=HTTPStatus.NO_CONTENT)
async def ask_about_thread(
    request: AskRequest,
    state: ServerState = Depends(get_state),
    image_service: ImageService = Depends(get_image_service),
) -> None:
    """Take a question asked in one thread, for whoever is answering to pick up.

    The reader does not wait here: the answer arrives later, pushed down the
    session socket, so writing the review is never blocked on a reply.
    """
    asked = _asked_in(request)
    thread = _hand_over_thread(request.thread, image_service)
    # Handed over with the thread already; named again, they are the same
    # files. Like every image in the thread, one this review no longer keeps
    # is left out: after a restart a screenshot is gone however recently it
    # was pasted, and nothing here can tell the two apart.
    images = _hand_over_kept(asked.images, image_service)
    state.inbox.hand_in(ThreadQuestion(question_id=request.question_id, body=asked.body, images=images, thread=thread))
    log.info("thread_question", thread_id=thread.thread_id, where=thread.where)


def _asked_in(request: AskRequest) -> SaysSomething:
    """What a question asks: the comment that opened its thread, or a turn the reader wrote in it.

    Raises:
        QuestionNotInThreadError: if it names neither.
    """
    if request.question_id == request.thread.thread_id:
        return request.thread
    for turn in request.thread.turns:
        if turn.turn_id == request.question_id and turn.author == TurnAuthor.READER:
            return turn
    msg = f"{request.question_id} is not something the reader said in {request.thread.thread_id}"
    raise QuestionNotInThreadError(msg)


@router.get("/events")
async def next_event(
    http_request: Request,
    wait_seconds: float = Query(default=DEFAULT_WAIT_SECONDS, gt=0, le=MAX_WAIT_SECONDS),
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
    return _envelope(await state.inbox.take(within=wait_seconds, caller_left=_until_the_caller_leaves(http_request)))


async def _until_the_caller_leaves(http_request: Request) -> None:
    """Return once whoever asked has gone away.

    The request has no body, so after it the only thing left to hear is the
    caller hanging up: a `wait` killed, or timed out by whatever ran it.
    """
    while (await http_request.receive())["type"] != "http.disconnect":
        continue


def _envelope(taken: AgentEvent | Silence) -> EventResponse:
    """Name what was taken, so the loop can tell the kinds apart."""
    match taken:
        case ThreadQuestion():
            return QuestionEvent(question=taken)
        case RoundSubmission():
            return RoundEvent(round=taken)
        case PanelMessage():
            return MessageEvent(message=taken)
        case PanelCancel():
            return CancelEvent(cancel=taken)
        case Silence.CLOSED:
            return ClosedEvent()
        # Nobody reads what a caller that left is answered
        case Silence.TIMED_OUT | Silence.CALLER_LEFT:
            return TimeoutEvent()
        case _:
            assert_never(taken)


@router.post("/reply", status_code=HTTPStatus.NO_CONTENT)
async def reply_to_thread(
    request: ReplyRequest,
    state: ServerState = Depends(get_state),
) -> None:
    """Push an answer into a thread of a review that is still open."""
    state.push(ReplyPush(thread_id=request.thread_id, question_id=request.question_id, text=request.text))
    log.info("thread_reply", thread_id=request.thread_id, question_id=request.question_id)


@router.post("/message", status_code=HTTPStatus.NO_CONTENT)
async def take_panel_message(
    request: MessageRequest,
    state: ServerState = Depends(get_state),
    image_service: ImageService = Depends(get_image_service),
    clock: Clock = Depends(get_clock),
) -> None:
    """Take what the reader typed in the panel, for the agent to pick up.

    Everything typed there goes now — the panel has no "add to review",
    because a message about the plan or the tests belongs to no thread and
    has nothing to wait for.
    """
    # Pasted a moment ago, so an image this review does not keep is a fault
    # to report, not a screenshot to leave out quietly. Checked before any
    # is handed over, so a refused message leaves none of them kept for good.
    image_service.require(request.images)
    handed = image_service.hand_over(request.images).paths
    state.message_arrived()

    state.inbox.hand_in(
        PanelMessage(
            message_id=request.message_id,
            text=request.body,
            threads=[_hand_over_thread(thread, image_service) for thread in request.threads],
            images=handed,
        )
    )
    state.panel.append(
        PanelEntry(
            message_id=request.message_id,
            author=TurnAuthor.READER,
            text=request.body,
            at=clock.now(),
            images=handed,
        )
    )
    log.info("panel_message", message_id=request.message_id, threads=len(request.threads), images=len(handed))


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
    stored = await image_service.keep(content)

    log.info("image_kept", image_id=stored.image_id, size=stored.size)
    return ImageResponse(image_id=stored.image_id)


async def _read_capped(http_request: Request, *, limit: int) -> bytes:
    """Read a body, stopping as soon as it runs past the limit.

    Past it is enough to know it is too big, and the rest is never held.

    Raises:
        UploadCutOffError: if the browser went away mid-upload.
    """
    received = bytearray()
    try:
        async for chunk in http_request.stream():
            received.extend(chunk)
            if len(received) > limit:
                break
    except ClientDisconnect as e:
        msg = "The upload was cut off"
        raise UploadCutOffError(msg) from e
    return bytes(received)


@router.get("/images/{image_id}")
async def serve_an_image(
    image_id: str,
    image_service: ImageService = Depends(get_image_service),
) -> FileResponse:
    """Hand back an image this review keeps, to be drawn in the panel."""
    stored = image_service.kept(image_id)
    return FileResponse(stored.path, media_type=stored.media_type)


@router.delete("/images/{image_id}", status_code=HTTPStatus.NO_CONTENT)
async def discard_an_image(
    image_id: str,
    image_service: ImageService = Depends(get_image_service),
) -> None:
    """Drop an image the reader took off the message before sending it.

    One that went out with a message stays: the agent may still be about to
    open it, and nothing on this side knows when it has.
    """
    await image_service.discard(image_id)
    log.info("image_discarded", image_id=image_id)


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


def _hand_over_thread(thread: ThreadInput, image_service: ImageService) -> Thread:
    """Take a thread off the wire, turns and all, and hand its images over.

    Every image it names becomes a file the agent may open, kept until the
    review ends; one this review no longer keeps drops out.
    """
    return Thread(
        thread_id=thread.thread_id,
        anchor=thread.anchor,
        severity=thread.severity,
        body=thread.body,
        images=_hand_over_kept(thread.images, image_service),
        turns=[_hand_over_turn(turn, image_service) for turn in thread.turns],
        raised_by=thread.raised_by,
        resolved=thread.resolved,
    )


def _hand_over_turn(turn: TurnInput, image_service: ImageService) -> Turn:
    """Take one turn off the wire, and hand its images over."""
    return Turn(
        author=turn.author,
        body=turn.body,
        round=turn.round,
        images=_hand_over_kept(turn.images, image_service),
    )


@router.post("/say", status_code=HTTPStatus.NO_CONTENT)
async def say_in_panel(
    request: SayRequest,
    state: ServerState = Depends(get_state),
    clock: Clock = Depends(get_clock),
) -> None:
    """Push what the agent has to say into a review still open.

    An answer names the message it answers. A message that names nothing is
    the agent speaking first, which is worth as much: work finished while
    the reader was reading is news they would otherwise have to ask for.
    """
    state.push(ChatPush(message_id=request.message_id, text=request.text, files=request.files))
    state.end_work_for(request.message_id)
    state.panel.append(
        PanelEntry(
            message_id=request.message_id,
            author=TurnAuthor.AUTHOR,
            text=request.text,
            at=clock.now(),
        )
    )
    log.info("panel_answer", message_id=request.message_id, unprompted=request.message_id is None)


@router.post("/progress", status_code=HTTPStatus.NO_CONTENT)
async def report_progress(
    request: ProgressRequest,
    state: ServerState = Depends(get_state),
    clock: Clock = Depends(get_clock),
) -> None:
    """Say what is being done, while it is being done.

    Waiting says only that something is happening. This says what: which
    files are being touched and what is being made of them. It replaces
    whatever was showing — the state of the work, not a log of it — and an
    empty one takes the line away.
    """
    state.report_work(
        None
        if request.says_nothing()
        else AgentWork(
            message_id=request.message_id,
            text=request.text,
            files=request.files,
            steps=request.steps,
            at=clock.now(),
        )
    )


@router.post("/show", status_code=HTTPStatus.NO_CONTENT)
async def show_a_file(
    request: ShowRequest,
    state: ServerState = Depends(get_state),
) -> None:
    """Take the reader to a file, and mark it for a moment when they arrive.

    The only thing here that moves somebody else's screen, so it is only
    ever sent when they asked to be taken somewhere.
    """
    state.push(ShowPush(file=request.file))
    log.info("file_shown", file=request.file)


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
    # Quoted here, from the diff the anchor will be followed through: the
    # lines are what let the thread find its code again when it moves
    anchor = anchors.quote(request.anchor)

    thread_id = state.raise_id()
    state.push(PointPush(thread_id=thread_id, anchor=anchor, body=request.body, severity=request.severity))
    log.info("thread_raised", thread_id=thread_id, where=anchor.where())
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
    return FollowResponse(anchors=[anchors.follow(anchor) for anchor in request.anchors])


@router.post("/cancel", status_code=HTTPStatus.NO_CONTENT)
async def cancel_panel_message(
    request: CancelRequest,
    state: ServerState = Depends(get_state),
) -> None:
    """Take back a message the agent has not answered yet.

    A request rather than a kill: it joins the queue behind whatever else is
    waiting, and the agent decides what to do about it. Nothing here can
    reach into another process and stop it mid-thought.
    """
    state.inbox.hand_in(PanelCancel(message_id=request.message_id))
    state.end_work_for(request.message_id)
    log.info("panel_cancelled", message_id=request.message_id)


@router.post("/status", status_code=HTTPStatus.NO_CONTENT)
async def report_status(
    request: StatusRequest,
    state: ServerState = Depends(get_state),
    clock: Clock = Depends(get_clock),
) -> None:
    """Take what the agent says about itself, and pass it on unchanged.

    Which model, and how much of its context is spent: neither can be
    measured from here, so both are quoted with the time they were said.
    """
    # Replaced whole rather than changed in place: a push already queued
    # carries the status as it was when it was said
    state.agent = AgentStatus(
        model=request.model if request.model is not None else state.agent.model,
        context=request.context if request.context is not None else state.agent.context,
        at=clock.now(),
    )
    state.push(StatusPush(agent=state.agent))
    log.info("agent_status", model=state.agent.model, context=state.agent.context)


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
    pump = asyncio.create_task(_forward(outbox, websocket))
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


async def _forward(outbox: asyncio.Queue[ServerPush], websocket: WebSocket) -> None:
    """Send down the socket everything pushed to it, for as long as it is open."""
    while True:
        await websocket.send_text((await outbox.get()).model_dump_json())


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
        heard = ReceivedHello.model_validate_json(said)
    except ValidationError as error:
        # The socket is a lifeline first; nonsense on it is not worth
        # dropping a review over, but worth a line for whoever debugs it
        log.debug("hello_refused", errors=error.error_count())
        return

    if heard.round is not None and heard.round > state.round:
        log.info("round_caught_up", was=state.round, now=heard.round)
        state.round = heard.round

    if heard.threads is not None:
        state.hold_threads(HeldThreads.read(heard.threads))


@router.post("/submit")
async def submit_review(
    request: SubmitRequest,
    state: ServerState = Depends(get_state),
    mode: ReviewMode = Depends(get_review_mode),
    diff_files: list[DiffFile] = Depends(get_diff_files),
    image_service: ImageService = Depends(get_image_service),
) -> SubmitResponse:
    """Send what has been written, and either end the review or carry on.

    Ending is the plain case: one send, and the agent reads the result on
    stdout. A round keeps the review open instead — the threads stay on
    screen, so an answer has somewhere to come back to.
    """
    if state.shutdown_event.is_set():
        msg = "Review already submitted"
        raise ReviewEndedError(msg)

    threads = [_hand_over_thread(thread, image_service) for thread in request.threads]
    sent_round = state.round

    if mode == ReviewMode.TRANSCRIPT:
        result = TranscriptReviewService().format_review(threads, request.body, diff_files, round_number=sent_round)
    else:
        result = ReviewService().format_review(threads, body=request.body, round_number=sent_round)

    state.last_round = RoundSubmission(number=sent_round, markdown=result.markdown, comment_count=result.comment_count)
    state.inbox.hand_in(state.last_round)

    if request.end:
        state.shutdown_event.set()
    else:
        state.round += 1
        state.push(RoundPush(number=state.round))

    log.info("review_submitted", comment_count=result.comment_count, round=sent_round, ended=request.end)

    return SubmitResponse(
        markdown=result.markdown,
        comment_count=result.comment_count,
        round=sent_round,
        ended=request.end,
    )


@router.post("/round")
async def retake_diff(
    http_request: Request,
    state: ServerState = Depends(get_state),
    root: Path | None = Depends(get_repo_root),
    base: str | None = Depends(get_diff_base),
    objects: Path | None = Depends(get_objects),
    clock: Clock = Depends(get_clock),
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
        msg = "No repository to retake the diff from"
        raise NoRepositoryError(msg)

    git = GitRepository(objects=objects)
    versions = VersionService(git_repository=git, clock=clock)
    # One retake at a time, each about one round: a round sent while git is
    # working must not tag this retake's mark with the round after it
    async with state.retaking:
        round_number = state.round
        # Asked before the new tree is written down, while the last mark is
        # still the one the diff on screen was taken at
        read_at = versions.began(state.snapshots, round_number)
        changes = await versions.changed_since(root, read_at)

        files = await DiffService(git_repository=git).get_diff(root, base=base)
        http_request.app.state.diff_files = files
        # Read after the diff, not before: a file saved in between then belongs
        # to the tree the diff was taken at, and the reader is not told about a
        # change that is already on their screen.
        state.tree = await TreeWatcherService(git_repository=git).read(root)
        if (mark := await versions.take(root, round_number=round_number)) is not None:
            state.snapshots.append(mark)

    state.push(DiffPush(changes=changes))
    log.info("diff_retaken", file_count=len(files), round=round_number, changed=len(changes.paths) if changes else None)

    return RoundResponse(file_count=len(files), round=round_number, changes=changes)


@router.post("/end", status_code=HTTPStatus.NO_CONTENT)
async def end_review(state: ServerState = Depends(get_state)) -> None:
    """End a review that has been kept open for rounds."""
    state.shutdown_event.set()
    log.info("review_ended", round=state.round)
