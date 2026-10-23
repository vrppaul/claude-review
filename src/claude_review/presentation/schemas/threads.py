"""The API's threads: what they hang on, what the page sends of them, and what the agent is handed."""

from pathlib import Path
from typing import Annotated, Literal, Self, assert_never

from pydantic import (
    Field,
    JsonValue,
    StrictBool,
    StrictInt,
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
from claude_review.presentation.schemas.base import (
    MAX_TEXT_LENGTH,
    MAX_THREADS,
    AgentText,
    ImageIds,
    SafeId,
    Schema,
)
from claude_review.services.place_words import place_in_words

# The most turns one thread carries
MAX_TURNS = 200

# The longest line an anchor may quote. It quotes a line of the diff, which
# shows the lines of no file larger than this many bytes, and a character
# takes at least one
MAX_QUOTE_LINE_LENGTH = LARGEST_FILE_SHOWN_BYTES
# One line an anchor quotes, as the page sends it
QuoteLine = Annotated[str, Field(max_length=MAX_QUOTE_LINE_LENGTH)]


class LineAnchor(Schema):
    """Lines of one side of a file in the review's own diff, as the page names them: where, and what they said.

    A quote sent empty is filled in by the review from its diff.
    """

    kind: Literal[AnchorKind.LINE] = AnchorKind.LINE
    file: FilePath
    side: LineSide
    start_line: StrictInt = Field(ge=FIRST_LINE)
    end_line: StrictInt = Field(ge=FIRST_LINE)
    quote: list[QuoteLine] = Field(max_length=MAX_QUOTE_LINES)
    outdated: StrictBool

    @model_validator(mode="after")
    def start_before_end(self) -> Self:
        models.check_line_span(self.start_line, self.end_line)
        return self

    @classmethod
    def from_domain(cls, anchor: models.LineAnchor) -> Self:
        return cls(
            kind=anchor.kind,
            file=anchor.file,
            side=anchor.side,
            start_line=anchor.start_line,
            end_line=anchor.end_line,
            quote=anchor.quote,
            outdated=anchor.outdated,
        )

    def to_domain(self) -> models.LineAnchor:
        return models.LineAnchor(
            kind=self.kind,
            file=self.file,
            side=self.side,
            start_line=self.start_line,
            end_line=self.end_line,
            quote=self.quote,
            outdated=self.outdated,
        )


class PointedLines(Schema):
    """Lines of one side of a file in the review's own diff, as the agent points at them: where, and no more.

    The review quotes them itself, from its diff, as it raises the thread.
    """

    file: FilePath
    side: LineSide
    start_line: StrictInt = Field(ge=FIRST_LINE)
    end_line: StrictInt = Field(ge=FIRST_LINE)

    @model_validator(mode="after")
    def start_before_end(self) -> Self:
        models.check_line_span(self.start_line, self.end_line)
        return self

    def to_domain(self) -> models.LineAnchor:
        # Not quoted yet, and so not out of date: the review quotes it from the diff on screen
        return models.LineAnchor(
            kind=AnchorKind.LINE,
            file=self.file,
            side=self.side,
            start_line=self.start_line,
            end_line=self.end_line,
            quote=[],
            outdated=False,
        )


class OverviewBlock(Schema):
    """One of the overview's three lines, by its name."""

    at: Literal[StoryBlockKind.OVERVIEW] = StoryBlockKind.OVERVIEW
    text: OverviewText

    @classmethod
    def from_domain(cls, block: models.OverviewBlock) -> Self:
        return cls(at=block.at, text=block.text)

    def to_domain(self) -> models.OverviewBlock:
        return models.OverviewBlock(at=self.at, text=self.text)


class ItemBlock(Schema):
    """One thing a list of the overview holds, by where it stands in the list, counted from 0."""

    at: Literal[StoryBlockKind.ITEM] = StoryBlockKind.ITEM
    list: OverviewList
    item: StrictInt = Field(ge=FIRST_ITEM)

    @classmethod
    def from_domain(cls, block: models.ItemBlock) -> Self:
        return cls(at=block.at, list=block.list, item=block.item)

    def to_domain(self) -> models.ItemBlock:
        return models.ItemBlock(at=self.at, list=self.list, item=self.item)


class ChapterBlock(Schema):
    """What a chapter says of itself, the chapter by its id."""

    at: Literal[StoryBlockKind.CHAPTER] = StoryBlockKind.CHAPTER
    chapter: ChapterId
    text: ChapterText

    @classmethod
    def from_domain(cls, block: models.ChapterBlock) -> Self:
        return cls(at=block.at, chapter=block.chapter, text=block.text)

    def to_domain(self) -> models.ChapterBlock:
        return models.ChapterBlock(at=self.at, chapter=self.chapter, text=self.text)


class ReasonBlock(Schema):
    """A step's reason, the step by its file and the first line it tells."""

    at: Literal[StoryBlockKind.REASON] = StoryBlockKind.REASON
    file: FilePath
    first_line: StrictInt = Field(ge=FIRST_LINE)

    @classmethod
    def from_domain(cls, block: models.ReasonBlock) -> Self:
        return cls(at=block.at, file=block.file, first_line=block.first_line)

    def to_domain(self) -> models.ReasonBlock:
        return models.ReasonBlock(at=self.at, file=self.file, first_line=self.first_line)


# A block of the story's words, as the API carries it
type StoryBlock = Annotated[OverviewBlock | ItemBlock | ChapterBlock | ReasonBlock, Field(discriminator="at")]


def _block_from_domain(block: models.StoryBlock) -> StoryBlock:
    """The schema of a block of the story's words, whichever it is."""
    match block:
        case models.OverviewBlock():
            return OverviewBlock.from_domain(block)
        case models.ItemBlock():
            return ItemBlock.from_domain(block)
        case models.ChapterBlock():
            return ChapterBlock.from_domain(block)
        case models.ReasonBlock():
            return ReasonBlock.from_domain(block)
        case _:
            assert_never(block)


# The words of a block a story anchor quotes: a text of the story, bounded as anything said in a review is
QuotedWords = Annotated[str, Field(max_length=MAX_TEXT_LENGTH)]


class StoryAnchor(Schema):
    """A block of the words of the story told of the change, as the page names it.

    A quote sent empty is filled in by the review from the story it holds.
    """

    kind: Literal[AnchorKind.STORY] = AnchorKind.STORY
    block: StoryBlock
    quote: list[QuotedWords] = Field(max_length=STORY_QUOTE_TEXTS)
    outdated: StrictBool

    @classmethod
    def from_domain(cls, anchor: models.StoryAnchor) -> Self:
        return cls(
            kind=anchor.kind, block=_block_from_domain(anchor.block), quote=anchor.quote, outdated=anchor.outdated
        )

    def to_domain(self) -> models.StoryAnchor:
        return models.StoryAnchor(
            kind=self.kind, block=self.block.to_domain(), quote=self.quote, outdated=self.outdated
        )


# Everything a thread can hang on, as the API carries it
type Anchor = Annotated[LineAnchor | StoryAnchor, Field(discriminator="kind")]


def anchor_from_domain(anchor: models.Anchor) -> Anchor:
    """The schema of one of the domain's anchors, whatever its kind."""
    match anchor:
        case models.LineAnchor():
            return LineAnchor.from_domain(anchor)
        case models.StoryAnchor():
            return StoryAnchor.from_domain(anchor)
        case _:
            assert_never(anchor)


class Turn(Schema):
    """One thing said in a thread after the comment that opened it, its screenshots as files to open."""

    author: TurnAuthor
    body: str
    round: int
    images: list[Path]

    @classmethod
    def from_domain(cls, turn: models.Turn) -> Self:
        return cls(author=turn.author, body=turn.body, round=turn.round, images=turn.images)


class Thread(Schema):
    """A thread as the agent is handed it: where it is, everything said in it, its screenshots as files."""

    thread_id: str
    anchor: Anchor
    severity: CommentSeverity
    body: str
    images: list[Path]
    turns: list[Turn]
    raised_by: TurnAuthor
    resolved: StrictBool

    @classmethod
    def from_domain(cls, thread: models.Thread) -> Self:
        return cls(
            thread_id=thread.thread_id,
            anchor=anchor_from_domain(thread.anchor),
            severity=thread.severity,
            body=thread.body,
            images=thread.images,
            turns=[Turn.from_domain(turn) for turn in thread.turns],
            raised_by=thread.raised_by,
            resolved=thread.resolved,
        )

    # Said from the anchor each time it is asked, never kept beside it: a thread
    # cannot say one place and hang on another, wherever it was built — by
    # itself, or inside a question or a panel message
    @computed_field
    @property
    def where(self) -> str:
        """The place, in plain words, for whoever reads the thread as text."""
        return place_in_words(self.anchor.to_domain())


class SaysSomething(Schema):
    """Something said: words, screenshots, or both — but never neither."""

    body: str = Field(max_length=MAX_TEXT_LENGTH)
    images: ImageIds

    @model_validator(mode="after")
    def says_something(self) -> Self:
        """A screenshot can be the whole of what is said, but something has to be."""
        if says_nothing(self.body) and not self.images:
            msg = "needs text or an image"
            raise ValueError(msg)
        return self


class TurnDraft(SaysSomething):
    """One turn of a thread the page holds, its screenshots by their ids."""

    # The id the browser gave it, which is what a question asked in it names
    turn_id: SafeId
    author: TurnAuthor
    round: int = Field(ge=FIRST_ROUND)

    @classmethod
    def from_domain(cls, turn: models.TurnDraft) -> Self:
        return cls(body=turn.body, images=turn.images, turn_id=turn.turn_id, author=turn.author, round=turn.round)

    def to_domain(self) -> models.TurnDraft:
        return models.TurnDraft(
            body=self.body, images=self.images, turn_id=self.turn_id, author=self.author, round=self.round
        )


class SaidAsHanded(Schema):
    """What opened a thread, as the agent has it: who said it, its words, and its screenshots by their ids."""

    author: TurnAuthor
    body: str
    images: list[str]

    @classmethod
    def from_domain(cls, said: models.SaidAsHanded) -> Self:
        return cls(author=said.author, body=said.body, images=said.images)


class ThreadAsHanded(Schema):
    """What the agent has of a thread: how it was meant, what opened it, and each turn it was handed, in order.

    The page takes these words in place of its own: the agent may have been
    handed a copy older than the page's, and what it has the reader rewrites
    no more. What the page holds and the agent does not goes with the next
    round: a word said since, or the thread settled or opened again since.
    """

    severity: CommentSeverity
    opening: SaidAsHanded
    turns: list[TurnDraft]
    # The round the agent first had the thread in, which the page says it went in
    round: int = Field(ge=FIRST_ROUND)
    # Whether the thread was settled when the agent was last handed it
    resolved: StrictBool

    @classmethod
    def from_domain(cls, has: models.ThreadAsHanded) -> Self:
        return cls(
            severity=has.severity,
            opening=SaidAsHanded.from_domain(has.opening),
            turns=[TurnDraft.from_domain(turn) for turn in has.turns],
            round=has.round,
            resolved=has.resolved,
        )


class ThreadDraft(SaysSomething):
    """A thread as the page holds it, turns and all: the same both ways.

    The page holds the threads — they are unsent work — so whatever is
    about one sends it along as it stands right now: a round, a question, a
    panel message, and the hello in which the page says what it holds. The
    review keeps what the page said, and hands it back to a page that opens
    with no draft of its own.
    """

    thread_id: SafeId
    anchor: Anchor
    severity: CommentSeverity
    turns: list[TurnDraft] = Field(max_length=MAX_TURNS)
    # Who opened it. Sent back so a thread the author raised is not read as
    # something the reader wrote.
    raised_by: TurnAuthor
    resolved: StrictBool

    @classmethod
    def from_domain(cls, thread: models.ThreadDraft) -> Self:
        return cls(
            body=thread.body,
            images=thread.images,
            thread_id=thread.thread_id,
            anchor=anchor_from_domain(thread.anchor),
            severity=thread.severity,
            turns=[TurnDraft.from_domain(turn) for turn in thread.turns],
            raised_by=thread.raised_by,
            resolved=thread.resolved,
        )

    def to_domain(self) -> models.ThreadDraft:
        """The thread as the review holds what the page holds."""
        return models.ThreadDraft(
            body=self.body,
            images=self.images,
            thread_id=self.thread_id,
            anchor=self.anchor.to_domain(),
            severity=self.severity,
            turns=[turn.to_domain() for turn in self.turns],
            raised_by=self.raised_by,
            resolved=self.resolved,
        )


class SubmitRequest(Schema):
    """Request body for POST /api/submit."""

    threads: list[ThreadDraft] = Field(max_length=MAX_THREADS)
    body: str | None = Field(default=None, max_length=MAX_TEXT_LENGTH)
    # Whether this send is the last one. False sends a round and leaves the
    # review open, which only makes sense while something is answering it.
    end: StrictBool


class SubmitResponse(Schema):
    """Response for POST /api/submit."""

    markdown: str
    comment_count: int
    # Which round was just sent: the one written next is the one after it
    round: int
    ended: StrictBool


class AskRequest(Schema):
    """Request body for POST /api/ask — the reader asking in a thread.

    The whole thread goes, as it stands. `question_id` names what is asked:
    the thread's own id for the comment that opened it, or the id of one of
    the reader's turns in it. The browser decides which; the server only
    finds it.
    """

    question_id: SafeId
    thread: ThreadDraft


# What a hello's threads say the page holds, three ways
HELLO_THREADS_MEANING = (
    "What the page holds, three ways. Null: nothing — a page that does not know them yet — and the"
    " review keeps what it holds. A list: every thread the page holds, which the review holds from then"
    " on in place of the reader's it held — an empty one when the last was deleted. The threads the"
    " agent raised are never taken away by a list that leaves them out: a page with no draft holds none"
    " of them, and reads them from GET /api/threads as it opens."
)


class HelloBase[Threads](Schema):
    """What a page says on its socket: the round it had reached, and the threads it holds.

    Written once for both of its readings — the browser's, of what it says,
    and the server's, of what it hears — which differ only in how far a
    thread is read: a field the page says is a field the server hears.
    """

    round: int | None = Field(default=None, ge=FIRST_ROUND)
    threads: list[Threads] | None = Field(default=None, max_length=MAX_THREADS, description=HELLO_THREADS_MEANING)


class SessionHello(HelloBase[ThreadDraft]):
    """What the browser says on connecting, and whenever its threads change.

    The review on screen is the only side that knows what has been written
    in it — the threads are unsent work — and keeps the round it reached
    even where a server restarted mid-review lost what it kept. So it says
    both, and neither costs anybody anything: this never leaves the machine
    until an agent asks for it.
    """


class NamedThread(Schema):
    """All the server reads of a thread it cannot read whole: the id it goes by."""

    # Held to the rule every id is: one no page or review could have given
    # names no thread, and owns nothing to keep from being handed out
    thread_id: SafeId


# A hello's thread as the server hears it: whole; by its id alone, when it
# cannot be read whole, since a thread left out still owns its id in the
# browser; or as it came. Every one the page sent is kept, so each counts
# against the hello's bound
type HeardThread = Annotated[ThreadDraft | NamedThread | JsonValue, Field(union_mode="left_to_right")]


class ReceivedHello(HelloBase[HeardThread]):
    """A hello as the server takes it: one thread out of bounds costs neither the round nor any other thread.

    `SessionHello` is what the browser says; this is how the server hears it.
    """


class ThreadsResponse(Schema):
    """Response for GET /api/threads — the threads the review holds, for a page that opens with no draft of its own.

    As a page last said them, and the agent's own however a page left them;
    and what the agent has of each, which the page offers no more to
    rewrite. Read once, as the page opens: from then on the page says what it
    holds, and the pushes what the agent is handed.
    """

    threads: list[ThreadDraft]
    # What the agent has of each thread it raised or was handed, by thread
    handed: dict[str, ThreadAsHanded]


class ThreadSummary(Schema):
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
    resolved: StrictBool
    outdated: StrictBool
    turn_count: int

    @classmethod
    def from_draft(cls, thread: models.ThreadDraft) -> Self:
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
    def from_thread(cls, thread: Thread) -> Self:
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


class PointRequest(Schema):
    """Request body for POST /api/point — the author raising a thread.

    The lines a reader's comment hangs on, because it becomes exactly that:
    a thread on a line, which the reader answers, settles or removes. Lines
    alone: the agent points at no block of the story's words.
    """

    lines: PointedLines
    body: AgentText
    severity: CommentSeverity


class PointResponse(Schema):
    """Response for POST /api/point — which thread was raised."""

    thread_id: str


class FollowRequest(Schema):
    """Request body for POST /api/anchors/follow — where these are now.

    The browser holds the threads, and the server holds the diff they hang
    on: after a round the browser sends what its threads hang on, and gets
    each one back moved onto the diff as it now stands, in the same order.
    """

    anchors: list[Anchor] = Field(max_length=MAX_THREADS)


class FollowResponse(Schema):
    """Response for POST /api/anchors/follow, one anchor per one asked about."""

    anchors: list[Anchor]
