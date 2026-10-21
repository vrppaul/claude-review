"""What the review's own page asks of it: its content, the threads asked about, the panel, the rounds."""

from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Query, Request
from fastapi.responses import FileResponse

from claude_review.domain.exceptions import (
    AgentWordsChangedError,
    AnchorLinesNotShownError,
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
from claude_review.domain.models import FIRST_LINE, MAX_ID_LENGTH, MAX_PATH_LENGTH
from claude_review.presentation.dependencies import BroadcastDep, ReleaseDep, ReviewDep
from claude_review.presentation.errors import Takes, refusals
from claude_review.presentation.schemas.agent import (
    AgentStatus,
    AgentWork,
    CancelRequest,
    ConversationResponse,
    ImageResponse,
    MessageRequest,
    SaidInPanel,
)
from claude_review.presentation.schemas.base import SafeId, made_or_none
from claude_review.presentation.schemas.content import (
    SEND_LIMITS,
    DiffFile,
    DiffResponse,
    FileWindowResponse,
    RetakeResponse,
    ReviewResponse,
    StoryAsking,
    VersionsResponse,
    where_from_domain,
)
from claude_review.presentation.schemas.story import StoryHeld, StoryResponse
from claude_review.presentation.schemas.threads import (
    AskRequest,
    FollowRequest,
    FollowResponse,
    SubmitRequest,
    SubmitResponse,
    ThreadDraft,
    ThreadsResponse,
    anchor_from_domain,
)
from claude_review.presentation.version_labels import (
    changes_since_round,
    key_of,
    review_version,
    shown_base,
)
from claude_review.services.image_service import IMAGE_FORMATS, MAX_IMAGE_BYTES

router = APIRouter()


@router.get("/review")
async def get_the_review(review: ReviewDep, release: ReleaseDep, broadcast: BroadcastDep) -> ReviewResponse:
    """Say what the review is and where it stands: what a page opening, or coming back, must learn."""
    standing = review.standing()
    work = review.work_under_way()
    told = broadcast.position()
    return ReviewResponse(
        title=standing.title,
        where=where_from_domain(standing.where),
        identity=standing.identity,
        round=standing.round,
        answerer_attached=standing.answerer_attached,
        agent=AgentStatus.from_domain(standing.agent),
        work=made_or_none(AgentWork.from_domain, work),
        takes_a_story=standing.takes_a_story,
        story_asking=made_or_none(StoryAsking.from_domain, standing.story_asking),
        limits=SEND_LIMITS,
        release=release,
        instance=told.instance,
        sequence=told.sequence,
    )


@router.get("/threads")
async def held_threads(review: ReviewDep) -> ThreadsResponse:
    """Say what threads the review holds, for a page that opens with no draft of them.

    Another browser, a private window, cleared site data: the page has none
    of the reader's threads, nor the agent's. It takes these as its own
    rather than saying it holds none — which would leave an agent arriving
    later with nothing to read. Read-only: no page is told what another
    holds once it is open.
    """
    return ThreadsResponse(threads=[ThreadDraft.from_domain(held) for held in review.threads_held()])


@router.get("/conversation")
async def held_conversation(review: ReviewDep) -> ConversationResponse:
    """Say what was said in the panel, for a page to draw as it opens.

    What the agent said before any page was open is pushed to nobody, and a
    page in another browser, or a private window, has no draft of what this
    one saw. Every part comes under the id a page that heard it holds it by,
    so a page with a draft draws each part once. Read-only, like the threads.
    """
    return ConversationResponse(said=[SaidInPanel.from_domain(said) for said in review.conversation_held()])


@router.get("/story")
async def held_story(review: ReviewDep) -> StoryResponse:
    """Say what story the review holds: the last the agent told of its change, each step with what it shows.

    None while nobody has told one, which is no refusal: a review is read
    without a story as it always was. How the reader's asking for one
    stands is read with the review's facts, which say how far the telling
    had got.
    """
    held = review.story_held()
    return StoryResponse(held=made_or_none(StoryHeld.from_domain, held))


@router.post(
    "/story/request", status_code=HTTPStatus.NO_CONTENT, responses=refusals(NoRepositoryError, takes=Takes.NOTHING)
)
async def ask_for_a_story(review: ReviewDep) -> None:
    """Take the reader's asking for a story of the change, for an agent to pick up.

    Asked once however often it is sent: two pages open on the review, or
    two presses, hand the agent one request. The reader does not wait here:
    every page is told how the asking stands, and then that a story was told.
    """
    review.ask_for_story()


@router.post("/story/cancel", status_code=HTTPStatus.NO_CONTENT)
async def stop_the_story(review: ReviewDep) -> None:
    """Stop the story the reader asked for, taken by an agent or not.

    Nothing is refused: with no story awaited there is nothing to stop,
    and that is what the reader wanted. A story an agent sends all the
    same is still taken.
    """
    review.stop_story()


@router.get("/diff", responses=refusals(UnknownVersionError, NoRepositoryError, takes=Takes.PARAMETERS))
async def get_diff(
    review: ReviewDep,
    *,
    ignore_whitespace: bool = False,
    base: Annotated[str | None, Query(max_length=MAX_ID_LENGTH)] = None,
) -> DiffResponse:
    """Serve the review's content against the base the page asks for, the review's own when it names none.

    The page is told the key of the base in force, so it asks for it again
    without building a key itself, and whether it is narrower than the
    review's own, which it goes back to by naming none. And which take of
    the review it read, whatever the base: a story is of the code on screen
    only while it says the same take.
    """
    view = await review.view(made_or_none(key_of, base), ignore_whitespace=ignore_whitespace)
    opened_against = review.standing().opened_against
    return DiffResponse(
        files=[DiffFile.from_domain(file) for file in view.files],
        base=made_or_none(lambda shown: shown_base(shown, opened_against), view.shown),
        moved=view.moved,
        take=view.take,
    )


@router.get("/versions")
async def offered_versions(review: ReviewDep) -> VersionsResponse:
    """Say what the working tree can be compared against: nothing at all, for files or a conversation."""
    opened_against = review.standing().opened_against
    return VersionsResponse(versions=[review_version(offered, opened_against) for offered in await review.offer()])


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
    # Any path the diff draws, a name holding a control character too: one
    # that cannot be commented on can still be read wider
    path: Annotated[str, Query(min_length=1, max_length=MAX_PATH_LENGTH)],
    start: Annotated[int, Query(ge=FIRST_LINE)],
    end: Annotated[int, Query(ge=FIRST_LINE)],
    review: ReviewDep,
) -> FileWindowResponse:
    """Serve lines a hunk left out, so the reader can widen its context."""
    window = await review.file_window(path, start, end)
    return FileWindowResponse.from_domain(window)


