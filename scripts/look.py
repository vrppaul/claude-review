"""Look at the review's page as a reader would, and say what is there.

A change to what the reader sees is looked at in a browser before it is
called done, and whoever reviews it looks again. Each of those looks used to
be a script written for it: one to make a change long enough to scroll, one
to serve it, one to open a browser and print what it read off the page.
Thirty-six were written in one day, each starting the server and the
browser its own way, and some left a server running. This is that look,
written once.

It makes a repository of its own with a long change in it (`long_change.py`
says what the change is), serves the change through the review's own
command line, tells a story of it the same way, opens Chromium once, takes
the steps it is handed, and stops the server it started, by that server's
pid. The repository, the story and what the review remembers about its
reader are kept in a directory of the look's own, removed as it ends: a
look writes nothing where it is run, and a fresh reader opens the page
every time.

    uv run python scripts/look.py [--view story|files] [--theme light|dark]
        [--width PIXELS] [--shots DIRECTORY] [--untold] STEP...
    uv run python scripts/look.py --keep [--untold]

`--untold` leaves the change untold: the page opens on a review that holds
no story, as every review does until its agent tells one. What the page
shows a reader who asks for a story and waits for it is reached from there,
with the steps that are the agent's. The look's reader has not turned
stories on, so an untold change asked for as its story opens on the files,
under the question the page asks before a story is written.

Run in the repository's root. The review serves the page as it was last
built, so a look is refused when a file under `frontend/src` was written
after the build: it would be a look at an older page than the one written.
Build first, `cd frontend && pnpm build`.

A step is one of

    press:TEST_ID        press the first element of that test id
    press:TEST_ID:NTH    press another of them, counted from 0 as Playwright counts
    key:KEY              press a key, named as Playwright names keys: j, Tab, Control+Enter
    scroll:PIXELS        scroll the reading area down by that many pixels, or up by a number below zero
    shot:NAME            keep a picture of the window as NAME.png in the directory --shots names
    agent:wait           the review's agent waits a moment for what the reader hands over, as
                         `claude-review wait` does: it is attached from then on, and has taken
                         what the review held for it
    agent:story          the review's agent tells the story, as `claude-review story` does

As the page opens and after each step the look prints one line, each value
under its name: the step; `page`, how much taller than its window the page
is and how far it has scrolled, both 0 on a page that holds its place;
`area`, the reading area on screen, how far it has scrolled, its height and
the height of what it holds; `keyboard`, what holds the keyboard, by its
tag, test id and label, whether it is ringed, and its box; `bar`, what the
chapter bar says; `read`, the parts of the story read through; `reading`,
the part being read. The line of the page as it opens says where the review
was served.

The page is read once it has said the same for a moment, so a glide is over
when its line is printed. A page that has not come to rest after a few
seconds is printed as it is, its step marked as still moving.

A step that cannot be taken ends the look. Of a press it is said which of
three things stood in its way: no element of that test id, fewer of them
than were counted to, or one that is there and takes no press. A key
Playwright does not know ends it too. The step is named on stderr and the
look exits 1; the steps after it are not taken. A command of the agent's
that the review refuses ends the look the same way, said as the command and
what it printed. A picture with no directory named to keep it in is refused
earlier, as the command line is read.

With a story's contents put away, as they are on a narrow window until
they are brought back, `read` and `reading` say so: the contents are what
says them.

`--keep`, in place of steps: serve the change, tell its story unless it is
left untold, print where the review is, and stay until the review ends. A
review ends once its page has been closed, so a kept look opens none: it is
how a page is put before a person.

Stopped from outside, by SIGTERM or at Ctrl-C, a look ends where it stands:
it closes its browser, stops its server and removes its directory on the
way out. That holds from the first line of the look's own. Before it, while
Python is still loading the look, about its first tenth of a second, the
look has made nothing, and a signal ends it as it ends any process.

Elements are found by test id alone.

Exits 0 having looked, or having kept a review until it ended; 2 at a
command line it cannot read; 130 stopped from outside. It exits 1, with the
reason on stderr, whenever it could not look: run where there is no page,
or the page is not built, or was built before a source of it was last
written; git could not make the repository, the review could not be served
or did not take the story, or one of those commands ran out of its time;
the page did not open; or a step could not be taken.
"""

