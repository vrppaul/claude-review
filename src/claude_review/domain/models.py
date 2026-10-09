"""Domain models for claude-review."""

from enum import StrEnum, auto
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator


class ReviewModel(BaseModel):
    """A model that crosses the wire: written out, it carries every field.

    A field with a default may be left out by whoever sends one, but the
    review always writes it, so the schema of what it writes says so — and
    the browser's types, generated from that schema, do not call such a
    field maybe missing. Models that never leave the server are plain.
    """

    model_config = ConfigDict(json_schema_serialization_defaults_required=True)


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


class DiffLine(ReviewModel):
    """A single line in a diff hunk."""

    type: LineType
    old_no: int | None = None
    new_no: int | None = None
    content: str


class DiffHunk(ReviewModel):
    """A contiguous block of changes in a file."""

    header: str
    old_start: int
    new_start: int
    lines: list[DiffLine]


class DiffFile(ReviewModel):
    """A file that has been changed.

    A file can change without producing hunks: binary content has no lines to
    show, and a permission change touches no line at all. The extra fields let
    the UI say which of those happened instead of showing an empty panel.
    """

    path: str
    status: FileStatus
    hunks: list[DiffHunk]
    is_binary: bool = False
    old_mode: str | None = None
    new_mode: str | None = None


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


# What a file path may hold. A newline in one would let a filename write its
# own heading in the review — a whole fabricated section, blocker and all, in
# what the agent reads. Git quotes such names, and the parser faithfully
# decodes them.
SAFE_PATH = r"^[^\x00-\x1f\x7f]+$"

# The longest path a file system here hands out
MAX_PATH_LENGTH = 4096

# A file as the review names it: one line, never markup
FilePath = Annotated[str, Field(min_length=1, max_length=MAX_PATH_LENGTH, pattern=SAFE_PATH)]

# A moment, in milliseconds since the epoch: the one unit the review says
# every time in, so the browser reads them all the same way
EpochMillis = Annotated[int, Field(ge=0)]

# The most lines an anchor keeps of what it was written against
MAX_QUOTE_LINES = 200


class AnchorBase(ReviewModel):
    """What every kind of anchor has, whatever it hangs on.

    Where it hangs goes stale as the work moves things; what it said when it
    was made is what finds its place again, and what says what the thread was
    about once that place is gone.
    """

    quote: list[str] = Field(default_factory=list, max_length=MAX_QUOTE_LINES)
    # What it was made on is gone from what the review now holds
    outdated: bool = False


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
        if self.start_line > self.end_line:
            msg = "start_line must be <= end_line"
            raise ValueError(msg)
        return self

    def where(self) -> str:
        """The place as the review writes it: "`a.py`:42-47", or "… (removed)".

        A removed line exists only in the file as it was, so its number is
        said to belong there, or it would be read against the current file.
        """
        removed = " (removed)" if self.side == LineSide.OLD else ""
        span = str(self.start_line) if self.start_line == self.end_line else f"{self.start_line}-{self.end_line}"
        return f"`{self.file}`:{span}{removed}"


# Everything a thread can hang on, told apart by `kind`; `AnchorService`
# answers for each kind
type Anchor = LineAnchor


class Turn(ReviewModel):
    """One thing said in a thread after the comment that opened it."""

    author: TurnAuthor
    body: str
    round: int = 1
    # Screenshots pasted with it, as files whoever answers can open
    images: list[Path] = []


class Thread(ReviewModel):
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
    images: list[Path] = []
    turns: list[Turn] = []
    # Who opened it. The author may point at a line too — "here I did it
    # differently from what you asked" belongs on the line, not in a
    # paragraph elsewhere. The reader then works with it as with their own,
    # but it is not theirs and is never drawn as if it were.
    raised_by: TurnAuthor
    # Settled, by the reader who opened it. Travels with the review, because
    # an agent reading a settled thread should not act on it again.
    resolved: bool

    @computed_field
    @property
    def where(self) -> str:
        """The place, named the way the review names it everywhere it is told."""
        return self.anchor.where()


class ReviewResult(BaseModel):
    """Formatted review output."""

    markdown: str
    comment_count: int


class ThreadQuestion(ReviewModel):
    """Something the reader asked in one thread, with the whole thread around it."""

    # Which question in that thread. A thread can have more than one waiting
    # at a time, and an answer has to say which it belongs to.
    question_id: str
    # What is asked: the reader's last word in the thread, or the comment
    # that opened it
    body: str
    images: list[Path] = []
    # Everything said in the thread so far, the question included, so an
    # answer to the third question is not written as if it were the first
    thread: Thread


