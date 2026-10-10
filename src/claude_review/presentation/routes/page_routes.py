"""What the review's own page asks of it: its content, the threads asked about, the panel, the rounds."""

from http import HTTPStatus

import structlog
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse

from claude_review.domain.exceptions import (
    FileNotInReviewError,
    FileUnreadableError,
    ImageAlreadySentError,
    ImageRefusedError,
    ImagesNotKeptError,
    ImageTooLargeError,
    LineRangeError,
    NoRepositoryError,
    PathOutsideRepositoryError,
    QuestionNotInThreadError,
    ReviewEndedError,
    UnknownImageError,
    UnknownVersionError,
)
from claude_review.domain.models import ReviewKey
from claude_review.presentation.body_limit import BodyTooLargeError
from claude_review.presentation.broadcast import BrowserBroadcast
from claude_review.presentation.dependencies import get_broadcast, get_release, get_review
from claude_review.presentation.refusals import Takes, refusals
from claude_review.presentation.version_words import (
    changes_on_the_wire,
    key_of,
    key_text,
    phrase_of,
    version_on_the_wire,
)
from claude_review.presentation.wire.agent import AgentStatus, AgentWork, CancelRequest, ImageResponse, MessageRequest
from claude_review.presentation.wire.base import MAX_ID_LENGTH
from claude_review.presentation.wire.content import (
    SEND_LIMITS,
    DiffFile,
    DiffResponse,
    FileWindowResponse,
    RetakeResponse,
    ReviewResponse,
    VersionsResponse,
)
from claude_review.presentation.wire.threads import (
    AskRequest,
    FollowRequest,
    FollowResponse,
    SubmitRequest,
    SubmitResponse,
    anchor_in_the_review,
    anchor_on_the_wire,
)
from claude_review.services.image_service import MAX_IMAGE_BYTES
from claude_review.services.review.review import Review

log = structlog.get_logger()

router = APIRouter()


@router.get("/review")
async def get_the_review(
    review: Review = Depends(get_review),
    release: str = Depends(get_release),
    broadcast: BrowserBroadcast = Depends(get_broadcast),
) -> ReviewResponse:
    """Say what the review is and where it stands: what a page opening, or coming back, must learn."""
    standing = review.standing()
    work = review.work_under_way()
    told = broadcast.position()
    return ReviewResponse(
        title=standing.title,
        mode=standing.mode,
        round=standing.round,
        answerer_attached=standing.answerer_attached,
        agent=AgentStatus.of(standing.agent),
        work=AgentWork.of(work) if work is not None else None,
        limits=SEND_LIMITS,
        release=release,
        instance=told.instance,
        sequence=told.sequence,
    )


@router.get("/diff", responses=refusals(UnknownVersionError, NoRepositoryError, takes=Takes.PARAMETERS))
async def get_diff(
    *,
    ignore_whitespace: bool = Query(default=False),
    base: str | None = Query(default=None, max_length=MAX_ID_LENGTH),
    review: Review = Depends(get_review),
) -> DiffResponse:
    """Serve the review's content against the base the page asks for.

    The page is told the key of the base in force and of the review's own,
    so it asks for the one and goes back to the other without building a key
    itself.
    """
    view = await review.view(key_of(base) if base is not None else None, ignore_whitespace=ignore_whitespace)
    opened_against = review.standing().opened_against
    return DiffResponse(
        files=[DiffFile.of(file) for file in view.files],
        phrase=phrase_of(view.shown, opened_against) if view.shown is not None else None,
        base_key=key_text(view.shown) if view.shown is not None else None,
        review_key=key_text(ReviewKey()) if view.shown is not None else None,
        moved=view.moved,
    )


@router.get("/versions")
async def offered_versions(review: Review = Depends(get_review)) -> VersionsResponse:
    """Say what the working tree can be compared against: nothing at all, for files or a conversation."""
    opened_against = review.standing().opened_against
    return VersionsResponse(versions=[version_on_the_wire(offered, opened_against) for offered in await review.offer()])


@router.get(
    "/file-window",
    responses=refusals(
        NoRepositoryError,
        LineRangeError,
        PathOutsideRepositoryError,
        FileNotInReviewError,
        FileUnreadableError,
        takes=Takes.PARAMETERS,
    ),
)
async def get_file_window(
    path: str = Query(min_length=1),
    start: int = Query(ge=1),
    end: int = Query(ge=1),
    review: Review = Depends(get_review),
) -> FileWindowResponse:
    """Serve lines a hunk left out, so the reader can widen its context."""
    window = await review.file_window(path, start, end)
    return FileWindowResponse(start=window.start, lines=window.lines, total=window.total)


@router.post("/anchors/follow", responses=refusals(takes=Takes.JSON_BODY))
async def follow_anchors(request: FollowRequest, review: Review = Depends(get_review)) -> FollowResponse:
    """Say where each anchor is in the review's content as it now stands.

    The page holds the threads and the review holds the content, so after a
    round the threads come here to be moved: one whose lines survived
    follows them, one whose lines are gone is marked outdated and keeps its
    quote.
    """
    followed = review.follow([anchor_in_the_review(anchor) for anchor in request.anchors])
    return FollowResponse(anchors=[anchor_on_the_wire(anchor) for anchor in followed])


