"""Break lines of the page on purpose, in a copy of it, and name the tests that fail.

For whoever reviews a change to the page and asks which of its lines no
test holds. A test seen failing before its code existed holds that code;
of a line nobody saw fail, the only way to know is to break it and run the
tests. Done by hand that is an edit of the working tree, a start of vitest
and an edit back for every line, and a run cut short leaves the tree
broken. Here every line is broken at once, in a copy, and vitest starts
once.

    uv run python scripts/break_lines.py BREAKS.json

Run in the repository's root. The document names the test files to run and
the lines to break, every path written from `frontend/`:

    {"tests": ["tests/anchors.test.ts"],
     "breaks": [{"name": "lines named as one line",
                 "file": "src/lib/anchors/line-label.ts",
                 "old": "'Removed lines' : 'Lines'",
                 "new": "'Removed line' : 'Line'"}]}

A break's `old` stands in its file exactly once, as the breaks before it in
the document leave the file: a text that stands twice would break a line
nobody meant.

`frontend/` is copied to a temporary directory without `node_modules`, and
pnpm installs the copy's own there from its store, without the network:
vite serves nothing from outside its root, so the copy cannot borrow the
working tree's. The lines are broken in the copy and never in the working
tree, so a run cut short leaves nothing broken; and the copy is removed as
the run ends, also when the run is stopped from outside, by SIGTERM or at
Ctrl-C, with pnpm or vitest stopped first. pnpm and vitest each have a
limit, and one that runs out of it is stopped and said to have failed.

It prints `broke NAME: FILE` for every break, once the copy is broken and
before vitest starts; then `failed: FILE > TEST` for every test that
failed; `could not run FILE: why` for a test file vitest could not read, as
when a break leaves a module it imports unreadable; and how many of the
tests failed.

Its limit: every break is in place for the one run. A test that fails says
that some break reached it, not which one; and a break whose effect another
break undoes or hides is not told from one no test holds. Breaks that must
be told apart go in runs of their own.

The page's tests only.

Exits 0 having broken the lines and run the tests, whatever failed; 1
having refused the document or been unable to run, with the reason on
stderr and nothing copied for a document refused; 2 at a command line it
cannot read; 130 stopped from outside.
"""

import argparse
import asyncio
import os
import shutil
import sys
import tempfile
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from commands import STOPPED_FROM_OUTSIDE, CommandFailedError, StoppedError, complete, run

# The page, from the repository's root, and the directory of what pnpm installed for it
FRONTEND = Path("frontend")
INSTALLED = "node_modules"
# What the copy and vitest's report are called in the run's own directory
COPY = "frontend"
REPORT = "report.json"
SCRATCH_PREFIX = "claude-review-break-lines-"

# How long pnpm has to install for the copy, and vitest to run the tests named: many times what
# either takes, the whole of the page's tests being run in twenty seconds
INSTALLED_WITHIN_SECONDS = 120
TESTS_RUN_WITHIN_SECONDS = 600

# How many times a break's text stands in its file
ONCE = 1
# What vitest says of a test, or of a test file, that failed
FAILED = "failed"
# What ends the first line of what vitest says went wrong with a file: the rest is where in the code
END_OF_LINE = "\n"

# What is printed of a run
BROKE = "broke {name}: {file}"
TEST_FAILED = "failed: {file} > {test}"
COULD_NOT_RUN = "could not run {file}: {why}"
HOW_MANY_FAILED = "{failed} of {total} tests failed"

# What is said of a document that is refused
NOT_A_DOCUMENT = "{document} is not a document of lines to break: {why}"
NO_SUCH_FILE = f"{{name}}: there is no {{file}} in {FRONTEND}/"
NO_SUCH_TEST_FILE = f"there is no test file {{file}} in {FRONTEND}/"
NOT_ONCE = "{name}: its text stands {stands} times in {file}, and a break names a text that stands there once"
# And of a run vitest left no report of
NO_REPORT = "vitest left no report of its run: {said}"