class PanelMessage(ReviewModel):
    """Something the reader typed in the agent panel.

    A thread is about one line; this is about everything else — the plan,
    the tests, a file nobody commented on. It may still point at threads,
    and then it carries them, so the agent is not left guessing which lines
    "that one" meant.
    """

    message_id: str
    body: str
    threads: list[Thread] = []
    # Images the reader pasted, as files the agent can open
    images: list[Path] = []


class AgentStatus(ReviewModel):
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


class PanelCancel(ReviewModel):
    """The reader withdrawing a panel message before it was answered.

    A request, not a kill: it goes onto the same queue as everything else,
    and whoever is working decides what to do about it.
    """

    message_id: str


class PanelEntry(ReviewModel):
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
    images: list[Path] = []


class RoundSubmission(ReviewModel):
    """One round of a review, on its way to whoever answers it.

    A round is everything written since the last one was sent. The review
    does not end with it: the agent answers, changes what it changed, and
    the diff is retaken under the same threads.
    """

    number: int
    markdown: str
    comment_count: int


# Everything the reader hands over for the agent to pick up, in one queue so
# they are answered in the order they were sent
type AgentEvent = ThreadQuestion | RoundSubmission | PanelMessage | PanelCancel


class ChangesSince(ReviewModel):
    """Which files changed since a round began, so they are read again rather than all of them."""

    since_round: int
    paths: list[str]


class PathState(BaseModel):
    """One path where the working tree differs from HEAD, as the disk has it now.

    Git says only that a path differs, and that stays true through every
    later edit of it; its size and modification time say when its content
    changed again.
    """

    model_config = ConfigDict(frozen=True)

    path: str
    # None when nothing is on the disk at the path: it was deleted
    modified_ns: int | None
    size: int | None


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

    round: int
    tree: str
    at: EpochMillis


class GitRef(BaseModel):
    """A branch or a tag, and when whatever it points at was committed."""

    name: str
    at: EpochMillis


class VersionKind(StrEnum):
    """Where a base came from, so a menu can group them.

    Three answers to one question — what is the working tree being compared
    against: what the review opened with, a tree one of its rounds was read
    at, or a ref that was there all along.
    """

    REVIEW = auto()
    ROUND = auto()
    REF = auto()


class ReviewVersion(ReviewModel):
    """One base the working tree can be compared against.

    Two names for it: `label` is what a menu row calls it, `phrase` what the
    header says while it is the one in force. Both are written here rather
    than assembled in the browser, because "uncommitted changes" is not
    "changes since" anything.
    """

    key: str
    kind: VersionKind
    label: str
    phrase: str
    at: EpochMillis | None = None
    changed: int | None = None


class ReviewWorkspace(BaseModel):
    """Where a review writes, so nothing of it lands in the repository under review."""

    # Where the trees written down at every take of the diff are kept. None
    # in a review whose content did not come from a repository: it leaves no
    # marks, and so cannot offer its own rounds as bases.
    objects: Path | None
    # Where the images the reader pastes into the panel are kept
    images: Path


class Theme(StrEnum):
    """How the review is coloured: as the system says, or always light or dark."""

    SYSTEM = auto()
    LIGHT = auto()
    DARK = auto()


class DiffLayout(StrEnum):
    """Whether a diff reads down one column or across two."""

    UNIFIED = auto()
    SPLIT = auto()


class ReaderSettings(ReviewModel):
    """How this reader reads a review, the same in every review on the machine.

    Each field holds what a reader who has never chosen gets.
    """

    theme: Theme = Theme.SYSTEM
    diff_layout: DiffLayout = DiffLayout.UNIFIED
    # Leave out changes that only alter whitespace
    ignore_whitespace: bool = False
    # A tick when an answer arrives while the review is in a background tab
    sound_on_replies: bool = False


class GuideState(ReviewModel):
    """What the review remembers of having shown this reader around."""

    # The release whose news the reader was last shown
    seen_release: str | None = None


class ReaderFiles(BaseModel):
    """Where what a review remembers about its reader is kept, for every review.

    Two files for two kinds of thing: what the reader chose, kept with their
    configuration, and what the review noticed, kept with other programs'
    state. Configuration is often kept in git, where a release number
    changing with every upgrade would be noise.
    """

    settings: Path
    guide: Path


class StoredImage(BaseModel):
    """An image the reader pasted, written into the review's workspace."""

    image_id: str
    path: Path
    media_type: str
    size: int


class ImageLedger(BaseModel):
    """What one review keeps of the images pasted into it.

    Held beside the rest of the review's state rather than read back off the
    disk: the ledger is what says an id exists, so no path is ever built from
    one, and the running total is what keeps the review under its limit
    without counting the directory on every upload.
    """

    kept: dict[str, StoredImage] = {}
    # Images that went out with a message. The agent may still be about to
    # open them, so they stay until the review ends.
    sent: set[str] = set()
    held_bytes: int = 0
