"""Threads on the wire: what they hang on, what the page sends of them, and what the agent is handed."""

from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    Strict,
    TypeAdapter,
    ValidationError,
    computed_field,
    model_validator,
)

from claude_review.domain import models
from claude_review.domain.models import (
    FIRST_ITEM,
    FIRST_LINE,
    FIRST_ROUND,
    LARGEST_FILE_SHOWN_BYTES,
    MAX_QUOTE_LINES,
    STORY_QUOTE_TEXTS,
    AnchorKind,
    ChapterId,
    ChapterText,
    CommentSeverity,
    FilePath,
    LineSide,
    OverviewList,
    OverviewText,
    StoryBlockKind,
    TurnAuthor,
    says_nothing,
)
from claude_review.presentation.wire.base import (
    MAX_TEXT_LENGTH,
    MAX_THREADS,
    AgentText,
    ImageIds,
    WireBool,
    WireId,
    WireModel,
)
from claude_review.services.place_words import place_in_words

# The most turns one thread carries
MAX_TURNS = 200

# The longest line an anchor may quote. It quotes a line of the diff, which
# shows the lines of no file larger than this many bytes, and a character
# takes at least one
MAX_QUOTE_LINE_LENGTH = LARGEST_FILE_SHOWN_BYTES
# One line an anchor quotes, as the page and the agent send it
QuoteLine = Annotated[str, Field(max_length=MAX_QUOTE_LINE_LENGTH)]


class LineAnchor(WireModel):
    """Lines of one side of a file in the review's own diff, as the page and the agent name them.

    A quote left out is filled in by the review from its diff.
    """

    kind: Literal[AnchorKind.LINE] = AnchorKind.LINE
    file: FilePath
    side: LineSide
    start_line: int = Field(ge=FIRST_LINE)
    end_line: int = Field(ge=FIRST_LINE)
    quote: list[QuoteLine] = Field(default_factory=list, max_length=MAX_QUOTE_LINES)
    outdated: WireBool = False

    @model_validator(mode="after")
    def start_before_end(self) -> Self:
        models.check_line_span(self.start_line, self.end_line)
        return self


class OverviewBlock(WireModel):
    """One of the overview's three lines, by its name."""

    at: Literal[StoryBlockKind.OVERVIEW] = StoryBlockKind.OVERVIEW
    text: OverviewText


class ItemBlock(WireModel):
    """One thing a list of the overview holds, by where it stands in the list, counted from 0."""

    at: Literal[StoryBlockKind.ITEM] = StoryBlockKind.ITEM
    list: OverviewList
    # A number as JSON writes one, and nothing else: `false` would otherwise be read as the first item
    item: Annotated[int, Strict()] = Field(ge=FIRST_ITEM)


class ChapterBlock(WireModel):
    """What a chapter says of itself, the chapter by its id."""

    at: Literal[StoryBlockKind.CHAPTER] = StoryBlockKind.CHAPTER
    chapter: ChapterId
    text: ChapterText


class ReasonBlock(WireModel):
    """A step's reason, the step by its file and the first line it tells."""

    at: Literal[StoryBlockKind.REASON] = StoryBlockKind.REASON
    file: FilePath
    first_line: int = Field(ge=FIRST_LINE)


# A block of the story's words, as the wire carries it
type StoryBlock = Annotated[OverviewBlock | ItemBlock | ChapterBlock | ReasonBlock, Field(discriminator="at")]

# The words of a block a story anchor quotes: a text of the story, bounded as anything said in a review is
QuotedWords = Annotated[str, Field(max_length=MAX_TEXT_LENGTH)]


class StoryAnchor(WireModel):
    """A block of the words of the story told of the change, as the page and the agent name it.

    A quote left out is filled in by the review from the story it holds.
    """

    kind: Literal[AnchorKind.STORY] = AnchorKind.STORY
    block: StoryBlock
    quote: list[QuotedWords] = Field(default_factory=list, max_length=STORY_QUOTE_TEXTS)
    outdated: WireBool = False


# Everything a thread can hang on, as the wire carries it
type Anchor = Annotated[LineAnchor | StoryAnchor, Field(discriminator="kind")]


# Every kind of anchor, read from the other side's form by its fields
ANCHORS_ON_THE_WIRE: TypeAdapter[Anchor] = TypeAdapter(Anchor)
ANCHORS_IN_THE_REVIEW: TypeAdapter[models.Anchor] = TypeAdapter(models.Anchor)