@router.post("/anchors/follow", responses=refusals(takes=Takes.JSON_BODY))
async def follow_anchors(request: FollowRequest, review: ReviewDep) -> FollowResponse:
    """Say where each anchor is in the review's content as it now stands.

    The page holds the threads and the review holds the content, so after a
    round the threads come here to be moved: one whose lines survived
    follows them, one whose lines are gone is marked outdated and keeps its
    quote.
    """
    followed = review.follow([anchor.to_domain() for anchor in request.anchors])
    return FollowResponse(anchors=[anchor_from_domain(anchor) for anchor in followed])


@router.post(
    "/ask",
    status_code=HTTPStatus.NO_CONTENT,
    responses=refusals(
        QuestionNotInThreadError, AnchorLinesNotShownError, AgentWordsChangedError, takes=Takes.JSON_BODY
    ),
)
async def ask_about_thread(request: AskRequest, review: ReviewDep) -> None:
    """Take a question asked in one thread, for whoever is answering to pick up.

    The reader does not wait here: the answer arrives later, pushed down the
    session socket, so writing the review is never blocked on a reply.
    """
    review.ask(request.question_id, request.thread.to_domain())


@router.post(
    "/message",
    status_code=HTTPStatus.NO_CONTENT,
    responses=refusals(ImagesNotKeptError, AnchorLinesNotShownError, AgentWordsChangedError, takes=Takes.JSON_BODY),
)
async def take_panel_message(request: MessageRequest, review: ReviewDep) -> None:
    """Take what the reader typed in the panel, for the agent to pick up.

    Everything typed there goes now — the panel has no "add to review",
    because a message about the plan or the tests belongs to no thread and
    has nothing to wait for.
    """
    review.take_message(
        message_id=request.message_id,
        body=request.body,
        threads=[thread.to_domain() for thread in request.threads],
        image_ids=request.images,
    )


