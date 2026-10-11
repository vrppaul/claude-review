"""Domain models for claude-review."""

from enum import StrEnum, auto
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError, model_validator

from claude_review.domain.exceptions import QuestionNotInThreadError


class ReviewMode(StrEnum):
    """What kind of content is being reviewed.

    DIFF  — git changes (the default): two-column line numbers, add/delete styling.
    FILES — plain text files (plans, docs): single line numbers, no diff decoration.
    TRANSCRIPT — conversation messages: each message is a reviewable block.
    """

    DIFF = auto()
    FILES = auto()
    TRANSCRIPT = auto()


class LineType(StrEnum):
    """Type of a diff line."""

    CONTEXT = auto()
    ADD = auto()
    DELETE = auto()


class LineSide(StrEnum):
    """Which version of the file a line belongs to.

    OLD — the version before the change; such a line no longer exists in the
    working tree, so its number only makes sense against the original file.
    NEW — the version after the change. Files and transcript modes have no
    "before", so every line there is NEW.
    """

    OLD = auto()
    NEW = auto()


class FileStatus(StrEnum):
    """Status of a file in the diff."""

    MODIFIED = auto()
    ADDED = auto()
    DELETED = auto()
    RENAMED = auto()


class DiffLine(BaseModel):
    """A single line in a diff hunk."""

    kind: LineType
    old_number: int | None = None
    new_number: int | None = None
    content: str


class DiffHunk(BaseModel):
    """A contiguous block of changes in a file."""

    header: str
    # The number of each side's first line in the hunk. A side with no lines
    # in it starts where its first line would be: the line after the one
    # before the hunk, the first for a file with none.
    old_start: int
    new_start: int
    lines: list[DiffLine]


class DiffFile(BaseModel):
    """A file that has been changed.

    A file can change without producing hunks: binary content has no lines to
    show, and a permission change touches no line at all. The extra fields let
    the UI say which of those happened instead of showing an empty panel.
    """

    path: str
    # Where the file was before it moved; None unless it was renamed
    old_path: str | None = None
    status: FileStatus
    hunks: list[DiffHunk]
    is_binary: bool = False
    # The file's mode before and after, when it changed: its permissions, or
    # its type, as when a file became a link (git's mode 120000)
    old_mode: str | None = None
    new_mode: str | None = None

    @property
    def commentable(self) -> bool:
        """Whether a thread may hang on the file: whether its path is one a thread may name.

        Git hands out names no thread can carry — a tab, a newline, an escape
        in them — and such a file is still shown, but only to be read: one
        thread on it would have its whole round refused.
        """
        try:
            FILE_PATHS.validate_python(self.path)
        except ValidationError:
            return False
        return True


class CommentSeverity(StrEnum):
    """How the reader means a comment to be taken.

    NOTE — an observation; act on it if you agree.
    QUESTION — asking, not asserting; answer before changing anything.
    BLOCKER — this has to change before the work is done.
    """

    NOTE = auto()
    QUESTION = auto()
    BLOCKER = auto()


class TurnAuthor(StrEnum):
    """Who wrote a turn in a thread.

    READER — the person reviewing.
    AUTHOR — whoever wrote the change and answers for it.
    """

    READER = auto()
    AUTHOR = auto()


class AnchorKind(StrEnum):
    """What a thread can hang on.

    LINE — lines of one side of a file in the review's own diff.
    """

    LINE = auto()


# What a file path a thread may name, or the agent may say, holds: no control
# character. A newline in one would let a filename write its own heading in
# the review — a whole fabricated section, blocker and all, in what the agent
# reads — and a tab or an escape has no place in a heading or a chip either.
# Git quotes such names and the parser faithfully decodes them, so the diff
# still shows such a file; it only takes no thread (`DiffFile.commentable`).
SAFE_PATH = r"^[^\x00-\x1f\x7f]+$"

# The longest path a file system here hands out
MAX_PATH_LENGTH = 4096

