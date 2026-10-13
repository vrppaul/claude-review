"""`scripts/break_lines.py`: lines of the page broken on purpose, in a copy of it, run as it is run.

Each test runs the script as a process, in a repository of its own. That
repository's `frontend/` asks for what the page asks for, by the page's own
`package.json` and lockfile, so pnpm installs it from its store without the
network; what it holds is a module of three functions and a test for two of
them. The script is held to what vitest really reports, and to no line of
the page.

It is here, among the browser tests, though it opens no browser: this is
the directory CI runs with pnpm and its store at hand.
"""

import asyncio
import contextlib
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from pydantic import BaseModel, ConfigDict

from tests.e2e.browsers_loop import BROWSERS_LOOP

BREAK_LINES = Path(__file__).parents[2] / "scripts" / "break_lines.py"
# The page, for what it asks pnpm for
PAGE = Path(__file__).parents[2] / "frontend"
ASKED_OF_PNPM = ("package.json", "pnpm-lock.yaml")
# How long a run may take before it is cut: several times what one takes
RUN_SECONDS = 120
# What the script exits with: it broke the lines and ran the tests, or it refused what it was asked
RAN = 0
REFUSED = 1

# Where the document of what to break is written, and the directory lines are broken in a copy of
ASKED = "breaks.json"
FRONTEND = "frontend"
MODULE = "src/sums.ts"
TESTS = "tests/sums.test.ts"
# The configuration vitest reads in place of the page's: it names the tests, and nothing else
VITE_CONFIG = """\
import { defineConfig } from 'vitest/config';

export default defineConfig({ test: { include: ['tests/**/*.test.ts'] } });
"""
# Three functions: a test holds the first two, and nothing holds the third
THE_MODULE = """\
export function sum(left: number, right: number): number {
	return left + right;
}

export function difference(left: number, right: number): number {
	return left - right;
}

export function product(left: number, right: number): number {
	return left * right;
}
"""
THE_TESTS = """\
import { expect, test } from 'vitest';
import { difference, sum } from '../src/sums';

test('a sum adds', () => {
	expect(sum(2, 3)).toBe(5);
});

test('a difference takes away', () => {
	expect(difference(5, 3)).toBe(2);
});
"""
# What each of the two tests is said to be when it fails, and what is said of the tests as a whole
THE_SUM_FAILED = f"failed: {TESTS} > a sum adds"
THE_DIFFERENCE_FAILED = f"failed: {TESTS} > a difference takes away"
ONE_OF_TWO_FAILED = "1 of 2 tests failed"
NONE_FAILED_OF_NONE = "0 of 0 tests failed"


class Ran(BaseModel):
    """A run of the script: what it exited with, the lines it printed, and what it said of refusing."""

    model_config = ConfigDict(frozen=True)

    exit_code: int
    lines: list[str]
    refusal: str


class Refusal(BaseModel):
    """A document the script refuses: what is wrong with it, the document, and what is said of it."""

    model_config = ConfigDict(frozen=True)

    what: str
    document: str
    said: str


# The documents, each written by hand as whoever breaks lines writes one. The script holds a document
# to the fields it has, so a field misspelt here is refused there, not passed over.
# Two lines broken: the sum, which a test holds, and the product, which nothing holds
TWO_LINES_BROKEN = """\
{"tests": ["tests/sums.test.ts"],
 "breaks": [{"name": "a sum that takes away", "file": "src/sums.ts", "old": "left + right", "new": "left - right"},
            {"name": "a product that divides", "file": "src/sums.ts", "old": "left * right", "new": "left / right"}]}
"""
# A break that leaves the module unreadable, and with it the test file that imports it
A_MODULE_LEFT_UNREADABLE = """\
{"tests": ["tests/sums.test.ts"],
 "breaks": [{"name": "half a sum", "file": "src/sums.ts", "old": "return left + right;", "new": "return left +;"}]}
"""
# Lines to break named by a field the document does not have
A_FIELD_MISSPELT = '{"tests": ["tests/sums.test.ts"], "breaks": [], "braeks": []}'

REFUSALS = [
    Refusal(
        what="a text that stands three times",
        document="""\
{"tests": ["tests/sums.test.ts"],
 "breaks": [{"name": "any return", "file": "src/sums.ts", "old": "return left", "new": "return 0"}]}
""",
        said=f"any return: its text stands 3 times in {MODULE}, and a break names a text that stands there once",
    ),
    Refusal(
        what="a text that stands nowhere",
        document="""\
{"tests": ["tests/sums.test.ts"],
 "breaks": [{"name": "a remainder", "file": "src/sums.ts", "old": "left % right", "new": "0"}]}
""",
        said=f"a remainder: its text stands 0 times in {MODULE}, and a break names a text that stands there once",
    ),
    Refusal(
        what="a file that is not there",
        document="""\
{"tests": ["tests/sums.test.ts"],
 "breaks": [{"name": "nowhere", "file": "src/none.ts", "old": "left", "new": "right"}]}
""",
        said=f"nowhere: there is no src/none.ts in {FRONTEND}/",
    ),
    Refusal(
        what="a file outside the page",
        document="""\
{"tests": ["tests/sums.test.ts"],
 "breaks": [{"name": "the way out", "file": "../breaks.json", "old": "tests", "new": "nothing"}]}
""",
        said=f"the way out: there is no ../breaks.json in {FRONTEND}/",
    ),
    Refusal(
        what="a test file that is not there",
        document="""\
{"tests": ["tests/none.test.ts"],
 "breaks": [{"name": "a sum that takes away", "file": "src/sums.ts", "old": "left + right", "new": "left - right"}]}
""",
        said=f"there is no test file tests/none.test.ts in {FRONTEND}/",
    ),
]