import argparse
import asyncio
import contextlib
import os
import re
import sys
import tempfile
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Callable, Coroutine, Generator
from enum import StrEnum, auto
from functools import partial
from pathlib import Path
from typing import Self, override

from playwright.async_api import Error as BrowserError, Page, async_playwright
from pydantic import BaseModel, ConfigDict, Field

from commands import CommandFailedError, Running, complete, exit_code_of, run, running
from long_change import CHANGED, COMMITTED, THE_STORY

# The review's own command line, run in the environment the look runs in
REVIEW = (sys.executable, "-m", "claude_review")
# The port asked for to be given any free one
ANY_PORT = "0"
# How the review says where it is, on stderr, once it is served
READY_ANNOUNCEMENT = "Review ready at "
# What stands between an address and its port
BEFORE_THE_PORT = ":"
# How long the review has to say where it is, and how long git and the review's commands have to end
SERVED_WITHIN_SECONDS = 30
COMMAND_WITHIN_SECONDS = 60
# How long the agent's wait waits for the reader, in seconds as the command line takes them: what a look
# hands the agent is held by the review before the wait begins, so a moment is enough to take it
AGENT_WAITS_SECONDS = "0.1"

# Where the review keeps what it remembers about its reader, by the XDG base directory rules
CONFIG_HOME_VARIABLE = "XDG_CONFIG_HOME"
STATE_HOME_VARIABLE = "XDG_STATE_HOME"
# Where git reads the settings of whoever runs it and of the machine: nowhere, so a look is the
# same look on every machine
GIT_VARIABLE_PREFIX = "GIT_"
GIT_SETTINGS_OF_THE_USER = "GIT_CONFIG_GLOBAL"
GIT_WITHOUT_THE_MACHINES_SETTINGS = "GIT_CONFIG_NOSYSTEM"
GIT_YES = "1"

# What the look's own directory holds: the repository, the story's document, and the reader's two homes
REPOSITORY = "long-change"
STORY_DOCUMENT = "story.json"
CONFIG_HOME = "config"
STATE_HOME = "state"
SCRATCH_PREFIX = "claude-review-look-"

# How git commits what the change is made against, and as whom
COMMITTED_AS = ("-c", "user.name=A look", "-c", "user.email=look@example.invalid")
GIT_COMMANDS = (
    ("init", "--quiet", "--initial-branch", "main"),
    ("add", "--all"),
    (*COMMITTED_AS, "commit", "--quiet", "--message", "chore: what the long change is made against"),
)

# How tall the window is, and how wide unless a look asks
WINDOW_HEIGHT = 900
WIDTH_UNLESS_ASKED = 1440
# How long the browser waits for an element before a step on it cannot be taken
STEP_WITHIN_MS = 3_000
# The page has come to rest once it has said the same for this long, looked at this often;
# after this long it is said as it is
STILL_FOR_SECONDS = 0.3
LOOKED_AT_EVERY_SECONDS = 0.1
GIVEN_UP_AFTER_SECONDS = 5.0

# The button that puts away the card offering a fresh reader the tour: the card stands over the page
TOUR_NOT_NOW = "guide-not-now"
# The bar that says which chapter is read, an entry of the story's contents, the mark of one read
# through, and the entry of what no step tells
CHAPTER_BAR = "chapter-bar"
PART_ENTRY = "go-to-part"
READ_MARK = "part-read-mark"
LEFT_OUT_ENTRY = "contents-left-out"
ANY_ENTRY = re.compile(f"^(?:{PART_ENTRY}|{LEFT_OUT_ENTRY})$")