# What the script exits with
RAN = 0
REFUSED = 1

FROZEN = ConfigDict(frozen=True)
# A document is held to the fields it has: a misspelt one is refused, not passed over
AS_WRITTEN = ConfigDict(frozen=True, extra="forbid")


class RefusedError(Exception):
    """The lines cannot be broken or the tests run as asked: what the error says is what is printed."""


class Break(BaseModel):
    """A line to break: what the break is called, its file, the text that stands there once, and what replaces it."""

    model_config = AS_WRITTEN

    name: str
    file: str
    old: str = Field(min_length=1)
    new: str


class Asked(BaseModel):
    """The document: the test files to run, and the lines to break before they are."""

    model_config = AS_WRITTEN

    tests: list[str] = Field(min_length=1)
    breaks: list[Break]


class TestReported(BaseModel):
    """A test as vitest reports it: its full name, and how it ended."""

    model_config = FROZEN

    full_name: str = Field(alias="fullName")
    status: str


class FileReported(BaseModel):
    """A test file as vitest reports it: where it is, how it ended, what went wrong with it, and its tests."""

    model_config = FROZEN

    name: Path
    status: str
    message: str
    tests: list[TestReported] = Field(alias="assertionResults")

    def failed_tests(self) -> list[TestReported]:
        return [test for test in self.tests if test.status == FAILED]

    def could_not_run(self) -> bool:
        """Whether the file itself failed: it failed, and none of its tests is what failed."""
        return self.status == FAILED and not self.failed_tests()


class Report(BaseModel):
    """What vitest says of a run: how many tests it ran, how many failed, and each test file."""

    model_config = FROZEN

    total: int = Field(alias="numTotalTests")
    failed: int = Field(alias="numFailedTests")
    files: list[FileReported] = Field(alias="testResults")


def _asked(document: Path) -> Asked:
    """What a document asks to be broken and run.

    Raises:
        RefusedError: if it cannot be read as such a document, with what is wrong with it.
    """
    try:
        asked = Asked.model_validate_json(document.read_bytes())
    except (OSError, ValidationError) as error:
        refusal = NOT_A_DOCUMENT.format(document=document, why=error)
        raise RefusedError(refusal) from error
    return asked


def _is_a_file_of(frontend: Path, written: str) -> bool:
    """Whether a path names a file inside the page: one that climbs out of it names nothing there."""
    named = (frontend / written).resolve()
    return named.is_relative_to(frontend.resolve()) and named.is_file()


def _held_to_its_tests(frontend: Path, tests: list[str]) -> None:
    """Hold the document to test files that are there: vitest runs what it finds and says nothing of the rest.

    Raises:
        RefusedError: at the first that is not.
    """
    for written in tests:
        if not _is_a_file_of(frontend, written):
            refusal = NO_SUCH_TEST_FILE.format(file=written)
            raise RefusedError(refusal)


def _broken(frontend: Path, breaks: list[Break]) -> dict[str, str]:
    """Each file the breaks touch, by its path, as it reads with every break of it made.

    Raises:
        RefusedError: at the first break whose file is not there, or whose text does not stand in it once.
    """
    texts: dict[str, str] = {}
    for made in breaks:
        if not _is_a_file_of(frontend, made.file):
            refusal = NO_SUCH_FILE.format(name=made.name, file=made.file)
            raise RefusedError(refusal)
        text = texts[made.file] if made.file in texts else (frontend / made.file).read_text()
        stands = text.count(made.old)
        if stands != ONCE:
            refusal = NOT_ONCE.format(name=made.name, stands=stands, file=made.file)
            raise RefusedError(refusal)
        texts[made.file] = text.replace(made.old, made.new)
    return texts


def _write(root: Path, texts: dict[str, str]) -> None:
    """Write each text over the file of its path under the root."""
    for path, text in texts.items():
        (root / path).write_text(text)