def _repository(root: Path) -> Path:
    """A repository whose page is the module and its tests, asking pnpm for what the real page asks for."""
    frontend = root / FRONTEND
    (frontend / MODULE).parent.mkdir(parents=True)
    (frontend / TESTS).parent.mkdir(parents=True)
    (frontend / MODULE).write_text(THE_MODULE)
    (frontend / TESTS).write_text(THE_TESTS)
    (frontend / "vite.config.ts").write_text(VITE_CONFIG)
    for asked_for in ASKED_OF_PNPM:
        (frontend / asked_for).write_bytes((PAGE / asked_for).read_bytes())
    return root


async def _break_lines(repository: Path, document: str) -> Ran:
    """Run the script in the repository's root on a document of what to break, as it is run from a shell."""
    (repository / ASKED).write_text(document)
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        str(BREAK_LINES),
        ASKED,
        cwd=repository,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        printed, refusal = await asyncio.wait_for(process.communicate(), timeout=RUN_SECONDS)
    finally:
        # A run cut short is not left running; one that ended is no longer there to stop
        with contextlib.suppress(ProcessLookupError):
            process.kill()
    return Ran(exit_code=process.returncode, lines=printed.decode().splitlines(), refusal=refusal.decode())


class BrokenRun(BaseModel):
    """The one run most tests read: the repository it was made in, and what the script printed."""

    model_config = ConfigDict(frozen=True)

    repository: Path
    ran: Ran


@pytest_asyncio.fixture(scope="module", loop_scope=BROWSERS_LOOP)
async def two_lines_broken(tmp_path_factory: pytest.TempPathFactory) -> BrokenRun:
    """One run with two lines broken: one a test holds, and one nothing holds."""
    repository = _repository(tmp_path_factory.mktemp("broken"))
    ran = await _break_lines(repository, TWO_LINES_BROKEN)
    assert ran.exit_code == RAN, ran.refusal
    return BrokenRun(repository=repository, ran=ran)


async def test_a_broken_line_is_named_by_the_test_that_holds_it(two_lines_broken: BrokenRun) -> None:
    assert THE_SUM_FAILED in two_lines_broken.ran.lines


async def test_a_test_whose_lines_stand_is_not_named_and_a_line_nothing_holds_fails_nothing(
    two_lines_broken: BrokenRun,
) -> None:
    """Two lines were broken and one test failed: the product, which no test holds, went unnoticed."""
    assert THE_DIFFERENCE_FAILED not in two_lines_broken.ran.lines
    assert ONE_OF_TWO_FAILED in two_lines_broken.ran.lines


async def test_every_line_broken_is_said_by_its_name_and_its_file(two_lines_broken: BrokenRun) -> None:
    assert f"broke a sum that takes away: {MODULE}" in two_lines_broken.ran.lines
    assert f"broke a product that divides: {MODULE}" in two_lines_broken.ran.lines


async def test_the_working_tree_is_as_it_was_once_its_lines_were_broken(two_lines_broken: BrokenRun) -> None:
    """The lines are broken in a copy, and what pnpm installs for the copy stays with it."""
    frontend = two_lines_broken.repository / FRONTEND

    assert (frontend / MODULE).read_text() == THE_MODULE
    assert sorted(kept.name for kept in frontend.iterdir()) == sorted(
        [*ASKED_OF_PNPM, "src", "tests", "vite.config.ts"]
    )


async def test_a_test_file_that_can_no_longer_be_read_is_said_to_be_one_that_could_not_be_run(tmp_path: Path) -> None:
    ran = await _break_lines(_repository(tmp_path), A_MODULE_LEFT_UNREADABLE)

    assert ran.exit_code == RAN, ran.refusal
    assert any(line.startswith(f"could not run {TESTS}: ") for line in ran.lines)
    assert NONE_FAILED_OF_NONE in ran.lines


@pytest.mark.parametrize("refused", REFUSALS, ids=lambda refused: refused.what)
async def test_what_cannot_be_broken_or_run_is_refused_by_name_and_nothing_is_run(
    tmp_path: Path, refused: Refusal
) -> None:
    ran = await _break_lines(_repository(tmp_path), refused.document)

    assert ran.exit_code == REFUSED
    assert ran.refusal.strip() == refused.said
    assert ran.lines == []


async def test_a_document_with_a_field_it_does_not_have_is_refused_and_nothing_is_run(tmp_path: Path) -> None:
    ran = await _break_lines(_repository(tmp_path), A_FIELD_MISSPELT)

    assert ran.exit_code == REFUSED
    assert ran.refusal.startswith(f"{ASKED} is not a document of lines to break: ")
    assert "braeks" in ran.refusal
    assert ran.lines == []