# How much taller than its window the page is, and how far the page itself has scrolled
THE_PAGE_ITSELF = """() => ({
    taller: document.documentElement.scrollHeight - window.innerHeight,
    scrolled: Math.round(window.scrollY),
})"""
# The reading area: which it is, how far it has scrolled, its height, and the height of what it holds
THE_READING_AREA = """(area) => ({
    test_id: area.dataset.testid,
    scroll_top: Math.round(area.scrollTop),
    height: area.clientHeight,
    holds: area.scrollHeight,
})"""
# What holds the keyboard: the page's body when nothing does
THE_KEYBOARDS_HOLDER = """() => {
    const holder = document.activeElement;
    const box = holder.getBoundingClientRect();
    return {
        tag: holder.tagName,
        test_id: holder.dataset.testid ?? null,
        label: holder.getAttribute('aria-label'),
        ringed: holder.matches(':focus-visible'),
        width: Math.round(box.width),
        height: Math.round(box.height),
    };
}"""
# What entries of the contents are called, and what those being read are called: an entry
# with no name of its own is called by its words
THEIR_NAMES = "(entries) => entries.map((entry) => entry.getAttribute('aria-label'))"
NAMES_OF_THOSE_BEING_READ = """(entries) => entries
    .filter((entry) => entry.hasAttribute('aria-current'))
    .map((entry) => entry.getAttribute('aria-label') ?? entry.textContent)"""
# Scroll an area down by a number of pixels, at once
SCROLLED_DOWN_BY = "(area, pixels) => area.scrollBy(0, pixels)"

# What parts the kind of a step from the rest of it, and a test id from the count after it
WITHIN_A_STEP = ":"
# The first element of a test id, as it is counted
THE_FIRST = "0"
# How a picture's file is named after its step
PICTURE_SUFFIX = ".png"

# What parts the values of a line, and the names of a list; what stands where there is nothing to say
BETWEEN_VALUES = " | "
BETWEEN_NAMES = " + "
NOTHING = "none"
# What brings a story's contents back once they are put away, there only then; and what a line says
# then of what is read, which the contents alone say
BRINGS_THE_CONTENTS_BACK = "show-contents"
CONTENTS_PUT_AWAY = "contents put away"
YES_OR_NO = {True: "yes", False: "no"}
# What a line opens with as the page opens, and a kept look's line of where its review is
OPENED = "open"
KEPT = "kept"
# What is said of a step whose page had not come to rest when it was read
STILL_MOVING = {True: ", still moving", False: ""}
# What ends a line of what the browser says went wrong: the rest is its own log
END_OF_LINE = "\n"

# The page's sources and the page as it was built, from the repository's root, where a look is run;
# how the page is built, and what is said of a page that cannot be looked at as it is
PAGE_SOURCES = Path("frontend/src")
BUILT_PAGE = Path("src/claude_review/static/dist/index.html")
HOW_IT_IS_BUILT = "`cd frontend && pnpm build`"
NO_PAGE_HERE = f"there is no {PAGE_SOURCES} here: a look is run in the repository's root"
NOT_BUILT = f"the page is not built: build it, {HOW_IT_IS_BUILT}"
BUILT_BEFORE = (
    "the page was built before {source} was last written, so a look would be a look at an older page: "
    f"build it again, {HOW_IT_IS_BUILT}"
)

# What is said of a look that cannot go on
NOT_SERVED = "the review ended before it said where it is: {said}"
NOT_SERVED_IN_TIME = f"the review did not say where it is within {SERVED_WITHIN_SECONDS} seconds"
NOT_TAKEN = "{step} could not be taken: {why}"
# What is said of a press that cannot be taken, by what stood in its way
NO_SUCH_ELEMENT = "{step} could not be taken: there is no element of test id {test_id} on the page"
TOO_FEW_ELEMENTS = "{step} could not be taken: there are {count} elements of test id {test_id}, counted from 0"
NOT_PRESSED = (
    "{step} could not be taken: the element is there and could not be pressed "
    f"within {STEP_WITHIN_MS} ms: it is hidden, disabled, or under something else"
)
# What is said of a picture with nowhere to go, and of one with no name
NOWHERE_TO_KEEP_IT = "{step} keeps a picture, and no directory was named to keep it in: name one with --shots"
NO_NAME = "a picture is kept under a name"
# What is said of what the command line cannot be read as
NOT_A_STEP = (
    "{written} is not a step: a step is press:TEST_ID, press:TEST_ID:NTH, key:KEY, scroll:PIXELS, shot:NAME, "
    "agent:wait or agent:story"
)
KEPT_TAKES_NO_STEPS = "--keep takes no steps: a kept look opens no page to take them on"

