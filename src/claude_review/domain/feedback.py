"""Feedback on claude-review itself, written in a review and sent to whoever makes it.

What the reader wrote and chose to send with it, and the issue the review writes of that. Nothing of the review
they were reading is held here — no file, line, comment or story — so nothing of it can go: the part of the page
they point at comes named by the page's test ids, never by its words, and the rest is the reader's to tick.
"""

from enum import StrEnum, auto

from pydantic import BaseModel


class FeedbackKind(StrEnum):
    """What the feedback is: something wrong with claude-review, or something wanted of it."""

    BUG = auto()
    IDEA = auto()


class ReadingView(StrEnum):
    """Which way the review was being read: its files, or the story told of them."""

    FILES = auto()
    STORY = auto()


class ShownTheme(StrEnum):
    """The theme the page was drawn in, as the reader saw it."""

    LIGHT = auto()
    DARK = auto()


class Reading(BaseModel):
    """What the reader was reading in when they wrote: the view, the theme and the window's size."""

    view: ReadingView
    theme: ShownTheme
    window_width: int
    window_height: int


class PartBox(BaseModel):
    """Where a part of the page stood in the window, in pixels from its top left."""

    left: int
    top: int
    width: int
    height: int


class PointedPart(BaseModel):
    """A part of the page the reader pointed at: named by the page's test ids, and where it stood."""

    name: str
    box: PartBox


class GoesWithIt(StrEnum):
    """What may go with the words, each a row the reader ticks or not."""

    # Where the review runs: its release, the operating system and the browser
    MACHINE = auto()
    # What the reader was reading in
    READING = auto()
    # The part of the page they pointed at
    PART = auto()


class FeedbackDraft(BaseModel):
    """What the reader wrote, what else may go with it, and what of that they left ticked to go."""

    kind: FeedbackKind
    words: str
    reading: Reading
    # None until the reader points at a part
    part: PointedPart | None
    going: frozenset[GoesWithIt]


class Machine(BaseModel):
    """Where the review runs: its release, the operating system, and the browser its page was read in, if known."""

    release: str
    operating_system: str
    browser: str | None


class WithItSaid(BaseModel):
    """What each row that may go with the words says it sends, ticked or not, in the words the issue says it in."""

    machine: str
    reading: str
    # None while no part is pointed at
    part: str | None


class FeedbackIssue(BaseModel):
    """The issue written of the feedback, to the letter, and the ways it can go: to GitHub, or to the agent."""

    title: str
    body: str
    with_it: WithItSaid
    # The address that opens the issue on GitHub, filled in where it fits
    address: str
    # Whether the address carries the body too: one too long for GitHub to take carries the title alone
    filled: bool
    # What the agent is handed, to look for an issue like it and file it once the reader says so
    for_agent: str