@router.post(
    "/ask",
    status_code=HTTPStatus.NO_CONTENT,
    responses=refusals(QuestionNotInThreadError, takes=Takes.JSON_BODY),
)
async def ask_about_thread(request: AskRequest, review: Review = Depends(get_review)) -> None:
    """Take a question asked in one thread, for whoever is answering to pick up.

    The reader does not wait here: the answer arrives later, pushed down the
    session socket, so writing the review is never blocked on a reply.
    """
    review.ask(request.question_id, request.thread.in_the_review())


@router.post(
    "/message",
    status_code=HTTPStatus.NO_CONTENT,
    responses=refusals(ImagesNotKeptError, takes=Takes.JSON_BODY),
)
async def take_panel_message(request: MessageRequest, review: Review = Depends(get_review)) -> None:
    """Take what the reader typed in the panel, for the agent to pick up.

    Everything typed there goes now — the panel has no "add to review",
    because a message about the plan or the tests belongs to no thread and
    has nothing to wait for.
    """
    review.take_message(
        message_id=request.message_id,
        body=request.body,
        threads=[thread.in_the_review() for thread in request.threads],
        image_ids=request.images,
    )


@router.post("/cancel", status_code=HTTPStatus.NO_CONTENT, responses=refusals(takes=Takes.JSON_BODY))
async def cancel_panel_message(request: CancelRequest, review: Review = Depends(get_review)) -> None:
    """Take back a message the agent has not answered yet.

    A request rather than a kill: it joins the queue behind whatever else is
    waiting, and the agent decides what to do about it.
    """
    review.take_back(request.message_id)


@router.post("/images", responses=refusals(BodyTooLargeError, ImageRefusedError, ImageTooLargeError))
async def keep_an_image(http_request: Request, review: Review = Depends(get_review)) -> ImageResponse:
    """Keep an image the reader is about to send, and say what it is called.

    Taken on its own, before the message: the reader sees it attached while
    still writing, and the message then carries an id rather than the bytes.
    The body is the image itself rather than a form, so there is nothing to
    parse.
    """
    stored = await review.keep_image(await _read_capped(http_request, limit=MAX_IMAGE_BYTES))
    log.info("image_kept", image_id=stored.image_id, size=stored.size)
    return ImageResponse(image_id=stored.image_id)


async def _read_capped(http_request: Request, *, limit: int) -> bytes:
    """Read a body, stopping as soon as it runs past the limit.

    Past it is enough to know it is too big, and the rest is never held.
    A browser gone mid-upload ends the read with `ClientDisconnect`, which
    the app drops as a request cut off.
    """
    received = bytearray()
    async for chunk in http_request.stream():
        received.extend(chunk)
        if len(received) > limit:
            break
    return bytes(received)


@router.get("/images/{image_id}", responses=refusals(UnknownImageError, takes=Takes.PARAMETERS))
async def serve_an_image(image_id: str, review: Review = Depends(get_review)) -> FileResponse:
    """Hand back an image this review keeps, to be drawn in the panel."""
    stored = review.kept_image(image_id)
    return FileResponse(stored.path, media_type=stored.media_type)


@router.delete(
    "/images/{image_id}",
    status_code=HTTPStatus.NO_CONTENT,
    responses=refusals(UnknownImageError, ImageAlreadySentError, takes=Takes.PARAMETERS),
)
async def discard_an_image(image_id: str, review: Review = Depends(get_review)) -> None:
    """Drop an image the reader took off the message before sending it.

    One that went out with a message stays: the agent may still be about to
    open it, and nothing on this side knows when it has.
    """
    await review.discard_image(image_id)
    log.info("image_discarded", image_id=image_id)


@router.post("/submit", responses=refusals(ReviewEndedError, takes=Takes.JSON_BODY))
async def submit_review(request: SubmitRequest, review: Review = Depends(get_review)) -> SubmitResponse:
    """Send what has been written, and either end the review or carry on.

    Ending is the plain case: one send, and the agent reads the result on
    stdout. A round keeps the review open instead — the threads stay on
    screen, so an answer has somewhere to come back to.
    """
    sent = review.submit(
        threads=[thread.in_the_review() for thread in request.threads], body=request.body, ends=request.end
    )
    return SubmitResponse(
        markdown=sent.markdown, comment_count=sent.comment_count, round=sent.number, ended=request.end
    )


@router.post("/retake", responses=refusals(NoRepositoryError))
async def retake_diff(review: Review = Depends(get_review)) -> RetakeResponse:
    """Take the diff again, after the work a round asked for: the agent asks, and so does the page.

    The pages on screen are told to reload it rather than being handed the
    files: a page has its own view of the diff — which files are folded,
    whether whitespace counts — and asking it to fetch keeps that one path.
    They are also told which files moved: a file the reader had ticked off
    keeps its tick through a retake, so without this they walk past code the
    agent rewrote under them.
    """
    retaken = await review.retake()
    return RetakeResponse(
        file_count=retaken.file_count, round=retaken.round, changes=changes_on_the_wire(retaken.changes)
    )


@router.post("/end", status_code=HTTPStatus.NO_CONTENT)
async def end_review(review: Review = Depends(get_review)) -> None:
    """End a review that has been kept open for rounds."""
    review.end()