# What the look exits with: looked, or kept until its review ended; ended at a step or before the
# page opened. Stopped from outside, it exits as every script does
LOOKED = 0
NOT_LOOKED = 1

FROZEN = ConfigDict(frozen=True)


class LookFailedError(Exception):
    """The look cannot go on: what it says is what is printed."""


class NotAStepError(Exception):
    """A word of the command line writes no step: what it says is what the command line is refused with."""


class NowhereToKeepError(Exception):
    """A step keeps a picture, and the command line names no directory for pictures."""


class View(BaseModel):
    """A way of reading the review: the control that chooses it, and the area that is then read in."""

    model_config = FROZEN

    switch: str
    area: str


STORY_VIEW = "story"
VIEWS = {
    STORY_VIEW: View(switch="read-as-story", area="story-view"),
    "files": View(switch="read-as-files", area="diff-view"),
}
# The reading area on screen: whichever view's is drawn, and only one is
READING_AREA = re.compile("^(?:" + "|".join(view.area for view in VIEWS.values()) + ")$")


class Theme(StrEnum):
    """The colours the reader's system asks for, which the page follows until the reader chooses."""

    LIGHT = auto()
    DARK = auto()


class Agent(BaseModel):
    """The review's agent, whom the look stands in for: each thing it does is one command of the review's own."""

    model_config = FROZEN

    # The port the review is served on, as its commands take it
    port: str
    environment: dict[str, str]
    # Where the story's document is written, for the command that tells it to read
    document: Path

    async def waits(self) -> None:
        """Wait a moment for what the reader hands over next: the review counts an agent attached from then on.

        Raises:
            CommandFailedError: if the review refuses the wait.
        """
        await self._runs("wait", "--seconds", AGENT_WAITS_SECONDS)

    async def tells_the_story(self) -> None:
        """Tell the story of the change: its document handed to the `story` command.

        Raises:
            CommandFailedError: if the review refuses the story.
        """
        await asyncio.to_thread(self.document.write_text, THE_STORY.model_dump_json())
        await self._runs("story", "--file", str(self.document))

    async def _runs(self, command: str, *options: str) -> None:
        """Run one command of the review's against the review served, and hold it to having done what it was asked."""
        ran = await run((*REVIEW, command, "--port", self.port, *options), self.environment, COMMAND_WITHIN_SECONDS)
        ran.must_have_succeeded()


class Stage(BaseModel):
    """What a step is taken on: the page open in the look's window, and the agent of the review it shows."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    page: Page
    agent: Agent


class Step(BaseModel, ABC):
    """One thing done in a look, on the page or by the review's agent, kept as it was written on the command line."""

    model_config = FROZEN

    written: str

    @abstractmethod
    async def take(self, stage: Stage) -> None:
        """Do it.

        Raises:
            LookFailedError: if it cannot be done, for a reason the step can say itself.
            CommandFailedError: if it is the agent's, and the review refuses its command.
        """


class Press(Step):
    """A press on an element, found by its test id and its place among those of that id."""

    test_id: str = Field(min_length=1)
    nth: int = Field(ge=0)

    @classmethod
    def read(cls, written: str, detail: str) -> Self:
        """The press a step writes: a test id, and after it the place among those of that id, the first unless said.

        Raises:
            ValueError: if no test id is written, or the place is no number.
        """
        test_id, _, nth = detail.partition(WITHIN_A_STEP)
        return cls(written=written, test_id=test_id, nth=int(nth or THE_FIRST))

    @override
    async def take(self, stage: Stage) -> None:
        elements = stage.page.get_by_test_id(self.test_id)
        count = await elements.count()
        if count == 0:
            failure = NO_SUCH_ELEMENT.format(step=self.written, test_id=self.test_id)
            raise LookFailedError(failure)
        if self.nth >= count:
            failure = TOO_FEW_ELEMENTS.format(step=self.written, count=count, test_id=self.test_id)
            raise LookFailedError(failure)
        try:
            await elements.nth(self.nth).click()
        except BrowserError as error:
            failure = NOT_PRESSED.format(step=self.written)
            raise LookFailedError(failure) from error


