"""The issue the review writes of a reader's feedback, to the letter, for GitHub or for the agent.

Every word the issue says is written here, out of what the reader wrote and what they left ticked to go with it,
but the name of a part of the page they pointed at, which the page gives in its own words. The page shows the issue
as written before anything leaves, so a reader can see that none of their code and nothing of their review is in
it; and this module is where anyone can read how it is written. It is opened on GitHub by an address that carries
it filled in, which the reader sends from there themselves; or handed to the reader's agent, to look for an issue
like it and file this one as it is, once the reader has seen what it will file.
"""

import platform
import re
from urllib.parse import quote, urlencode

from claude_review.domain.feedback import (
    FeedbackDraft,
    FeedbackIssue,
    FeedbackKind,
    Machine,
    PointedPart,
    Reading,
    ReadingView,
    ShownTheme,
)

# Where the issue goes, the address that opens a new one there, and the fields of its form that address fills
REPOSITORY = "vrppaul/claude-review"
NEW_ISSUE_ADDRESS = f"https://github.com/{REPOSITORY}/issues/new"
TITLE_FIELD = "title"
BODY_FIELD = "body"
# The longest address the issue is opened with filled in: GitHub refuses one much past eight thousand characters
# (414), and VS Code's issue reporter stops at this many
FILLED_ADDRESS_LONGEST = 7_500
# The longest title, cut at a word: about as much as GitHub's list of issues shows
TITLE_LONGEST = 80
# What a title cut short ends with, and what stands between a size's width and height
ELLIPSIS = "…"
TIMES = "\N{MULTIPLICATION SIGN}"
# What the agent is handed besides the words: its lead-in, the title and the rows, each at the longest the API
# takes, fit in this many characters; the test that hands the longest feedback to the agent holds it
ROOM_AROUND_THE_WORDS = 1_000

# How the issue names each kind of feedback, at the head of its title and to the agent
KIND_HEADINGS = {FeedbackKind.BUG: "Bug", FeedbackKind.IDEA: "Idea"}
KIND_NAMES = {FeedbackKind.BUG: "a bug", FeedbackKind.IDEA: "an idea"}
# How it names the view the reader was in, and the theme they saw
VIEW_NAMES = {ReadingView.FILES: "Files", ReadingView.STORY: "Story"}
THEME_NAMES = {ShownTheme.LIGHT: "light", ShownTheme.DARK: "dark"}

# The operating systems by the names their makers give them, where Python's differs
OPERATING_SYSTEM_NAMES = {"Darwin": "macOS"}

# The most digits a browser's release is read with: a user agent is whatever the request says, and no browser
# numbers a release past this
RELEASE_DIGITS_MOST = 5
RELEASE = rf"(?P<release>\d{{1,{RELEASE_DIGITS_MOST}}})"
# A browser by the mark its user agent carries, and the number of its release after it. In this order: Edge and
# Opera carry Chrome's mark as well, and Chrome carries Safari's, so the more particular mark is read first;
# Safari numbers its release after `Version/`
BROWSER_MARKS = (
    ("Edge", re.compile(rf"Edg/{RELEASE}")),
    ("Opera", re.compile(rf"OPR/{RELEASE}")),
    ("Firefox", re.compile(rf"Firefox/{RELEASE}")),
    ("Chrome", re.compile(rf"Chrome/{RELEASE}")),
    ("Safari", re.compile(rf"Version/{RELEASE}[^ ]* Safari/")),
)


def issue_of(draft: FeedbackDraft, machine: Machine) -> FeedbackIssue:
    """The issue written of the feedback, and the address that opens it on GitHub, filled in where that fits."""
    title = _title(draft)
    body = _body(draft, machine)
    filled_address = _address(title=title, body=body)
    filled = len(filled_address) <= FILLED_ADDRESS_LONGEST
    return FeedbackIssue(
        title=title,
        body=body,
        address=filled_address if filled else _address(title=title),
        filled=filled,
        for_agent=_for_agent(draft.kind, title, body),
    )


def browser_named(user_agent: str | None) -> str | None:
    """The browser a page was read in and its release, from the user agent it sends; none where no mark is known."""
    if user_agent is None:
        return None
    for name, mark in BROWSER_MARKS:
        if found := mark.search(user_agent):
            return f"{name} {found['release']}"
    return None


def operating_system_named(platform_name: str) -> str:
    """An operating system by the name its maker gives it, from the name Python reads off the platform."""
    return OPERATING_SYSTEM_NAMES.get(platform_name, platform_name)


# The operating system the review runs on, read once
THIS_OPERATING_SYSTEM = operating_system_named(platform.system())


def _title(draft: FeedbackDraft) -> str:
    """Its kind and the first line written, its spaces as one, cut short at a word, or in one where none ends.

    The room before the ellipsis is read with the character after it, so a word ending right where the room ends
    is kept whole.
    """
    heading = f"{KIND_HEADINGS[draft.kind]}: "
    first_line, *_ = draft.words.strip().splitlines()
    line = " ".join(first_line.split())
    if len(heading) + len(line) <= TITLE_LONGEST:
        return heading + line
    room = line[: TITLE_LONGEST - len(heading) - len(ELLIPSIS) + 1]
    word_end = room.rfind(" ")
    kept = room[:word_end] if word_end > 0 else room[:-1]
    return heading + kept + ELLIPSIS


def _body(draft: FeedbackDraft, machine: Machine) -> str:
    """What was written, then a line for each thing the reader left ticked to go with it."""
    words = draft.words.strip()
    with_it: list[str] = []
    if draft.with_machine:
        with_it.append(_machine_line(machine))
    if draft.reading is not None:
        with_it.append(_reading_line(draft.reading))
    if draft.part is not None:
        with_it.append(_part_line(draft.part))
    if not with_it:
        return words
    return f"{words}\n\n" + "\n".join(with_it)


def _machine_line(machine: Machine) -> str:
    browser = "" if machine.browser is None else f", {machine.browser}"
    return f"claude-review {machine.release}, {machine.operating_system}{browser}"


def _reading_line(reading: Reading) -> str:
    return (
        f"Reading {VIEW_NAMES[reading.view]}, the {THEME_NAMES[reading.theme]} theme, "
        f"a window {reading.window_width} {TIMES} {reading.window_height}"
    )


def _part_line(part: PointedPart) -> str:
    box = part.box
    return f"Pointed at {part.name}, {box.width} {TIMES} {box.height} at {box.left}, {box.top}"


def _address(*, title: str, body: str | None = None) -> str:
    """The address of a new issue in the repository, its title and, where given, its body filled in."""
    fields = {TITLE_FIELD: title} if body is None else {TITLE_FIELD: title, BODY_FIELD: body}
    return f"{NEW_ISSUE_ADDRESS}?{urlencode(fields, quote_via=quote)}"


def _for_agent(kind: FeedbackKind, title: str, body: str) -> str:
    """The issue as the agent is handed it: where it goes, filed as written, and seen by the reader before it is."""
    return (
        f"Feedback on claude-review, {KIND_NAMES[kind]}, for {REPOSITORY}. Look for an issue like it first, then show "
        "me what you will file: the title and body below as they are, adding nothing of this review. File it only "
        f"once I say so.\n\n{title}\n\n{body}"
    )