# A file as the review names it: one line, never markup
FilePath = Annotated[str, Field(min_length=1, max_length=MAX_PATH_LENGTH, pattern=SAFE_PATH)]

# The rule a file path is held to, for a path the review is handed rather than sent
FILE_PATHS: TypeAdapter[FilePath] = TypeAdapter(FilePath)

# A moment, in milliseconds since the epoch: the one unit the review says
# every time in, so the browser reads them all the same way
EpochMillis = Annotated[int, Field(ge=0)]

# The most lines an anchor keeps of what it was written against
MAX_QUOTE_LINES = 200

# The largest file whose lines the diff shows. Nobody reads a longer one line
# by line — it is a log, a bundle, a dump — and one 50 MB log, read whole,
# took a review half a minute and more than a gigabyte to show. A lock file is
# well under it, and its few changed lines still show.
LARGEST_FILE_SHOWN_BYTES = 4 * 1024 * 1024


class AnchorBase(BaseModel):
    """What every kind of anchor has, whatever it hangs on.

    Where it hangs goes stale as the work moves things; what it said when it
    was made is what finds its place again, and what says what the thread was
    about once that place is gone.
    """

    quote: list[str] = Field(default_factory=list, max_length=MAX_QUOTE_LINES)
    # What it was made on is gone from what the review now holds
    outdated: bool = False


def check_line_span(start_line: int, end_line: int) -> None:
    """Refuse lines that run backwards, wherever an anchor is read.

    Raises:
        ValueError: if the span ends before it starts.
    """
    if start_line > end_line:
        msg = "start_line must be <= end_line"
        raise ValueError(msg)


class LineAnchor(AnchorBase):
    """Lines of one side of a file in the review's own diff.

    Line numbers are only meaningful together with the side: a hunk that
    replaces a line has both an old line 42 and a new line 42.
    """

    kind: Literal[AnchorKind.LINE] = AnchorKind.LINE
    file: FilePath
    side: LineSide
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)

    @model_validator(mode="after")
    def start_before_end(self) -> Self:
        check_line_span(self.start_line, self.end_line)
        return self


# Everything a thread can hang on, told apart by `kind`; `AnchorService`
# answers for each kind
type Anchor = LineAnchor

# The round every review opens on; rounds are counted from it
FIRST_ROUND = 1


class Turn(BaseModel):
    """One thing said in a thread after the comment that opened it."""

    author: TurnAuthor
    body: str
    round: int = Field(ge=FIRST_ROUND)
    # Screenshots pasted with it, as files whoever answers can open
    images: list[Path]


class Thread(BaseModel):
    """A thread hanging on something the reader reads, and everything said in it.

    The comment that opened it stays in `body`, and everything said
    afterwards is a turn. Keeping the opening apart is not ceremony: it is
    what the anchor, the severity and the whole thread are about, and a
    review with nothing discussed is still only bodies.

    It carries the quoted lines as well as what was said, because the agent
    that answers may be reading it without the file in front of it.
    """

    thread_id: str
    anchor: Anchor
    severity: CommentSeverity
    body: str
    # Screenshots pasted with the comment that opened the thread
    images: list[Path]
    turns: list[Turn]
    # Who opened it. The author may point at a line too — "here I did it
    # differently from what you asked" belongs on the line, not in a
    # paragraph elsewhere. The reader then works with it as with their own,
    # but it is not theirs and is never drawn as if it were.
    raised_by: TurnAuthor
    # Settled, by the reader who opened it. Travels with the review, because
    # an agent reading a settled thread should not act on it again.
    resolved: bool


class SaidInDraft(BaseModel):
    """Something said in a thread the reader's page holds: words, and screenshots by the ids they are kept under."""

    body: str
    images: list[str]


class TurnDraft(SaidInDraft):
    """One turn of a thread, as the reader's page holds it."""

    # The id the page gave it, which is what a question asked in it names
    turn_id: str
    author: TurnAuthor
    round: int = Field(ge=FIRST_ROUND)