class Key(Step):
    """A key pressed on whatever holds the keyboard."""

    key: str = Field(min_length=1)

    @classmethod
    def read(cls, written: str, detail: str) -> Self:
        """The key a step writes.

        Raises:
            ValueError: if none is written.
        """
        return cls(written=written, key=detail)

    @override
    async def take(self, stage: Stage) -> None:
        await stage.page.keyboard.press(self.key)


class Scroll(Step):
    """The reading area scrolled down by a number of pixels."""

    pixels: int

    @classmethod
    def read(cls, written: str, detail: str) -> Self:
        """The scroll a step writes.

        Raises:
            ValueError: if what is written is no number of pixels.
        """
        return cls(written=written, pixels=int(detail))

    @override
    async def take(self, stage: Stage) -> None:
        await stage.page.get_by_test_id(READING_AREA).evaluate(SCROLLED_DOWN_BY, self.pixels)


class Shot(Step):
    """A picture of the window, and the file it is kept in."""

    file: Path

    @classmethod
    def kept_in(cls, shots: Path | None, written: str, detail: str) -> Self:
        """The picture a step writes, kept under its name in the directory for pictures.

        Raises:
            NowhereToKeepError: if no directory was named for them.
            ValueError: if no name is written.
        """
        if shots is None:
            raise NowhereToKeepError(NOWHERE_TO_KEEP_IT.format(step=written))
        if not detail:
            raise ValueError(NO_NAME)
        return cls(written=written, file=shots / f"{detail}{PICTURE_SUFFIX}")

    @override
    async def take(self, stage: Stage) -> None:
        await stage.page.screenshot(path=self.file)


class AgentCommand(StrEnum):
    """A command of the review's own that a look runs as the review's agent, as a step writes it."""

    WAIT = auto()
    STORY = auto()


# What the review's agent does at each command
AS_THE_AGENT: dict[AgentCommand, Callable[[Agent], Coroutine[None, None, None]]] = {
    AgentCommand.WAIT: Agent.waits,
    AgentCommand.STORY: Agent.tells_the_story,
}


class ByTheAgent(Step):
    """One thing the review's agent does while the page is open."""

    command: AgentCommand

    @classmethod
    def read(cls, written: str, detail: str) -> Self:
        """What a step writes for the agent to do.

        Raises:
            ValueError: if it names no command a look runs as the agent.
        """
        return cls(written=written, command=AgentCommand(detail))

    @override
    async def take(self, stage: Stage) -> None:
        await AS_THE_AGENT[self.command](stage.agent)


# What makes a step of what is written on the command line, given the step as written and what stands after its kind
StepReader = Callable[[str, str], Step]


def _step_readers(shots: Path | None) -> dict[str, StepReader]:
    """What reads each kind of step, by what the kind is written as: a picture is read knowing where pictures go."""
    return {
        "press": Press.read,
        "key": Key.read,
        "scroll": Scroll.read,
        "shot": partial(Shot.kept_in, shots),
        "agent": ByTheAgent.read,
    }


class Asked(BaseModel):
    """What a look was asked for on the command line."""

    model_config = FROZEN

    view: View
    theme: Theme
    width: int
    # Whether the story is told before the page opens: left untold, the review holds none until a step tells it
    story_told: bool
    keep: bool
    steps: list[Step]


class PageSeen(BaseModel):
    """The page itself against its window: 0 and 0 on a page that holds its place."""

    model_config = FROZEN

    taller: int
    scrolled: int

    def __str__(self) -> str:
        return f"taller={self.taller} scrolled={self.scrolled}"


class AreaSeen(BaseModel):
    """The reading area on screen: which it is, how far it has scrolled, and how much it holds."""

    model_config = FROZEN

    test_id: str
    scroll_top: int
    height: int
    holds: int

    def __str__(self) -> str:
        return f"{self.test_id} scrollTop={self.scroll_top} height={self.height} holds={self.holds}"


class KeyboardSeen(BaseModel):
    """What holds the keyboard, and whether the browser rings it."""

    model_config = FROZEN

    tag: str
    test_id: str | None
    label: str | None
    ringed: bool
    width: int
    height: int

    def __str__(self) -> str:
        return (
            f"{self.tag} testid={self.test_id or NOTHING} label={_quoted(self.label)} "
            f"ringed={YES_OR_NO[self.ringed]} box={self.width}x{self.height}"
        )