async def _copied(frontend: Path, copy: Path) -> None:
    """Copy the page, and install for the copy what the page asks pnpm for, from pnpm's store alone.

    Raises:
        CommandFailedError: if pnpm cannot, as when its store does not hold what the lockfile names.
    """
    await asyncio.to_thread(shutil.copytree, frontend, copy, symlinks=True, ignore=shutil.ignore_patterns(INSTALLED))
    install = ("pnpm", "--dir", str(copy), "install", "--frozen-lockfile", "--offline")
    installed = await run(install, os.environ, INSTALLED_WITHIN_SECONDS)
    installed.must_have_succeeded()


async def _reported(copy: Path, tests: list[str], report: Path) -> Report:
    """Start vitest once in the copy on the test files named, and read its report.

    Raises:
        RefusedError: if it left none, with what it printed in its place.
    """
    command = ("pnpm", "--dir", str(copy), "exec", "vitest", "run", "--reporter=json", f"--outputFile={report}")
    ran = await run((*command, *tests), os.environ, TESTS_RUN_WITHIN_SECONDS)
    try:
        written = await asyncio.to_thread(report.read_bytes)
    except FileNotFoundError as error:
        refusal = NO_REPORT.format(said=ran.said)
        raise RefusedError(refusal) from error
    return Report.model_validate_json(written)


async def _run_broken(frontend: Path, asked: Asked, texts: dict[str, str], scratch: Path) -> Report:
    """Break the lines in a copy of the page, and say what vitest reports of the tests run there."""
    copy = scratch / COPY
    await _copied(frontend, copy)
    await asyncio.to_thread(_write, copy, texts)
    for made in asked.breaks:
        print(BROKE.format(name=made.name, file=made.file), flush=True)
    return await _reported(copy, asked.tests, scratch / REPORT)


def _said_of(file: FileReported, copy: Path) -> list[str]:
    """What is printed of one test file: that it could not be run, or each of its tests that failed."""
    written = file.name.relative_to(copy)
    if file.could_not_run():
        why, _, _ = file.message.partition(END_OF_LINE)
        return [COULD_NOT_RUN.format(file=written, why=why)]
    return [TEST_FAILED.format(file=written, test=test.full_name) for test in file.failed_tests()]


def _said(report: Report, copy: Path) -> list[str]:
    """Every line printed of what vitest reports: what failed, and how many of the tests did."""
    return [
        *(line for file in report.files for line in _said_of(file, copy)),
        HOW_MANY_FAILED.format(failed=report.failed, total=report.total),
    ]


def _broken_and_run(document: Path) -> list[str]:
    """What is printed of breaking the lines a document names and running its tests.

    Raises:
        RefusedError: if the document is refused, before anything is copied, or vitest reports nothing.
        CommandFailedError: if pnpm cannot install for the copy, or either command runs out of time.
        StoppedError: if the run is stopped from outside; the copy is removed on the way out.
    """
    frontend = Path.cwd() / FRONTEND
    asked = _asked(document)
    _held_to_its_tests(frontend, asked.tests)
    texts = _broken(frontend, asked.breaks)
    with tempfile.TemporaryDirectory(prefix=SCRATCH_PREFIX) as scratch:
        # vitest says where a test file is by the path it really has, whatever links lead to the directory
        run_in = Path(scratch).resolve()
        report = complete(_run_broken(frontend, asked, texts, run_in))
        return _said(report, run_in / COPY)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("document", type=Path, metavar="BREAKS.json")
    try:
        said = _broken_and_run(parser.parse_args().document)
    except (RefusedError, CommandFailedError) as refusal:
        print(refusal, file=sys.stderr)
        return REFUSED
    except StoppedError:
        return STOPPED_FROM_OUTSIDE
    for line in said:
        print(line)
    return RAN


if __name__ == "__main__":
    sys.exit(main())
