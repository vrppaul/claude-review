"""What the review's own page asks of it: its content, the threads asked about, the panel, the rounds."""

from http import HTTPStatus

import structlog
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse

from claude_review.presentation.dependencies import get_release, get_review
from claude_review.presentation.schemas import (
    MAX_ID_LENGTH,
    AskRequest,
    CancelRequest,
    DiffResponse,
    FileWindowResponse,
    FollowRequest,
    FollowResponse,
    ImageResponse,
    MessageRequest,
    RoundResponse,
    SendLimits,
    SubmitRequest,
    SubmitResponse,
    VersionsResponse,
)
from claude_review.services.image_service import MAX_IMAGE_BYTES
from claude_review.services.review.review import Review

log = structlog.get_logger()

router = APIRouter()


@router.get("/diff")
async def get_diff(
    ignore_whitespace: bool = Query(default=False),
    base: str | None = Query(default=None, max_length=MAX_ID_LENGTH),
    review: Review = Depends(get_review),
    release: str = Depends(get_release),
) -> DiffResponse:
    """Serve the review's content, against the base the page asks for, and where the review stands."""
    view = await review.source.view(base, ignore_whitespace=ignore_whitespace)
    return DiffResponse(
        files=view.files,
        mode=review.mode,
        title=review.title,
        phrase=view.phrase,
        round=review.rounds.current,
        answerer_attached=review.answerer.attached,
        agent=review.answerer.status,
        moved=view.moved,
        limits=SendLimits(),
        release=release,
    )


@router.get("/versions")
async def offered_versions(review: Review = Depends(get_review)) -> VersionsResponse:
    """Say what the working tree can be compared against: nothing at all, for files or a conversation."""
    return VersionsResponse(versions=await review.source.offer())


@router.get("/file-window")
async def get_file_window(
    path: str = Query(min_length=1),
    start: int = Query(ge=1),
    end: int = Query(ge=1),
    review: Review = Depends(get_review),
) -> FileWindowResponse:
    """Serve lines a hunk left out, so the reader can widen its context."""
    window = await review.source.file_window(path, start, end)
    return FileWindowResponse(start=window.start, lines=window.lines, total=window.total)


@router.post("/anchors/follow")
async def follow_anchors(request: FollowRequest, review: Review = Depends(get_review)) -> FollowResponse:
    """Say where each anchor is in the review's content as it now stands.

    The page holds the threads and the review holds the content, so after a
    round the threads come here to be moved: one whose lines survived
    follows them, one whose lines are gone is marked outdated and keeps its
    quote.
    """
    anchors = review.content.anchors
    return FollowResponse(anchors=[anchors.follow(anchor) for anchor in request.anchors])


@router.post("/ask", status_code=HTTPStatus.NO_CONTENT)
async def ask_about_thread(request: AskRequest, review: Review = Depends(get_review)) -> None:
    """Take a question asked in one thread, for whoever is answering to pick up.

    The reader does not wait here: the answer arrives later, pushed down the
    session socket, so writing the review is never blocked on a reply.
    """
    review.ask(request.question_id, request.thread.draft())


@router.post("/message", status_code=HTTPStatus.NO_CONTENT)
async def take_panel_message(request: MessageRequest, review: Review = Depends(get_review)) -> None:
    """Take what the reader typed in the panel, for the agent to pick up.

    Everything typed there goes now — the panel has no "add to review",
    because a message about the plan or the tests belongs to no thread and
    has nothing to wait for.
    """
    review.take_message(
        message_id=request.message_id,
        body=request.body,
        threads=[thread.draft() for thread in request.threads],
        image_ids=request.images,
    )


@router.post("/cancel", status_code=HTTPStatus.NO_CONTENT)
async def cancel_panel_message(request: CancelRequest, review: Review = Depends(get_review)) -> None:
    """Take back a message the agent has not answered yet.

    A request rather than a kill: it joins the queue behind whatever else is
    waiting, and the agent decides what to do about it.
    """
    review.take_back(request.message_id)


@router.post("/images")
async def keep_an_image(http_request: Request, review: Review = Depends(get_review)) -> ImageResponse:
    """Keep an image the reader is about to send, and say what it is called.

    Taken on its own, before the message: the reader sees it attached while
    still writing, and the message then carries an id rather than the bytes.
    The body is the image itself rather than a form, so there is nothing to
    parse.
    """
    stored = await review.images.keep(await _read_capped(http_request, limit=MAX_IMAGE_BYTES))
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


@router.get("/images/{image_id}")
async def serve_an_image(image_id: str, review: Review = Depends(get_review)) -> FileResponse:
    """Hand back an image this review keeps, to be drawn in the panel."""
    stored = review.images.kept(image_id)
    return FileResponse(stored.path, media_type=stored.media_type)


@router.delete("/images/{image_id}", status_code=HTTPStatus.NO_CONTENT)
async def discard_an_image(image_id: str, review: Review = Depends(get_review)) -> None:
    """Drop an image the reader took off the message before sending it.

    One that went out with a message stays: the agent may still be about to
    open it, and nothing on this side knows when it has.
    """
    await review.images.discard(image_id)
    log.info("image_discarded", image_id=image_id)


@router.post("/submit")
async def submit_review(request: SubmitRequest, review: Review = Depends(get_review)) -> SubmitResponse:
    """Send what has been written, and either end the review or carry on.

    Ending is the plain case: one send, and the agent reads the result on
    stdout. A round keeps the review open instead — the threads stay on
    screen, so an answer has somewhere to come back to.
    """
    sent = review.submit(threads=[thread.draft() for thread in request.threads], body=request.body, ends=request.end)
    return SubmitResponse(
        markdown=sent.markdown, comment_count=sent.comment_count, round=sent.number, ended=request.end
    )


@router.post("/round")
async def retake_diff(review: Review = Depends(get_review)) -> RoundResponse:
    """Take the diff again, after the work a round asked for: the agent asks, and so does the page.

    The pages on screen are told to reload it rather than being handed the
    files: a page has its own view of the diff — which files are folded,
    whether whitespace counts — and asking it to fetch keeps that one path.
    They are also told which files moved: a file the reader had ticked off
    keeps its tick through a retake, so without this they walk past code the
    agent rewrote under them.
    """
    retaken = await review.retake()
    return RoundResponse(file_count=retaken.file_count, round=retaken.round, changes=retaken.changes)


@router.post("/end", status_code=HTTPStatus.NO_CONTENT)
async def end_review(review: Review = Depends(get_review)) -> None:
    """End a review that has been kept open for rounds."""
    review.end()