class Seen(BaseModel):
    """What the page says at one moment."""

    model_config = FROZEN

    page: PageSeen
    area: AreaSeen
    keyboard: KeyboardSeen
    # What the chapter bar says: nothing while no chapter's head has left the screen
    bar: list[str]
    read: list[str]
    being_read: list[str]
    # Whether a story's contents are put away: they are what says which parts are read and being read
    contents_put_away: bool

    def _said_by_the_contents(self, names: list[str]) -> str:
        """Names the contents say, or that the contents are put away and say nothing a look can read."""
        if self.contents_put_away:
            return CONTENTS_PUT_AWAY
        return _listed(names)

    def said_after(self, step: str) -> str:
        """The one line of it, each value under its name, after the step that led to it."""
        return BETWEEN_VALUES.join(
            [
                step,
                f"page: {self.page}",
                f"area: {self.area}",
                f"keyboard: {self.keyboard}",
                f"bar: {_listed(self.bar)}",
                f"read: {self._said_by_the_contents(self.read)}",
                f"reading: {self._said_by_the_contents(self.being_read)}",
            ]
        )


class AtRest(BaseModel):
    """What the page said once it had come to rest, or as it was when the look stopped waiting for it to."""

    model_config = FROZEN

    seen: Seen
    moving: bool

    def said_after(self, step: str) -> str:
        return self.seen.said_after(f"{step}{STILL_MOVING[self.moving]}")


