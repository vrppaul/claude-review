"""What the page is served of the review: its facts, its diff, the bases it can be read against, and its limits."""

from enum import StrEnum, auto
from typing import Annotated, Literal, Self, assert_never

from pydantic import Field, StrictBool

from claude_review.domain import models, story
from claude_review.domain.models import (
    LARGEST_FILE_SHOWN_BYTES,
    MAX_QUOTE_LINES,
    CheckoutKind,
    EpochMillis,
    FileStatus,
    LineType,
    ReviewMode,
    Unshown,
)
from claude_review.presentation.schemas.agent import AgentStatus, AgentWork
from claude_review.presentation.schemas.base import MAX_TEXT_LENGTH, Schema
from claude_review.presentation.schemas.feedback import MAX_FEEDBACK_WORDS
from claude_review.services.file_window_service import MAX_WINDOW_LINES, FileWindow
from claude_review.services.image_service import MAX_IMAGE_BYTES, MAX_IMAGES_PER_MESSAGE


class DiffLine(Schema):
    """A single line in a diff hunk, numbered on the side or sides it is on."""

    kind: LineType
    old_number: int | None
    new_number: int | None
    content: str

    @classmethod
    def from_domain(cls, line: models.DiffLine) -> Self:
        return cls(kind=line.kind, old_number=line.old_number, new_number=line.new_number, content=line.content)


# What a hunk's start says on either side: the browser counts the lines hidden above a hunk from it
HUNK_START_MEANING = (
    "The number of this side's first line in the hunk. A side with no lines in it starts where its"
    " first line would be: the line after the one before the hunk, the first for a file with none."
)


class DiffHunk(Schema):
    """A contiguous block of changes in a file."""

    header: str
    old_start: int = Field(description=HUNK_START_MEANING)
    new_start: int = Field(description=HUNK_START_MEANING)
    lines: list[DiffLine]

    @classmethod
    def from_domain(cls, hunk: models.DiffHunk) -> Self:
        return cls(
            header=hunk.header,
            old_start=hunk.old_start,
            new_start=hunk.new_start,
            lines=[DiffLine.from_domain(line) for line in hunk.lines],
        )


class DiffFile(Schema):
    """A file that has been changed, and what kind of change it was when it has no lines to show."""

    path: str
    # Where the file was before it moved; null unless it was renamed
    old_path: str | None
    status: FileStatus
    hunks: list[DiffHunk]
    # Why none of its lines are shown though its content changed; null when they are
    unshown: Unshown | None
    old_mode: str | None
    new_mode: str | None
    # Whether a thread may name it: a path holding a control character is shown, but only to be read
    commentable: StrictBool

    @classmethod
    def from_domain(cls, file: models.DiffFile) -> Self:
        return cls(
            path=file.path,
            old_path=file.old_path,
            status=file.status,
            hunks=[DiffHunk.from_domain(hunk) for hunk in file.hunks],
            unshown=file.unshown,
            old_mode=file.old_mode,
            new_mode=file.new_mode,
            commentable=file.commentable,
        )


class SendLimits(Schema):
    """The limits the browser checks before it sends: an image, the lines a comment covers, a read of a file, a text.

    Told by the server rather than repeated in the browser, so the two
    cannot drift apart — and a comment the server would refuse is never
    written in the first place. The largest file shown line by line goes
    with them, for the page to name when it shows a file without its lines.
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
    # The longest the reader's feedback on the review itself may be: less than a text, so the agent can be handed it
    max_feedback_length: int
    # The largest file whose lines the diff shows, in bytes
    largest_file_shown_bytes: int


# What this review holds every page to
SEND_LIMITS = SendLimits(
    max_image_bytes=MAX_IMAGE_BYTES,
    max_images_per_message=MAX_IMAGES_PER_MESSAGE,
    max_quoted_lines=MAX_QUOTE_LINES,
    max_window_lines=MAX_WINDOW_LINES,
    max_text_length=MAX_TEXT_LENGTH,
    max_feedback_length=MAX_FEEDBACK_WORDS,
    largest_file_shown_bytes=LARGEST_FILE_SHOWN_BYTES,
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


class ReviewVersion(Schema):
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


class ChangesSince(Schema):
    """Which files changed since a round began, so they are read again rather than all of them."""

    since_round: int
    # The key that shows only what changed since that round
    base_key: str
    paths: list[str]


class StoryAsking(Schema):
    """The reader asking the agent for a story, and how far that has got."""

    asked_at: EpochMillis
    # When an agent took the request; None while none has
    taken_at: EpochMillis | None
    # Whether the reader stopped it
    stopped: StrictBool

    @classmethod
    def from_domain(cls, asking: story.StoryAsking) -> Self:
        return cls(asked_at=asking.asked_at, taken_at=asking.taken_at, stopped=asking.stopped)


class OnBranch(Schema):
    """A branch checked out, by its name: the branch the change is made on."""

    at: Literal[CheckoutKind.BRANCH] = CheckoutKind.BRANCH
    branch: str

    @classmethod
    def from_domain(cls, checkout: models.OnBranch) -> Self:
        return cls(at=checkout.at, branch=checkout.branch)


class OnCommit(Schema):
    """A commit checked out on no branch, by its id as short as git writes it and still names it alone."""

    at: Literal[CheckoutKind.COMMIT] = CheckoutKind.COMMIT
    commit: str

    @classmethod
    def from_domain(cls, checkout: models.OnCommit) -> Self:
        return cls(at=checkout.at, commit=checkout.commit)


# What a working tree has checked out, told apart by `at`
type Checkout = Annotated[OnBranch | OnCommit, Field(discriminator="at")]


def _checkout_from_domain(checkout: models.Checkout) -> Checkout:
    """The schema of what a working tree has checked out, whichever it is."""
    match checkout:
        case models.OnBranch():
            return OnBranch.from_domain(checkout)
        case models.OnCommit():
            return OnCommit.from_domain(checkout)
        case _:
            assert_never(checkout)


class RepositoryAt(Schema):
    """Where the change under review is: the repository, by its name, and what its working tree had checked out."""

    name: str
    checkout: Checkout

    @classmethod
    def from_domain(cls, repository: models.RepositoryAt) -> Self:
        return cls(name=repository.name, checkout=_checkout_from_domain(repository.checkout))


class InRepository(Schema):
    """A review of a change in a repository: where it is, which the header says in place of the tool's name."""

    kind: Literal[ReviewMode.DIFF] = ReviewMode.DIFF
    repository: RepositoryAt

    @classmethod
    def from_domain(cls, where: models.InRepository) -> Self:
        return cls(kind=where.kind, repository=RepositoryAt.from_domain(where.repository))


