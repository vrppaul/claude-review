"""What the agent answering the review asks of it: what to answer next, what the review holds, where to say things."""

from http import HTTPStatus
from typing import assert_never

from fastapi import APIRouter, Depends, Path as PathParameter, Query, Request

from claude_review.domain.models import (
    AgentEvent,
    PanelCancel,
    PanelMessage,
    RoundSubmission,
    Thread,
    ThreadQuestion,
)
from claude_review.presentation.dependencies import get_review
from claude_review.presentation.schemas import (
    DEFAULT_WAIT_SECONDS,
    MAX_ID_LENGTH,
    MAX_WAIT_SECONDS,
    SAFE_ID,
    CancelEvent,
    ClosedEvent,
    ContextResponse,
    EventResponse,
    MessageEvent,
    PointRequest,
    PointResponse,
    ProgressRequest,
    QuestionEvent,
    ReplyRequest,
    RoundEvent,
    SayRequest,
    ShowRequest,
    StatusRequest,
    ThreadSummary,
    TimeoutEvent,
)
from claude_review.services.review.agent_inbox import Silence
from claude_review.services.review.review import Review


async def note_the_agent(review: Review = Depends(get_review)) -> None:
    """Whatever the agent asks says it is still there: every call renews its lease."""
    review.answerer.heard()


router = APIRouter(dependencies=[Depends(note_the_agent)])


@router.get("/events")
async def next_event(
    http_request: Request,
    wait_seconds: float = Query(default=DEFAULT_WAIT_SECONDS, gt=0, le=MAX_WAIT_SECONDS),
    review: Review = Depends(get_review),
) -> EventResponse:
    """Wait for the next thing the reader hands over.

    A long poll rather than a socket: the caller is a command in a shell,
    and blocking until there is something to do is exactly its shape.
    Returning "timeout" lets the caller decide whether to keep waiting.
    """
    return _envelope(await review.next_event(within=wait_seconds, caller_left=_until_the_caller_leaves(http_request)))


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


@router.get("/context")
async def review_context(review: Review = Depends(get_review)) -> ContextResponse:
    """Say what this review holds, for an agent that has just arrived.

    An agent restarted mid-review knows nothing: `events` hands over what
    happens next, never what already happened. Everything here has passed
    through this review, so it can say what was asked, what was answered and
    what is still open — as an index, because handing over the whole review
    unasked is how a catch-up costs more than the work. A thread is read in
    full from its own route.
    """
    return ContextResponse(
        title=review.title,
        round=review.rounds.current,
        file_count=len(review.content.files),
        answerer_attached=review.answerer.attached,
        agent=review.answerer.status,
        threads=[ThreadSummary.of(held) for held in review.threads.held],
        panel=review.conversation.entries,
    )


@router.get("/context/threads/{thread_id}")
async def read_thread(
    thread_id: str = PathParameter(max_length=MAX_ID_LENGTH, pattern=SAFE_ID),
    review: Review = Depends(get_review),
) -> Thread:
    """Hand over one thread the review holds, in full: every turn, its lines, its images.

    Read, so handed over: the agent may open its images from now on, and
    the reader can no longer take them off.
    """
    return review.read_thread(thread_id)


@router.post("/reply", status_code=HTTPStatus.NO_CONTENT)
async def reply_to_thread(request: ReplyRequest, review: Review = Depends(get_review)) -> None:
    """Push an answer into a thread of a review that is still open."""
    review.answer_thread(thread_id=request.thread_id, question_id=request.question_id, body=request.body)


@router.post("/say", status_code=HTTPStatus.NO_CONTENT)
async def say_in_panel(request: SayRequest, review: Review = Depends(get_review)) -> None:
    """Push what the agent has to say into a review still open.

    An answer names the message it answers. A message that names nothing is
    the agent speaking first, which is worth as much: work finished while
    the reader was reading is news they would otherwise have to ask for.
    """
    review.agent_says(message_id=request.message_id, body=request.body, files=request.files)


@router.post("/progress", status_code=HTTPStatus.NO_CONTENT)
async def report_progress(request: ProgressRequest, review: Review = Depends(get_review)) -> None:
    """Say what is being done, while it is being done.

    Waiting says only that something is happening. This says what: which
    files are being touched and what is being made of them. It replaces
    whatever was showing — the state of the work, not a log of it — and an
    empty one takes the line away.
    """
    review.answerer.report_work(
        message_id=request.message_id, text=request.text, files=request.files, steps=request.steps
    )


@router.post("/show", status_code=HTTPStatus.NO_CONTENT)
async def show_a_file(request: ShowRequest, review: Review = Depends(get_review)) -> None:
    """Take the reader to a file, and mark it for a moment when they arrive.

    The only thing here that moves somebody else's screen, so it is only
    ever sent when they asked to be taken somewhere.
    """
    review.show(request.file)


@router.post("/point")
async def raise_a_thread(request: PointRequest, review: Review = Depends(get_review)) -> PointResponse:
    """Put a thread on a line, from the side that wrote the change.

    "Here I did it differently from what you asked" belongs on the line it
    is about, not in a paragraph somewhere else. What arrives is an ordinary
    thread: the reader answers it, settles it or removes it. It is drawn as
    the author's, though, and it is never counted as the reader's own work.
    """
    return PointResponse(thread_id=review.raise_thread(request.anchor, body=request.body, severity=request.severity))


@router.post("/status", status_code=HTTPStatus.NO_CONTENT)
async def report_status(request: StatusRequest, review: Review = Depends(get_review)) -> None:
    """Take what the agent says about itself, and pass it on unchanged.

    Which model, and how much of its context is spent: neither can be
    measured from here, so both are quoted with the time they were said.
    """
    review.answerer.report_status(model=request.model, context=request.context)