class Served(BaseModel):
    """A review the look serves: where it is, and the process serving it."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    address: str
    server: Running

    def port(self) -> str:
        _, _, port = self.address.rpartition(BEFORE_THE_PORT)
        return port


def _on_one_line(words: str) -> str:
    """Words as the page gives them, with every run of space and every line end in them a single space."""
    return " ".join(words.split())


def _quoted(label: str | None) -> str:
    """A label between quotes, so its words are told from the values after it; no label is said outright."""
    if label is None:
        return NOTHING
    return f'"{_on_one_line(label)}"'


def _listed(names: list[str]) -> str:
    return BETWEEN_NAMES.join(_on_one_line(name) for name in names) or NOTHING


def _environment(scratch: Path) -> dict[str, str]:
    """What everything the look starts runs with: a reader of its own, and none of the settings git has here."""
    inherited = {name: value for name, value in os.environ.items() if not name.startswith(GIT_VARIABLE_PREFIX)}
    return {
        **inherited,
        CONFIG_HOME_VARIABLE: str(scratch / CONFIG_HOME),
        STATE_HOME_VARIABLE: str(scratch / STATE_HOME),
        GIT_SETTINGS_OF_THE_USER: os.devnull,
        GIT_WITHOUT_THE_MACHINES_SETTINGS: GIT_YES,
    }


def _write(root: Path, files: dict[str, str]) -> None:
    """Write each file under the root, by its path there."""
    for path, text in files.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text)


async def _long_change(repository: Path, environment: dict[str, str]) -> None:
    """Make the repository: its files committed, then the change left in its working tree.

    Raises:
        CommandFailedError: if git cannot.
    """
    await asyncio.to_thread(_write, repository, COMMITTED)
    for arguments in GIT_COMMANDS:
        made = await run(("git", "-C", str(repository), *arguments), environment, COMMAND_WITHIN_SECONDS)
        made.must_have_succeeded()
    await asyncio.to_thread(_write, repository, CHANGED)


async def _address_announced(server: Running) -> str:
    """Where the review says it is, as whoever starts one in the background reads it: off its stderr.

    Raises:
        LookFailedError: if the review ends without saying, with what it said in its place.
    """
    said = []
    while line := await server.line_said():
        if line.startswith(READY_ANNOUNCEMENT):
            return line.removeprefix(READY_ANNOUNCEMENT).strip()
        said.append(line.strip())
    failure = NOT_SERVED.format(said=" ".join(said))
    raise LookFailedError(failure)


async def _address_of(server: Running) -> str:
    """Where a review just started is served, once it says.

    Raises:
        LookFailedError: if it has not said in the time a review takes to start many times over.
    """
    try:
        return await asyncio.wait_for(_address_announced(server), timeout=SERVED_WITHIN_SECONDS)
    except TimeoutError as error:
        raise LookFailedError(NOT_SERVED_IN_TIME) from error


@contextlib.asynccontextmanager
async def _served(repository: Path, environment: dict[str, str]) -> AsyncGenerator[Served]:
    """Serve the review of the repository's change through the review's own command line, while the block runs.

    Raises:
        LookFailedError: if the review does not say where it is.
    """
    async with running((*REVIEW, "diff", "--port", ANY_PORT, "--no-open", str(repository)), environment) as server:
        yield Served(address=await _address_of(server), server=server)


@contextlib.asynccontextmanager
async def _window(asked: Asked) -> AsyncGenerator[Page]:
    """A Chromium window of the width and the theme asked for, closed as the block ends."""
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        try:
            page = await browser.new_page(
                viewport={"width": asked.width, "height": WINDOW_HEIGHT}, color_scheme=asked.theme.value
            )
            page.set_default_timeout(STEP_WITHIN_MS)
            yield page
        finally:
            await browser.close()


@contextlib.contextmanager
def _ending_the_look_at(step: str) -> Generator[None]:
    """End the look, naming the step, if the browser cannot do what the block asks of it."""
    try:
        yield
    except BrowserError as error:
        why, _, _ = error.message.partition(END_OF_LINE)
        failure = NOT_TAKEN.format(step=step, why=why)
        raise LookFailedError(failure) from error


async def _opened(page: Page, address: str, view: View) -> None:
    """Open the review as a reader new to it would, put the offer of a tour away, and ask to read it the way asked.

    The page shows that view, or asks first: a reader who has not turned stories on is asked before
    a story is written, and what the look then reads is the files, with that question over them.
    """
    await page.goto(address)
    await page.get_by_test_id(TOUR_NOT_NOW).click()
    await page.get_by_test_id(view.switch).click()
    await page.get_by_test_id(READING_AREA).wait_for()


async def _seen(page: Page) -> Seen:
    """What the page says now."""
    return Seen(
        page=PageSeen.model_validate(await page.evaluate(THE_PAGE_ITSELF)),
        area=AreaSeen.model_validate(await page.get_by_test_id(READING_AREA).evaluate(THE_READING_AREA)),
        keyboard=KeyboardSeen.model_validate(await page.evaluate(THE_KEYBOARDS_HOLDER)),
        bar=await page.get_by_test_id(CHAPTER_BAR).all_inner_texts(),
        read=await page.get_by_test_id(PART_ENTRY).filter(has=page.get_by_test_id(READ_MARK)).evaluate_all(THEIR_NAMES),
        being_read=await page.get_by_test_id(ANY_ENTRY).evaluate_all(NAMES_OF_THOSE_BEING_READ),
        contents_put_away=await page.get_by_test_id(BRINGS_THE_CONTENTS_BACK).count() > 0,
    )


async def _at_rest(page: Page) -> AtRest:
    """What the page says once it has said the same for a moment, or as it is if it never does."""
    clock = asyncio.get_running_loop()
    started = same_since = clock.time()
    seen = await _seen(page)
    while clock.time() - same_since < STILL_FOR_SECONDS and clock.time() - started < GIVEN_UP_AFTER_SECONDS:
        await asyncio.sleep(LOOKED_AT_EVERY_SECONDS)
        seen_now = await _seen(page)
        if seen_now != seen:
            seen, same_since = seen_now, clock.time()
    return AtRest(seen=seen, moving=clock.time() - same_since < STILL_FOR_SECONDS)


async def _steps_taken(served: Served, agent: Agent, asked: Asked) -> None:
    """Open the review in a window, take each step, and print what is there as it opens and after each."""
    async with _window(asked) as page:
        with _ending_the_look_at(OPENED):
            await _opened(page, served.address, asked.view)
            print((await _at_rest(page)).said_after(f"{OPENED} {served.address}"), flush=True)
        stage = Stage(page=page, agent=agent)
        for step in asked.steps:
            with _ending_the_look_at(step.written):
                await step.take(stage)
                print((await _at_rest(page)).said_after(step.written), flush=True)


async def _kept(served: Served) -> None:
    """Say where the review is, and stay until it ends."""
    print(f"{KEPT} {served.address}", flush=True)
    await served.server.ended()


async def _look(asked: Asked, scratch: Path) -> None:
    """Serve the long change, its story told unless it is left untold, and take the steps or keep it for a reader."""
    environment = _environment(scratch)
    await _long_change(scratch / REPOSITORY, environment)
    async with _served(scratch / REPOSITORY, environment) as served:
        agent = Agent(port=served.port(), environment=environment, document=scratch / STORY_DOCUMENT)
        if asked.story_told:
            await agent.tells_the_story()
        if asked.keep:
            await _kept(served)
        else:
            await _steps_taken(served, agent, asked)


def _step(written: str, readers: dict[str, StepReader]) -> Step:
    """The step a word of the command line writes.

    Raises:
        NotAStepError: if it writes none, saying what a step is, or that its picture has nowhere to go.
    """
    kind, _, detail = written.partition(WITHIN_A_STEP)
    try:
        step = readers[kind](written, detail)
    except NowhereToKeepError as error:
        raise NotAStepError(str(error)) from error
    except (KeyError, ValueError) as error:
        refusal = NOT_A_STEP.format(written=written)
        raise NotAStepError(refusal) from error
    return step


def _asked(arguments: list[str]) -> Asked:
    """What the command line asks for; one that cannot be read is refused with its usage."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--view", choices=list(VIEWS), default=STORY_VIEW)
    parser.add_argument("--theme", type=Theme, choices=list(Theme), default=Theme.LIGHT)
    parser.add_argument("--width", type=int, default=WIDTH_UNLESS_ASKED, metavar="PIXELS")
    parser.add_argument("--shots", type=Path, default=None, metavar="DIRECTORY")
    parser.add_argument("--untold", action="store_true")
    parser.add_argument("--keep", action="store_true")
    parser.add_argument("steps", nargs="*", metavar="STEP")
    read = parser.parse_args(arguments)
    if read.keep and read.steps:
        parser.error(KEPT_TAKES_NO_STEPS)
    # The steps are read last: a picture is read knowing where pictures go, wherever --shots stood among them
    readers = _step_readers(read.shots)
    try:
        steps = [_step(written, readers) for written in read.steps]
    except NotAStepError as refusal:
        parser.error(str(refusal))
    return Asked(
        view=VIEWS[read.view],
        theme=read.theme,
        width=read.width,
        story_told=not read.untold,
        keep=read.keep,
        steps=steps,
    )


