"""Serve a long change, with a story told of it, for whoever looks at the page.

A change to what the reader sees is looked at in a browser before it is
called done, and whoever reviews it looks again. Each of those looks used to
start with a script written for it: one to make a change long enough to
scroll, one to serve it, one to tell its story. This is that start, written
once. The look itself is the looker's: a person's eyes, or an agent's
browser.

It makes a repository of its own with a long change in it (`long_change.py`
says what the change is), serves the change through the review's own
command line, tells a story of it the same way, prints where the review is,
and stays until the review ends: a review ends once its page has been
closed. The repository, the story and what the review remembers about its
reader are kept in a directory of the look's own, removed as it ends: a
look writes nothing where it is run, and a fresh reader opens the page
every time.

    uv run python scripts/look.py [--untold]

It prints one line, `served` and the review's address.

`--untold` leaves the change untold: the page opens on a review that holds
no story, as every review does until its agent tells one.

Run in the repository's root. The review serves the page as it was last
built, so a look is refused when a file under `frontend/src` was written
after the build: it would be a look at an older page than the one written.
Build first, `cd frontend && pnpm build`.

Stopped from outside, by SIGTERM or at Ctrl-C, a look ends where it stands:
it stops its server and removes its directory on the way out.

Exits 0 once its review has ended; 2 at a command line it cannot read; 130
stopped from outside. It exits 1, with the reason on stderr, whenever it
could not serve: run where there is no page, or the page is not built, or
was built before a source of it was last written; git could not make the
repository, the review could not be served or did not take the story, or
one of those commands ran out of its time.
"""

import argparse
import asyncio
import contextlib
import os
import sys
import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path

from pydantic import BaseModel, ConfigDict

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

# The word the line of where the review is begins with
SERVED = "served"

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

# What is said of a review that did not say where it is
NOT_SERVED = "the review ended before it said where it is: {said}"
NOT_SERVED_IN_TIME = f"the review did not say where it is within {SERVED_WITHIN_SECONDS} seconds"

# What the look exits with: its review served until it ended, or none served. Stopped from outside, it exits as
# every script does
ENDED = 0
NOT_SERVED_AT_ALL = 1


class LookFailedError(Exception):
    """The look cannot go on: what it says is what is printed."""


class Served(BaseModel):
    """A review the look serves: where it is, and the process serving it."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    address: str
    server: Running

    def port(self) -> str:
        _, _, port = self.address.rpartition(BEFORE_THE_PORT)
        return port


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


async def _story_told(served: Served, environment: dict[str, str], document: Path) -> None:
    """Tell the story of the change as its agent does: its document handed to the review's `story` command.

    Raises:
        CommandFailedError: if the review refuses the story.
    """
    await asyncio.to_thread(document.write_text, THE_STORY.model_dump_json())
    told = await run(
        (*REVIEW, "story", "--port", served.port(), "--file", str(document)), environment, COMMAND_WITHIN_SECONDS
    )
    told.must_have_succeeded()


async def _look(scratch: Path, *, story_told: bool) -> None:
    """Serve the long change, its story told unless it is left untold, say where, and stay until it ends."""
    environment = _environment(scratch)
    await _long_change(scratch / REPOSITORY, environment)
    async with _served(scratch / REPOSITORY, environment) as served:
        if story_told:
            await _story_told(served, environment, scratch / STORY_DOCUMENT)
        print(f"{SERVED} {served.address}", flush=True)
        await served.server.ended()


def _last_written(root: Path) -> Path | None:
    """The file under a directory that was written last, or none where there is no file."""
    files = [path for path in root.rglob("*") if path.is_file()]
    return max(files, key=lambda path: path.stat().st_mtime, default=None)


def _held_to_the_page_as_it_is() -> None:
    """Hold the look to a page built since its sources were last written.

    The review serves the page as it was built, so a source changed since is not in what a look
    would see.

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
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--untold", action="store_true")
    asked = parser.parse_args(sys.argv[1:])
    with tempfile.TemporaryDirectory(prefix=SCRATCH_PREFIX) as scratch:
        try:
            _held_to_the_page_as_it_is()
            complete(_look(Path(scratch), story_told=not asked.untold))
        except (LookFailedError, CommandFailedError) as failure:
            print(failure, file=sys.stderr)
            return NOT_SERVED_AT_ALL
    return ENDED


if __name__ == "__main__":
    sys.exit(exit_code_of(main))
