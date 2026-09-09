"""Domain models for claude-review."""

from enum import StrEnum, auto

from pydantic import BaseModel


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

    type: LineType
    old_no: int | None = None
    new_no: int | None = None
    content: str


class DiffHunk(BaseModel):
    """A contiguous block of changes in a file."""

    header: str
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


class Turn(BaseModel):
    """One thing said in a thread after the comment that opened it."""

    author: TurnAuthor
    body: str
    round: int = 1


class Comment(BaseModel):
    """A thread hanging on a line or range of one side of the diff.

    Line numbers are only meaningful together with the side: a hunk that
    replaces a line has both an old line 42 and a new line 42.

    The comment that opened the thread stays in `body`, and everything said
    afterwards is a turn. Keeping the opening separate is not ceremony: it is
    what the anchor, the severity and the whole comment are about, and a
    review with nothing discussed is still only a body.
    """

    file: str
    side: LineSide
    severity: CommentSeverity
    start_line: int
    end_line: int
    body: str
    turns: list[Turn] = []
    # Settled, by the reader who opened it. Travels with the review, because
    # an agent reading a settled thread should not act on it again.
    resolved: bool = False
    # The lines it hung on are gone from the current diff. Then the anchor
    # says nothing useful and `quote` is what the thread is about.
    outdated: bool = False
    quote: list[str] = []


class ReviewResult(BaseModel):
    """Formatted review output."""

    markdown: str
    comment_count: int


class ThreadQuestion(BaseModel):
    """Something the reader asked about one comment thread.

    It carries the quoted lines as well as the question, because the Claude
    that answers may be reading this without the file in front of it.
    """

    thread_id: str
    # Which question in that thread. A thread can have more than one waiting
    # at a time, and an answer has to say which it belongs to.
    question_id: str
    file: str
    side: LineSide
    start_line: int
    end_line: int
    quote: list[str]
    body: str
    # What was already said in this thread, so an answer to the third
    # question is not written as if it were the first
    history: list[Turn] = []


class RoundSubmission(BaseModel):
    """One round of a review, on its way to whoever answers it.

    A round is everything written since the last one was sent. The review
    does not end with it: the agent answers, changes what it changed, and
    the diff is retaken under the same threads.
    """

    number: int
    markdown: str
    comment_count: int


class ThreadReply(BaseModel):
    """An answer to one thread, on its way back to the browser."""

    thread_id: str
    text: str
    question_id: str | None = None