def _last_written(root: Path) -> Path | None:
    """The file under a directory that was written last, or none where there is no file."""
    files = [path for path in root.rglob("*") if path.is_file()]
    return max(files, key=lambda path: path.stat().st_mtime, default=None)


def _held_to_the_page_as_it_is() -> None:
    """Hold the look to a page built since its sources were last written.

    The review serves the page as it was built, so a source changed since is not in what a look
    would see, and the line it printed would be said of a page that is no longer the one written.

    Raises:
        LookFailedError: if the look is not run where the page is, or the page is not built, or was
            built before a source of it was last written.
    """
    source = _last_written(PAGE_SOURCES)
    if source is None:
        raise LookFailedError(NO_PAGE_HERE)
    if not BUILT_PAGE.is_file():
        raise LookFailedError(NOT_BUILT)
    if source.stat().st_mtime > BUILT_PAGE.stat().st_mtime:
        failure = BUILT_BEFORE.format(source=source)
        raise LookFailedError(failure)


def main() -> int:
    asked = _asked(sys.argv[1:])
    with tempfile.TemporaryDirectory(prefix=SCRATCH_PREFIX) as scratch:
        try:
            _held_to_the_page_as_it_is()
            complete(_look(asked, Path(scratch)))
        except (LookFailedError, CommandFailedError) as failure:
            print(failure, file=sys.stderr)
            return NOT_LOOKED
    return LOOKED


if __name__ == "__main__":
    sys.exit(exit_code_of(main))