def anchor_in_the_review(anchor: Anchor) -> models.Anchor:
    """The review's own form of an anchor the wire carried, whatever its kind."""
    return ANCHORS_IN_THE_REVIEW.validate_python(anchor, from_attributes=True)


def anchor_on_the_wire(anchor: models.Anchor) -> Anchor:
    """The wire's form of one of the review's anchors, whatever its kind."""
    return ANCHORS_ON_THE_WIRE.validate_python(anchor, from_attributes=True)


class Turn(WireModel):
    """One thing said in a thread after the comment that opened it, its screenshots as files to open."""

    author: TurnAuthor
    body: str
    round: int
    images: list[Path]


class Thread(WireModel):
    """A thread as the agent is handed it: where it is, everything said in it, its screenshots as files."""

    thread_id: str
    anchor: Anchor
    severity: CommentSeverity
    body: str
    images: list[Path]
    turns: list[Turn]
    raised_by: TurnAuthor
    resolved: WireBool

    # Said from the anchor each time it is asked, never kept beside it: a thread
    # cannot say one place and hang on another, wherever it was built — by
    # itself, or inside a question or a panel message
    @computed_field
    @property
    def where(self) -> str:
        """The place, in plain words, for whoever reads the thread as text."""
        return place_in_words(anchor_in_the_review(self.anchor))


class SaysSomething(WireModel):
    """Something said: words, screenshots, or both — but never neither."""

    body: str = Field(max_length=MAX_TEXT_LENGTH)
    images: ImageIds = Field(default_factory=list)

    @model_validator(mode="after")
    def says_something(self) -> Self:
        """A screenshot can be the whole of what is said, but something has to be."""
        if says_nothing(self.body) and not self.images:
            msg = "needs text or an image"
            raise ValueError(msg)
        return self


class TurnInput(SaysSomething):
    """One turn of a thread, as the browser sends it back."""

    # The id the browser gave it, which is what a question asked in it names
    turn_id: WireId
    author: TurnAuthor
    round: int = Field(ge=FIRST_ROUND)


class ThreadInput(SaysSomething):
    """A thread as the browser holds it, turns and all.

    The browser holds the threads — they are unsent work — so whatever is
    about one sends it along as it stands right now: a round, a question, a
    panel message, and the hello in which the page says what it holds.
    """

    thread_id: WireId
    anchor: Anchor
    severity: CommentSeverity
    turns: list[TurnInput] = Field(default_factory=list, max_length=MAX_TURNS)
    # Who opened it. Sent back so a thread the author raised is not read as
    # something the reader wrote.
    raised_by: TurnAuthor
    resolved: WireBool

    def in_the_review(self) -> models.ThreadDraft:
        """The thread as the review holds what the page holds."""
        return models.ThreadDraft.model_validate(self, from_attributes=True)


class SubmitRequest(WireModel):
    """Request body for POST /api/submit."""

    threads: list[ThreadInput] = Field(max_length=MAX_THREADS)
    body: str | None = Field(default=None, max_length=MAX_TEXT_LENGTH)
    # Whether this send is the last one. False sends a round and leaves the
    # review open, which only makes sense while something is answering it.
    end: WireBool


class SubmitResponse(WireModel):
    """Response for POST /api/submit."""

    markdown: str
    comment_count: int
    # Which round was just sent: the one written next is the one after it
    round: int
    ended: WireBool


class AskRequest(WireModel):
    """Request body for POST /api/ask — the reader asking in a thread.

    The whole thread goes, as it stands. `question_id` names what is asked:
    the thread's own id for the comment that opened it, or the id of one of
    the reader's turns in it. The browser decides which; the server only
    finds it.
    """

    question_id: WireId
    thread: ThreadInput


# What a hello's threads say the page holds, three ways
HELLO_THREADS_MEANING = (
    "What the page holds, three ways. Null: nothing — a page that does not know them yet — and the"
    " review keeps what it holds. A list: every thread the page holds, which the review holds from then"
    " on in place of the reader's it held — an empty one when the last was deleted. The threads the"
    " agent raised are never taken away by a list that leaves them out: a page with no draft holds none"
    " of them, and reads them from GET /api/threads as it opens."
)


class HelloBase[Threads](WireModel):
    """What a page says on its socket: the round it had reached, and the threads it holds.

    Written once for both of its readings — the browser's, of what it says,
    and the server's, of what it hears — which differ only in how far a
    thread is read: a field the page says is a field the server hears.
    """

    round: int | None = Field(default=None, ge=FIRST_ROUND)
    threads: list[Threads] | None = Field(default=None, max_length=MAX_THREADS, description=HELLO_THREADS_MEANING)


