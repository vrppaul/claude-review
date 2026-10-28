"""What the page sends of a reader's feedback on the review, and the issue the review writes of it.

The page names the part of itself the reader pointed at, in its own words; everything else the issue says is
written by the review (`services/feedback.py`).
"""

from typing import Annotated, Self

from pydantic import ConfigDict, Field, StrictBool, StrictInt

from claude_review.domain.feedback import (
    FeedbackDraft,
    FeedbackIssue,
    FeedbackKind,
    PartBox,
    PointedPart,
    Reading,
    ReadingView,
    ShownTheme,
)
from claude_review.presentation.schemas.base import MAX_TEXT_LENGTH, SaidWords, Schema, made_or_none
from claude_review.services.feedback import ROOM_AROUND_THE_WORDS

# The longest name of a part of the page: its own words, from its pane down to the part, a line or two
MAX_PART_NAME_LENGTH = 200
# A part's name, on the one line of the issue it stands in, saying something
ONE_LINE_SAYING_SOMETHING = r"^[^\r\n]*\S[^\r\n]*$"
PartName = Annotated[str, Field(min_length=1, max_length=MAX_PART_NAME_LENGTH, pattern=ONE_LINE_SAYING_SOMETHING)]
# The most the reader may write: as much as anything said, less what the agent's message holds around it, so the
# feedback handed to the agent is a message the panel takes
MAX_FEEDBACK_WORDS = MAX_TEXT_LENGTH - ROOM_AROUND_THE_WORDS
FeedbackWords = Annotated[SaidWords, Field(max_length=MAX_FEEDBACK_WORDS)]

# The most pixels a size or a place may count: far past any window, or any part a page draws
MAX_PIXELS = 1_000_000
# A window's side, or a part's, in pixels
Pixels = Annotated[StrictInt, Field(ge=0, le=MAX_PIXELS)]
# How far a part's edge stood from the window's, in pixels: a part wider than the window, scrolled, starts before it
PixelsFromTheEdge = Annotated[StrictInt, Field(ge=-MAX_PIXELS, le=MAX_PIXELS)]


class ReadingSent(Schema):
    """What the reader was reading in: the view, the theme they saw and the window's size."""

    model_config = ConfigDict(extra="forbid")

    view: ReadingView
    theme: ShownTheme
    window_width: Pixels
    window_height: Pixels

    def to_domain(self) -> Reading:
        return Reading(
            view=self.view, theme=self.theme, window_width=self.window_width, window_height=self.window_height
        )


class PartSent(Schema):
    """A part of the page the reader pointed at, named in the page's own words, and where it stood in the window."""

    model_config = ConfigDict(extra="forbid")

    name: PartName
    left: PixelsFromTheEdge
    top: PixelsFromTheEdge
    width: Pixels
    height: Pixels

    def to_domain(self) -> PointedPart:
        return PointedPart(
            name=self.name, box=PartBox(left=self.left, top=self.top, width=self.width, height=self.height)
        )


class FeedbackRequest(Schema):
    """Request body for POST /api/feedback — what the reader wrote, and what they left ticked to go with it."""

    model_config = ConfigDict(extra="forbid")

    kind: FeedbackKind
    words: FeedbackWords
    # Whether where the review runs goes with it: its release, the operating system and the browser
    with_machine: StrictBool
    reading: ReadingSent | None
    part: PartSent | None

    def to_domain(self) -> FeedbackDraft:
        return FeedbackDraft(
            kind=self.kind,
            words=self.words,
            with_machine=self.with_machine,
            reading=made_or_none(ReadingSent.to_domain, self.reading),
            part=made_or_none(PartSent.to_domain, self.part),
        )


class FeedbackIssueResponse(Schema):
    """The issue written of the feedback, to the letter, and the ways it can go: to GitHub, or to the agent."""

    title: str
    body: str
    # The address that opens the issue on GitHub, filled in where it fits
    address: str
    # Whether the address carries the body too: one too long for GitHub to take carries the title alone
    filled: StrictBool
    # What the agent is handed, to look for an issue like it and file it once the reader says so
    for_agent: str

    @classmethod
    def from_domain(cls, issue: FeedbackIssue) -> Self:
        return cls(
            title=issue.title, body=issue.body, address=issue.address, filled=issue.filled, for_agent=issue.for_agent
        )
