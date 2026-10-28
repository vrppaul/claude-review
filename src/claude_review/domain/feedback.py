"""Feedback on claude-review itself, written in a review and sent to whoever makes it.

What the reader wrote and chose to send with it, and the issue the review writes of that. Nothing of the review
they were reading is held here — no file, line, comment or story — so nothing of it can go: the part of the page
they point at comes named in the page's own words, by the page, and the rest is the reader's to tick.
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
    """A part of the page the reader pointed at: named in the page's own words, and where it stood."""

    name: str
    box: PartBox


class FeedbackDraft(BaseModel):
    """What the reader wrote, and what of the rest they left ticked to go with it."""

    kind: FeedbackKind
    words: str
    # Whether where the review runs goes with it: its release, the operating system and the browser
    with_machine: bool
    reading: Reading | None
    part: PointedPart | None


class Machine(BaseModel):
    """Where the review runs: its release, the operating system, and the browser its page was read in, if known."""

    release: str
    operating_system: str
    browser: str | None


class FeedbackIssue(BaseModel):
    """The issue written of the feedback, to the letter, and the ways it can go: to GitHub, or to the agent."""

    title: str
    body: str
    # The address that opens the issue on GitHub, filled in where it fits
    address: str
    # Whether the address carries the body too: one too long for GitHub to take carries the title alone
    filled: bool
    # What the agent is handed, to look for an issue like it and file it once the reader says so
    for_agent: str