class ThreadDraft(SaidInDraft):
    """A thread as the reader's page holds it: unsent work, its screenshots not yet handed to anybody.

    Handed to the agent it becomes a `Thread`, its screenshots files the
    agent may open.
    """

    thread_id: str
    anchor: Anchor
    severity: CommentSeverity
    turns: list[TurnDraft]
    raised_by: TurnAuthor
    resolved: bool

    def part_asked(self, question_id: str) -> SaidInDraft:
        """What a question asks: the comment that opened the thread, or a turn the reader wrote in it.

        Raises:
            QuestionNotInThreadError: if it names neither.
        """
        if question_id == self.thread_id:
            return self
        for turn in self.turns:
            if turn.turn_id == question_id and turn.author == TurnAuthor.READER:
                return turn
        msg = f"{question_id} is not something the reader said in {self.thread_id}"
        raise QuestionNotInThreadError(msg)


class ReviewResult(BaseModel):
    """Formatted review output."""

    markdown: str
    comment_count: int


class ThreadQuestion(BaseModel):
    """Something the reader asked in one thread, with the whole thread around it."""

    # Which question in that thread. A thread can have more than one waiting
    # at a time, and an answer has to say which it belongs to.
    question_id: str
    # What is asked: the reader's last word in the thread, or the comment
    # that opened it
    body: str
    images: list[Path]
    # Everything said in the thread so far, the question included, so an
    # answer to the third question is not written as if it were the first
    thread: Thread


class PanelMessage(BaseModel):
    """Something the reader typed in the agent panel.

    A thread is about one line; this is about everything else — the plan,
    the tests, a file nobody commented on. It may still point at threads,
    and then it carries them, so the agent is not left guessing which lines
    "that one" meant.
    """

    message_id: str
    body: str
    threads: list[Thread]
    # Images the reader pasted, as files the agent can open
    images: list[Path]


class AgentStatus(BaseModel):
    """What the agent has said about itself.

    Nothing here can be measured from this side — the agent lives in another
    process — so every field starts empty and stays empty until it reports.
    A zero would read as a measurement, and it would be a lie.
    """

    model: str | None = None
    context: str | None = None
    # When it last reported, so the panel can say how old the numbers are
    # rather than presenting them as current
    at: EpochMillis | None = None


# The longest one branch of the work may be said in: a line, not a report
MAX_STEP_LENGTH = 200

# One branch of the work, as it is said
StepText = Annotated[str, Field(min_length=1, max_length=MAX_STEP_LENGTH)]


class ProgressStep(BaseModel):
    """One branch of the work: something being done, or something done."""

    text: StepText
    done: bool = False


class AgentWork(BaseModel):
    """What the agent is doing right now, whole: it replaces whatever was showing.

    The review alone decides when it ends — an empty report, the answer to
    the message it was for, that message taken back, or a new panel message
    — and says so, so every review on screen, and every one opened later,
    shows the same. A question in a thread does not end it: the agent may be
    working through a round, and answers the question beside it.
    """

    # Which message the work is for; None for work on the agent's own
    # account — a round being worked through, reviewers still reading
    message_id: str | None
    text: str
    files: list[FilePath]
    steps: list[ProgressStep]
    # When it was reported, so a review reloaded later says how long it has gone on
    at: EpochMillis


class PanelCancel(BaseModel):
    """The reader withdrawing a panel message before it was answered.

    A request, not a kill: it goes onto the same queue as everything else,
    and whoever is working decides what to do about it.
    """

    message_id: str


class PanelEntry(BaseModel):
    """One thing said in the panel, kept so a later agent can catch up.

    The reader's browser remembers the whole conversation across a reload;
    the agent may be a different process by then and remembers nothing. The
    server saw both halves go past, so it is the one that can say what was
    already discussed.
    """

    message_id: str | None = None
    author: TurnAuthor
    body: str
    at: EpochMillis
    # Screenshots the reader pasted; the agent says words only
    images: list[Path]


