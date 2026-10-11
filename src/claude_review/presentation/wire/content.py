"""What the page is served of the review's content: the diff, the bases it can be read against, and its limits."""

from enum import StrEnum, auto

from pydantic import Field

from claude_review.domain.models import MAX_QUOTE_LINES, EpochMillis, FileStatus, LineType, ReviewMode
from claude_review.presentation.wire.agent import AgentStatus, AgentWork
from claude_review.presentation.wire.base import MAX_TEXT_LENGTH, WireBool, WireModel
from claude_review.services.file_window_service import MAX_WINDOW_LINES
from claude_review.services.image_service import MAX_IMAGE_BYTES, MAX_IMAGES_PER_MESSAGE


class DiffLine(WireModel):
    """A single line in a diff hunk, numbered on the side or sides it is on."""

    kind: LineType
    old_number: int | None
    new_number: int | None
    content: str


# What a hunk's start says on either side: the browser counts the lines hidden above a hunk from it
HUNK_START_MEANING = (
    "The number of this side's first line in the hunk. A side with no lines in it starts where its"
    " first line would be: the line after the one before the hunk, the first for a file with none."
)


class DiffHunk(WireModel):
    """A contiguous block of changes in a file."""

    header: str
    old_start: int = Field(description=HUNK_START_MEANING)
    new_start: int = Field(description=HUNK_START_MEANING)
    lines: list[DiffLine]


class DiffFile(WireModel):
    """A file that has been changed, and what kind of change it was when it has no lines to show."""

    path: str
    # Where the file was before it moved; null unless it was renamed
    old_path: str | None
    status: FileStatus
    hunks: list[DiffHunk]
    is_binary: WireBool
    old_mode: str | None
    new_mode: str | None
    # Whether a thread may name it: a path holding a control character is shown, but only to be read
    commentable: WireBool


class SendLimits(WireModel):
    """The limits the browser checks before it sends: an image, the lines a comment covers, a read of a file, a text.

    Told by the server rather than repeated in the browser, so the two
    cannot drift apart — and a comment the server would refuse is never
    written in the first place.
    """

    max_image_bytes: int
    max_images_per_message: int
    # A comment quotes every line it covers, and the quote is capped
    max_quoted_lines: int
    # The most lines one read of a file hands back: asking for no more, the
    # browser gets back every line it asked for, next to the lines it asked from
    max_window_lines: int
    # The longest anything the reader writes may be: a comment, a reply, a
    # panel message, the summary of a round
    max_text_length: int


# What this review holds every page to
SEND_LIMITS = SendLimits(
    max_image_bytes=MAX_IMAGE_BYTES,
    max_images_per_message=MAX_IMAGES_PER_MESSAGE,
    max_quoted_lines=MAX_QUOTE_LINES,
    max_window_lines=MAX_WINDOW_LINES,
    max_text_length=MAX_TEXT_LENGTH,
)


class VersionKind(StrEnum):
    """Where a base came from, so a menu can group them.

    Three answers to one question — what is the working tree being compared
    against: what the review opened with, a tree one of its rounds was read
    at, or a ref that was there all along.
    """

    REVIEW = auto()
    ROUND = auto()
    REF = auto()


class ReviewVersion(WireModel):
    """One base the working tree can be compared against, as the page's menu shows it.

    `key` is what the page asks for it by; `label` is what a menu row calls
    it, `phrase` what the header says while it is the one in force.
    """

    key: str
    kind: VersionKind
    label: str
    phrase: str
    at: EpochMillis | None
    changed: int | None


class ChangesSince(WireModel):
    """Which files changed since a round began, so they are read again rather than all of them."""

    since_round: int
    # The key that shows only what changed since that round
    base_key: str
    paths: list[str]


class ReviewResponse(WireModel):
    """Response for GET /api/review — what the review is and where it stands, whichever base is on screen.

    Read when a page opens, and again when it comes back from a gap it could
    not be handed: a push is gone once sent, and a page that was not there for
    it learns the state here.
    """

    title: str
    # What makes it the same review whenever it is opened, as a name that says
    # nothing of what it is made of: the page keeps the reader's unsent work
    # under it, and knows by it a review on this port that is not its own
    identity: str
    mode: ReviewMode
    # Which round is being written, and whether anything is there to answer it
    round: int
    answerer_attached: WireBool
    # What the agent last said about itself, and what it says it is doing now
    agent: AgentStatus
    work: AgentWork | None
    # What the browser checks before uploading an image or quoting lines
    limits: SendLimits
    # How far the review's telling had got when this was read, in which run of
    # it: a page reading these facts continues from here on its socket
    instance: str
    sequence: int
    # Which release is serving the review, so the browser can tell a reader
    # what changed since the one they last saw. "Release" rather than
    # "version": a version here is a base the diff is read against.
    release: str


class ShownBase(WireModel):
    """The base a diff was taken against, as the page shows it.

    `key` is what the page asks for it by, `phrase` what the header says
    while it is in force. `narrowed`: it is narrower than the review's own —
    a round, a ref — so the diff shows less than the threads hang on.
    """

    key: str
    phrase: str
    narrowed: WireBool


class DiffResponse(WireModel):
    """Response for GET /api/diff — the review's content against one base."""

    files: list[DiffFile]
    # None in a review whose content did not come from a repository: it is
    # compared against nothing
    base: ShownBase | None
    # How many files have moved on since this diff was taken. A push says it
    # once; this is how a review that was reloaded, or opened late, finds out.
    moved: int


class VersionsResponse(WireModel):
    """Response for GET /api/versions — what the working tree can be read against."""

    versions: list[ReviewVersion]


class RetakeResponse(WireModel):
    """Response for POST /api/retake — the diff taken again.

    The files that changed are named, so an agent that has come back to a
    review it left knows which ones to read again rather than all of them.
    None when this review kept no tree to compare against.
    """

    file_count: int
    round: int
    changes: ChangesSince | None


class FileWindowResponse(WireModel):
    """Response for GET /api/file-window."""

    start: int
    lines: list[str]
    total: int