class SessionHello(HelloBase[ThreadInput]):
    """What the browser says on connecting, and whenever its threads change.

    The review on screen is the only side that knows what has been written
    in it — the threads are unsent work — and the only side that survives a
    server restarted mid-review. So it says both, and neither costs anybody
    anything: this never leaves the machine until an agent asks for it.
    """


class ReceivedHello(HelloBase[JsonValue]):
    """A hello as the server first reads it, its threads not yet read one by one.

    `SessionHello` is what the browser says; this is how the server takes
    it. One thread out of bounds must not cost the round and every other
    thread with it, so each is read on its own afterwards (`HeldThreads`).
    """


class HeldThreads(BaseModel):
    """The threads a hello says the page holds, as the server read them: those it can read, and the ids of the rest.

    Never on the wire itself: what the server made of what was.
    """

    model_config = ConfigDict(frozen=True)

    readable: list[ThreadInput]
    # A thread left out still owns its id in the browser, so the server
    # must not hand that id out again
    unreadable_ids: list[str]

    @classmethod
    def read(cls, threads: list[JsonValue]) -> Self:
        """Read each thread on its own, keeping what can be read and the id of what cannot."""
        readable: list[ThreadInput] = []
        unreadable_ids: list[str] = []
        for thread in threads:
            try:
                readable.append(ThreadInput.model_validate(thread))
            except ValidationError:
                if (thread_id := _thread_id_of(thread)) is not None:
                    unreadable_ids.append(thread_id)
        return cls(readable=readable, unreadable_ids=unreadable_ids)


class NamedThread(WireModel):
    """All the server reads of a thread it cannot read whole: the id it goes by."""

    # Held to the rule every id is: one no page or review could have given
    # names no thread, and owns nothing to keep from being handed out
    thread_id: WireId


def _thread_id_of(thread: JsonValue) -> str | None:
    """The id a thread the server cannot read goes by, if it names one a page could have given it."""
    try:
        named = NamedThread.model_validate(thread)
    except ValidationError:
        return None
    return named.thread_id


class ThreadsResponse(WireModel):
    """Response for GET /api/threads — the threads the review holds, for a page that opens with no draft of its own.

    As a page last said them, and the agent's own however a page left them.
    Read once, as the page opens: from then on the page says what it holds.
    """

    threads: list[ThreadInput]


class ThreadSummary(WireModel):
    """A thread in short: enough to choose what to read, and nothing handed over.

    The comment that opened it, whole — a reader of the index shortens it as
    it likes — but no images and no turns: those are what reading the thread
    in full is for, and handing out an image's path is what keeps it from
    being taken off a comment nobody has sent yet.
    """

    thread_id: str
    where: str
    severity: CommentSeverity
    body: str
    raised_by: TurnAuthor
    resolved: WireBool
    outdated: WireBool
    turn_count: int

    @classmethod
    def of_draft(cls, thread: models.ThreadDraft) -> Self:
        """The summary of a thread as the page holds it."""
        return cls(
            thread_id=thread.thread_id,
            where=place_in_words(thread.anchor),
            severity=thread.severity,
            body=thread.body,
            raised_by=thread.raised_by,
            resolved=thread.resolved,
            outdated=thread.anchor.outdated,
            turn_count=len(thread.turns),
        )

    @classmethod
    def of_thread(cls, thread: Thread) -> Self:
        """The summary of a thread as the agent was handed it."""
        return cls(
            thread_id=thread.thread_id,
            where=thread.where,
            severity=thread.severity,
            body=thread.body,
            raised_by=thread.raised_by,
            resolved=thread.resolved,
            outdated=thread.anchor.outdated,
            turn_count=len(thread.turns),
        )


class PointRequest(WireModel):
    """Request body for POST /api/point — the author raising a thread.

    The same anchor a reader's comment carries, because it becomes exactly
    that: a thread on a line, which the reader answers, settles or removes.
    """

    anchor: Anchor
    body: AgentText
    severity: CommentSeverity


class PointResponse(WireModel):
    """Response for POST /api/point — which thread was raised."""

    thread_id: str


class FollowRequest(WireModel):
    """Request body for POST /api/anchors/follow — where these are now.

    The browser holds the threads, and the server holds the diff they hang
    on: after a round the browser sends what its threads hang on, and gets
    each one back moved onto the diff as it now stands, in the same order.
    """

    anchors: list[Anchor] = Field(max_length=MAX_THREADS)


class FollowResponse(WireModel):
    """Response for POST /api/anchors/follow, one anchor per one asked about."""

    anchors: list[Anchor]