class OfFiles(Schema):
    """A review of files read once, each whole: in no repository, and called by its title."""

    kind: Literal[ReviewMode.FILES] = ReviewMode.FILES

    @classmethod
    def from_domain(cls, where: models.OfFiles) -> Self:
        return cls(kind=where.kind)


class OfConversation(Schema):
    """A review of a conversation Claude Code kept: in no repository, and called by its title."""

    kind: Literal[ReviewMode.TRANSCRIPT] = ReviewMode.TRANSCRIPT

    @classmethod
    def from_domain(cls, where: models.OfConversation) -> Self:
        return cls(kind=where.kind)


type WhereTheChangeIs = Annotated[InRepository | OfFiles | OfConversation, Field(discriminator="kind")]


def where_from_domain(where: models.WhereTheChangeIs) -> WhereTheChangeIs:
    """The schema of where the change under review is, whichever kind of review it is."""
    match where:
        case models.InRepository():
            return InRepository.from_domain(where)
        case models.OfFiles():
            return OfFiles.from_domain(where)
        case models.OfConversation():
            return OfConversation.from_domain(where)
        case _:
            assert_never(where)


class ReviewResponse(Schema):
    """Response for GET /api/review — what the review is and where it stands, whichever base is on screen.

    Read when a page opens, and again when it comes back from a gap it could
    not be handed: a push is gone once sent, and a page that was not there for
    it learns the state here.
    """

    title: str
    # Where the change is, by the kind of review it is, which the header says
    # in place of the tool's name: a repository's, or files or a conversation
    # read once, said by the title
    where: WhereTheChangeIs
    # What makes it the same review whenever it is opened, as a name that says
    # nothing of what it is made of: the page keeps the reader's unsent work
    # under it, and knows by it a review on this port that is not its own
    identity: str
    # Which round is being written, and whether anything is there to answer it
    round: int
    answerer_attached: StrictBool
    # What the agent last said about itself, and what it says it is doing now
    agent: AgentStatus
    work: AgentWork | None
    # Whether a story can be told of the review, so the page offers one only
    # where it can be, and never asks what kind of review this is to know
    takes_a_story: StrictBool
    # How the reader's asking for a story stands: None while nobody asked for
    # one, and once a story is told. Read here, a page orders it against the
    # pushes that change it, by the sequence below, as it does every fact here
    story_asking: StoryAsking | None
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


class ShownBase(Schema):
    """The base a diff was taken against, as the page shows it.

    `key` is what the page asks for it by, `phrase` what the header says
    while it is in force. `narrowed`: it is narrower than the review's own —
    a round, a ref — so the diff shows less than the threads hang on.
    """

    key: str
    phrase: str
    narrowed: StrictBool


class DiffResponse(Schema):
    """Response for GET /api/diff — the review's content against one base."""

    files: list[DiffFile]
    # None in a review whose content did not come from a repository: it is
    # compared against nothing
    base: ShownBase | None
    # How many files have moved on since this diff was taken. A push says it
    # once; this is how a review that was reloaded, or opened late, finds out.
    moved: int
    # The take the review held as this was read, whatever base it is read
    # against: the one the threads' lines are numbered by, and the one a
    # story must say for its pieces to be numbered so too
    take: int


class VersionsResponse(Schema):
    """Response for GET /api/versions — what the working tree can be read against."""

    versions: list[ReviewVersion]


class RetakeResponse(Schema):
    """Response for POST /api/retake — the diff taken again.

    The files that changed are named, so an agent that has come back to a
    review it left knows which ones to read again rather than all of them.
    None when this review kept no tree to compare against.
    """

    file_count: int
    round: int
    changes: ChangesSince | None


class FileWindowResponse(Schema):
    """Response for GET /api/file-window."""

    start: int
    lines: list[str]
    total: int

    @classmethod
    def from_domain(cls, window: FileWindow) -> Self:
        return cls(start=window.start, lines=window.lines, total=window.total)