class RoundSubmission(BaseModel):
    """One round of a review, on its way to whoever answers it.

    A round is everything written since the last one was sent. The review
    does not end with it: the agent answers, changes what it changed, and
    the diff is retaken under the same threads.
    """

    number: int = Field(ge=FIRST_ROUND)
    markdown: str
    comment_count: int


# Everything the reader hands over for the agent to pick up, in one queue so
# they are answered in the order they were sent
type AgentEvent = ThreadQuestion | RoundSubmission | PanelMessage | PanelCancel


class ChangedSinceRound(BaseModel):
    """Which files changed since a round began, so they are read again rather than all of them."""

    model_config = ConfigDict(frozen=True)

    round: int = Field(ge=FIRST_ROUND)
    paths: list[str]


class PathState(BaseModel):
    """One path where the working tree differs from HEAD, as the disk has it now.

    Git says only that a path differs, and that stays true through every
    later edit of it; its size and modification time say when its content
    changed again, and whether it may be run when its mode did — which
    changes neither.
    """

    model_config = ConfigDict(frozen=True)

    path: str
    # None when nothing is on the disk at the path: it was deleted
    modified_ns: int | None
    size: int | None
    # Whether its owner may run it: of a file's mode, the one bit git keeps
    executable: bool | None


# The working tree as one taking of the diff left it
type TreeState = frozenset[PathState]


class TreeSnapshot(BaseModel):
    """The working tree as one taking of the diff saw it.

    The work under review is uncommitted, so between two rounds there may be
    no commit at all — nothing to go back to unless a mark is left. Every
    time the diff is taken, the tree it showed is written as a git object
    and remembered here, which is what lets a later round be asked what has
    changed since.
    """

    round: int = Field(ge=FIRST_ROUND)
    tree: str
    at: EpochMillis


class GitRef(BaseModel):
    """A branch or a tag, and when whatever it points at was committed."""

    name: str
    at: EpochMillis


# The ref every repository with a commit has: against it, the uncommitted changes
HEAD = "HEAD"


class ReviewKey(BaseModel):
    """The review's own base: what it was opened against, and the diff it keeps."""

    model_config = ConfigDict(frozen=True)


class RoundKey(BaseModel):
    """The tree one of the review's rounds began at."""

    model_config = ConfigDict(frozen=True)

    round: int = Field(ge=FIRST_ROUND)


class RefKey(BaseModel):
    """A branch or a tag the repository had all along."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1)


# What the working tree can be compared against: the review's own base, a
# round's, or a ref's
type VersionKey = ReviewKey | RoundKey | RefKey


class VersionOnOffer(BaseModel):
    """One base the working tree can be compared against, and what the reader would see against it."""

    model_config = ConfigDict(frozen=True)

    key: VersionKey
    # When it was made: a round when it began, a ref when it was committed
    at: EpochMillis | None
    # How many files differ from it, when git will say
    changed: int | None


class Theme(StrEnum):
    """How the review is coloured: as the system says, or always light or dark."""

    SYSTEM = auto()
    LIGHT = auto()
    DARK = auto()


class DiffLayout(StrEnum):
    """Whether a diff reads down one column or across two."""

    UNIFIED = auto()
    SPLIT = auto()


class ReaderSettings(BaseModel):
    """How this reader reads a review, the same in every review on the machine.

    Each field holds what a reader who has never chosen gets.
    """

    theme: Theme = Theme.SYSTEM
    diff_layout: DiffLayout = DiffLayout.UNIFIED
    # Leave out changes that only alter whitespace
    ignore_whitespace: bool = False
    # A tick when an answer arrives while the review is in a background tab
    sound_on_replies: bool = False


class GuideState(BaseModel):
    """What the review remembers of having shown this reader around."""

    # The release whose news the reader was last shown
    seen_release: str | None = None
