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
        [--width PIXELS] [--shots DIRECTORY] STEP...
    uv run python scripts/look.py --keep

A step is one of

    press:TEST_ID        press the first element of that test id
    press:TEST_ID:NTH    press another of them, counted from 0 as Playwright counts
    key:KEY              press a key, named as Playwright names keys: j, Tab, Control+Enter
    scroll:PIXELS        scroll the reading area down by that many pixels, or up by a number below zero
    shot:NAME            keep a picture of the window as NAME.png in the directory --shots names

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

A step that cannot be taken ends the look: no element of that test id, a
key Playwright does not know, a picture with no directory to keep it in.
The step is named on stderr and the look exits 1; the steps after it are
not taken.

`--keep`, in place of steps: serve the change, tell its story, print where
the review is, and stay until the review ends. A review ends once its page
has been closed, so a kept look opens none: it is how a page is put before
a person. Stopped from outside, a look stops its server on the way out.

Elements are found by test id alone.
"""

import argparse
import asyncio
import contextlib
import os
import re
import signal
import sys
import tempfile
from abc import ABC, abstractmethod
from asyncio.subprocess import DEVNULL, PIPE, Process
from collections.abc import AsyncIterator, Iterator
from enum import StrEnum, auto
from pathlib import Path
from typing import Self, override

from commands import CommandFailedError, run
from long_change import CHANGED, COMMITTED, THE_STORY
from playwright.async_api import Error as BrowserError, Page, async_playwright
from pydantic import BaseModel, ConfigDict, Field

# The review's own command line, run in the environment the look runs in
REVIEW = (sys.executable, "-m", "claude_review")
# The port asked for to be given any free one
ANY_PORT = "0"
# How the review says where it is, on stderr, once it is served
READY_ANNOUNCEMENT = "Review ready at "
# What stands between an address and its port
BEFORE_THE_PORT = ":"
# How long the review has to say where it is, and how long to stop once told to, before it is stopped outright
SERVED_WITHIN_SECONDS = 30
STOPPED_WITHIN_SECONDS = 10

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
YES_OR_NO = {True: "yes", False: "no"}
# What a line opens with as the page opens, and a kept look's line of where its review is
OPENED = "open"
KEPT = "kept"
# What is said of a step whose page had not come to rest when it was read
STILL_MOVING = {True: ", still moving", False: ""}
# What ends a line of what the browser says went wrong: the rest is its own log
END_OF_LINE = "\n"

# What is said of a look that cannot go on
NO_PIPE = "the review was started with no pipe for what it says on stderr"
NOT_SERVED = "the review ended before it said where it is: {said}"
NOT_SERVED_IN_TIME = f"the review did not say where it is within {SERVED_WITHIN_SECONDS} seconds"
NOT_TAKEN = "{step} could not be taken: {why}"
NOWHERE_TO_KEEP_IT = "{step} could not be taken: name a directory to keep pictures in with --shots"
# What is said of what the command line cannot be read as
NOT_A_STEP = "{written} is not a step: a step is press:TEST_ID, press:TEST_ID:NTH, key:KEY, scroll:PIXELS or shot:NAME"
KEPT_TAKES_NO_STEPS = "--keep takes no steps: a kept look opens no page to take them on"

# What the look exits with: looked, or kept until its review ended; ended at a step or before the
# page opened; stopped from outside, as a shell says of a program stopped at Ctrl-C
LOOKED = 0
NOT_LOOKED = 1
STOPPED_FROM_OUTSIDE = 130

FROZEN = ConfigDict(frozen=True)


class LookFailedError(Exception):
    """The look cannot go on: what it says is what is printed."""


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


class Step(BaseModel, ABC):
    """One thing done on the page, kept as it was written on the command line."""

    model_config = FROZEN

    written: str

    @classmethod
    @abstractmethod
    def read(cls, written: str, detail: str) -> Self:
        """The step a word of the command line writes, from what stands after its kind.

        Raises:
            ValueError: if what stands there is not what a step of this kind takes.
        """

    @abstractmethod
    async def take(self, page: Page, shots: Path | None) -> None:
        """Do it on the page; a picture it keeps goes to the directory for them, where there is one."""


class Press(Step):
    """A press on an element, found by its test id and its place among those of that id."""

    test_id: str = Field(min_length=1)
    nth: int = Field(ge=0)

    @classmethod
    @override
    def read(cls, written: str, detail: str) -> Self:
        test_id, _, nth = detail.partition(WITHIN_A_STEP)
        return cls(written=written, test_id=test_id, nth=int(nth or THE_FIRST))

    @override
    async def take(self, page: Page, shots: Path | None) -> None:
        await page.get_by_test_id(self.test_id).nth(self.nth).click()


class Key(Step):
    """A key pressed on whatever holds the keyboard."""

    key: str = Field(min_length=1)

    @classmethod
    @override
    def read(cls, written: str, detail: str) -> Self:
        return cls(written=written, key=detail)

    @override
    async def take(self, page: Page, shots: Path | None) -> None:
        await page.keyboard.press(self.key)


class Scroll(Step):
    """The reading area scrolled down by a number of pixels."""

    pixels: int

    @classmethod
    @override
    def read(cls, written: str, detail: str) -> Self:
        return cls(written=written, pixels=int(detail))

    @override
    async def take(self, page: Page, shots: Path | None) -> None:
        await page.get_by_test_id(READING_AREA).evaluate(SCROLLED_DOWN_BY, self.pixels)


class Shot(Step):
    """A picture of the window, kept under a name."""

    name: str = Field(min_length=1)

    @classmethod
    @override
    def read(cls, written: str, detail: str) -> Self:
        return cls(written=written, name=detail)

    @override
    async def take(self, page: Page, shots: Path | None) -> None:
        if shots is None:
            failure = NOWHERE_TO_KEEP_IT.format(step=self.written)
            raise LookFailedError(failure)
        await page.screenshot(path=shots / f"{self.name}{PICTURE_SUFFIX}")


# What a step's kind is written as, before what it is done to
STEP_KINDS: dict[str, type[Step]] = {"press": Press, "key": Key, "scroll": Scroll, "shot": Shot}


class Asked(BaseModel):
    """What a look was asked for on the command line."""

    model_config = FROZEN

    view: View
    theme: Theme
    width: int
    shots: Path | None
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

    def said_after(self, step: str) -> str:
        """The one line of it, each value under its name, after the step that led to it."""
        return BETWEEN_VALUES.join(
            [
                step,
                f"page: {self.page}",
                f"area: {self.area}",
                f"keyboard: {self.keyboard}",
                f"bar: {_listed(self.bar)}",
                f"read: {_listed(self.read)}",
                f"reading: {_listed(self.being_read)}",
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
    server: Process

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
        (await run(("git", "-C", str(repository), *arguments), environment)).must_have_succeeded()
    await asyncio.to_thread(_write, repository, CHANGED)


def _errors_of(server: Process) -> asyncio.StreamReader:
    """Where a review started with a pipe for its errors says them."""
    if server.stderr is None:
        raise LookFailedError(NO_PIPE)
    return server.stderr


async def _address_announced(errors: asyncio.StreamReader) -> str:
    """Where the review says it is, as whoever starts one in the background reads it: off its stderr.

    Raises:
        LookFailedError: if the review ends without saying, with what it said in its place.
    """
    said = []
    while line := (await errors.readline()).decode():
        if line.startswith(READY_ANNOUNCEMENT):
            return line.removeprefix(READY_ANNOUNCEMENT).strip()
        said.append(line.strip())
    failure = NOT_SERVED.format(said=" ".join(said))
    raise LookFailedError(failure)


async def _address_of(server: Process) -> str:
    """Where a review just started is served, once it says.

    Raises:
        LookFailedError: if it has not said in the time a review takes to start many times over.
    """
    try:
        return await asyncio.wait_for(_address_announced(_errors_of(server)), timeout=SERVED_WITHIN_SECONDS)
    except TimeoutError as error:
        raise LookFailedError(NOT_SERVED_IN_TIME) from error


async def _stopped(server: Process) -> None:
    """Stop a server by its pid and wait until it is gone: told to first, then stopped outright."""
    with contextlib.suppress(ProcessLookupError):
        server.terminate()
    try:
        await asyncio.wait_for(server.wait(), timeout=STOPPED_WITHIN_SECONDS)
    except TimeoutError:
        with contextlib.suppress(ProcessLookupError):
            server.kill()
        await server.wait()


@contextlib.asynccontextmanager
async def _served(repository: Path, environment: dict[str, str]) -> AsyncIterator[Served]:
    """Serve the review of the repository's change through the review's own command line, while the block runs.

    Raises:
        LookFailedError: if the review does not say where it is.
    """
    server = await asyncio.create_subprocess_exec(
        *REVIEW, "diff", "--port", ANY_PORT, "--no-open", str(repository), env=environment, stdout=DEVNULL, stderr=PIPE
    )
    try:
        yield Served(address=await _address_of(server), server=server)
    finally:
        await _stopped(server)


async def _story_told(served: Served, document: Path, environment: dict[str, str]) -> None:
    """Tell the story of the change, as an agent tells one: its document handed to the `story` command.

    Raises:
        CommandFailedError: if the review refuses the story.
    """
    await asyncio.to_thread(document.write_text, THE_STORY.model_dump_json())
    told = await run((*REVIEW, "story", "--port", served.port(), "--file", str(document)), environment)
    told.must_have_succeeded()


@contextlib.asynccontextmanager
async def _window(asked: Asked) -> AsyncIterator[Page]:
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
def _ending_the_look_at(step: str) -> Iterator[None]:
    """End the look, naming the step, if the browser cannot do what the block asks of it."""
    try:
        yield
    except BrowserError as error:
        why, _, _ = error.message.partition(END_OF_LINE)
        failure = NOT_TAKEN.format(step=step, why=why)
        raise LookFailedError(failure) from error


async def _opened(page: Page, address: str, view: View) -> None:
    """Open the review as a reader new to it would, put the offer of a tour away, and read it the way asked."""
    await page.goto(address)
    await page.get_by_test_id(TOUR_NOT_NOW).click()
    await page.get_by_test_id(view.switch).click()
    await page.get_by_test_id(view.area).wait_for()


async def _seen(page: Page) -> Seen:
    """What the page says now."""
    return Seen(
        page=PageSeen.model_validate(await page.evaluate(THE_PAGE_ITSELF)),
        area=AreaSeen.model_validate(await page.get_by_test_id(READING_AREA).evaluate(THE_READING_AREA)),
        keyboard=KeyboardSeen.model_validate(await page.evaluate(THE_KEYBOARDS_HOLDER)),
        bar=await page.get_by_test_id(CHAPTER_BAR).all_inner_texts(),
        read=await page.get_by_test_id(PART_ENTRY).filter(has=page.get_by_test_id(READ_MARK)).evaluate_all(THEIR_NAMES),
        being_read=await page.get_by_test_id(ANY_ENTRY).evaluate_all(NAMES_OF_THOSE_BEING_READ),
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


async def _steps_taken(served: Served, asked: Asked) -> None:
    """Open the review in a window, take each step, and print what is there as it opens and after each."""
    async with _window(asked) as page:
        with _ending_the_look_at(OPENED):
            await _opened(page, served.address, asked.view)
            print((await _at_rest(page)).said_after(f"{OPENED} {served.address}"), flush=True)
        for step in asked.steps:
            with _ending_the_look_at(step.written):
                await step.take(page, asked.shots)
                print((await _at_rest(page)).said_after(step.written), flush=True)


async def _kept(served: Served) -> None:
    """Say where the review is, and stay until it ends."""
    print(f"{KEPT} {served.address}", flush=True)
    await served.server.wait()


async def _look(asked: Asked, scratch: Path) -> None:
    """Serve the long change with its story told, and take the steps on its page, or keep it for a reader."""
    environment = _environment(scratch)
    await _long_change(scratch / REPOSITORY, environment)
    async with _served(scratch / REPOSITORY, environment) as served:
        await _story_told(served, scratch / STORY_DOCUMENT, environment)
        if asked.keep:
            await _kept(served)
        else:
            await _steps_taken(served, asked)


def _step(written: str) -> Step:
    """The step a word of the command line writes.

    Raises:
        argparse.ArgumentTypeError: if it writes none, for the command line to be refused with.
    """
    kind, _, detail = written.partition(WITHIN_A_STEP)
    try:
        step = STEP_KINDS[kind].read(written, detail)
    except (KeyError, ValueError) as error:
        refusal = NOT_A_STEP.format(written=written)
        raise argparse.ArgumentTypeError(refusal) from error
    return step


def _asked(arguments: list[str]) -> Asked:
    """What the command line asks for; one that cannot be read is refused with its usage."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--view", choices=list(VIEWS), default=STORY_VIEW)
    parser.add_argument("--theme", type=Theme, choices=list(Theme), default=Theme.LIGHT)
    parser.add_argument("--width", type=int, default=WIDTH_UNLESS_ASKED, metavar="PIXELS")
    parser.add_argument("--shots", type=Path, default=None, metavar="DIRECTORY")
    parser.add_argument("--keep", action="store_true")
    parser.add_argument("steps", nargs="*", type=_step, metavar="STEP")
    read = parser.parse_args(arguments)
    if read.keep and read.steps:
        parser.error(KEPT_TAKES_NO_STEPS)
    return Asked(
        view=VIEWS[read.view], theme=read.theme, width=read.width, shots=read.shots, keep=read.keep, steps=read.steps
    )


def main() -> int:
    asked = _asked(sys.argv[1:])
    # Stopped from outside, the look leaves as it does at Ctrl-C: its server stopped on the way out
    signal.signal(signal.SIGTERM, signal.default_int_handler)
    with tempfile.TemporaryDirectory(prefix=SCRATCH_PREFIX) as scratch:
        try:
            asyncio.run(_look(asked, Path(scratch)))
        except (LookFailedError, CommandFailedError) as failure:
            print(failure, file=sys.stderr)
            return NOT_LOOKED
        except KeyboardInterrupt:
            return STOPPED_FROM_OUTSIDE
    return LOOKED


if __name__ == "__main__":
    sys.exit(main())