@router.post("/cancel", status_code=HTTPStatus.NO_CONTENT, responses=refusals(takes=Takes.JSON_BODY))
async def cancel_panel_message(request: CancelRequest, review: ReviewDep) -> None:
    """Take back a message the agent has not answered yet.

    A request rather than a kill: it joins the queue behind whatever else is
    waiting, and the agent decides what to do about it.
    """
    review.take_back(request.message_id)


# An image as the API describes one: the image itself, as bytes, in any
# format the review keeps
IMAGE_CONTENT = {known.media_type: {"schema": {"type": "string", "format": "binary"}} for known in IMAGE_FORMATS}
# What POST /images is sent, and what GET /images/{image_id} answers with
IMAGE_BODY = {"requestBody": {"required": True, "content": IMAGE_CONTENT}}
IMAGE_REPLY = {HTTPStatus.OK: {"description": "The image, as it was pasted", "content": IMAGE_CONTENT}}


@router.post(
    "/images", responses=refusals(ImageRefusedError, ImageTooLargeError, takes=Takes.RAW_BODY), openapi_extra=IMAGE_BODY
)
async def keep_an_image(http_request: Request, review: ReviewDep) -> ImageResponse:
    """Keep an image the reader is about to send, and say what it is called.

    Taken on its own, before the message: the reader sees it attached while
    still writing, and the message then carries an id rather than the bytes.
    The body is the image itself rather than a form, so there is nothing to
    parse.
    """
    stored = await review.keep_image(await _read_capped(http_request, limit=MAX_IMAGE_BYTES))
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


@router.get(
    "/images/{image_id}",
    response_class=FileResponse,
    responses={**IMAGE_REPLY, **refusals(UnknownImageError, takes=Takes.PARAMETERS)},
)
async def serve_an_image(image_id: SafeId, review: ReviewDep) -> FileResponse:
    """Hand back an image this review keeps, to be drawn in the panel."""
    stored = review.kept_image(image_id)
    return FileResponse(stored.path, media_type=stored.media_type)


@router.delete(
    "/images/{image_id}",
    status_code=HTTPStatus.NO_CONTENT,
    responses=refusals(UnknownImageError, ImageAlreadySentError, takes=Takes.PARAMETERS),
)
async def discard_an_image(image_id: SafeId, review: ReviewDep) -> None:
    """Drop an image the reader took off the message before sending it.

    One that went out with a message stays: the agent may still be about to
    open it, and nothing on this side knows when it has.
    """
    await review.discard_image(image_id)


@router.post(
    "/submit",
    responses=refusals(ReviewEndedError, AnchorLinesNotShownError, AgentWordsChangedError, takes=Takes.JSON_BODY),
)
async def submit_review(request: SubmitRequest, review: ReviewDep) -> SubmitResponse:
    """Send what has been written, and either end the review or carry on.

    Ending is the plain case: one send, and the agent reads the result on
    stdout. A round keeps the review open instead — the threads stay on
    screen, so an answer has somewhere to come back to.
    """
    sent = review.submit(
        threads=[thread.to_domain() for thread in request.threads], body=request.body, ends=request.end
    )
    return SubmitResponse(
        markdown=sent.markdown, comment_count=sent.comment_count, round=sent.number, ended=request.end
    )


@router.post("/retake", responses=refusals(NoRepositoryError, takes=Takes.NOTHING))
async def retake_diff(review: ReviewDep) -> RetakeResponse:
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
        file_count=retaken.file_count, round=retaken.round, changes=made_or_none(changes_since_round, retaken.changes)
    )


@router.post("/end", status_code=HTTPStatus.NO_CONTENT)
async def end_review(review: ReviewDep) -> None:
    """End a review that has been kept open for rounds."""
    review.end()
