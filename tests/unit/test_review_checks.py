"""The checks the agent reported, as the review's `ReviewChecks` keeps them: their one owner.

Each is stamped as it arrives with the round, the moment and the tree git
writes down; one reported under a name already held takes its place. Each
time the working tree changes, every check is measured against it: one with
a path changed since its tree is out of date, and so is each of its failures
in a file that changed. Every page is told the checks whole, each time they
change.
"""

import asyncio
from typing import override

from claude_review.domain.checks import Check, CheckFailure, CheckReport, CheckStatus
from claude_review.domain.page_events import ChecksChanged
from claude_review.services.review.review_checks import ReviewChecks, TreesWritten
from tests.helpers import FixedClock, RecordingPage

# When the review's clock says the checks arrive
REPORTED_AT = 1_791_000_000_000
# The tree git writes the working tree down as, while nothing changes; the one
# it writes once a file has changed; and one git can no longer read
THE_TREE = "tree-of-the-change"
TREE_EDITED = "tree-edited-since"
TREE_UNREAD = "tree-pruned-since"
SECOND_ROUND = 2
# Where the tests failed, and a file of the change no test failed in
FAILING_TEST_FILE = "tests/test_a.py"
UNTESTED_FILE = "src/b.py"

PYTEST_FAILED = CheckReport(
    name="pytest",
    status=CheckStatus.FAILED,
    summary="1 failed, 411 passed",
    failures=[CheckFailure(path=FAILING_TEST_FILE, line=42, what="test_rename", why="AssertionError")],
)
PYTEST_PASSED = CheckReport(name="pytest", status=CheckStatus.PASSED, summary="412 passed", failures=[])
RUFF_PASSED = CheckReport(name="ruff", status=CheckStatus.PASSED, summary=None, failures=[])
TY_PASSED = CheckReport(name="ty", status=CheckStatus.PASSED, summary=None, failures=[])
TY_FAILED_IN_TWO_FILES = CheckReport(
    name="ty",
    status=CheckStatus.FAILED,
    summary="2 errors",
    failures=[
        CheckFailure(path=FAILING_TEST_FILE, line=3, what="unresolved-import", why=None),
        CheckFailure(path=UNTESTED_FILE, line=9, what="invalid-return-type", why=None),
    ],
)


class TreesOfTheTest(TreesWritten):
    """A repository whose working tree git writes down as the test says, and measures as the test says.

    `tree` is None where git will not write it. A measuring is answered once
    `answer` is set, which it is unless the test holds git back.
    """

    def __init__(self) -> None:
        self.tree: str | None = THE_TREE
        self.changed: dict[str, list[str]] = {THE_TREE: []}
        self.asked = asyncio.Event()
        self.answer = asyncio.Event()
        self.answer.set()

    @override
    async def tree_as_it_stands(self) -> str | None:
        return self.tree

    @override
    async def changed_since(self, trees: list[str]) -> dict[str, list[str]]:
        self.asked.set()
        await self.answer.wait()
        return self.changed


def _checks(page: RecordingPage, trees: TreesOfTheTest) -> ReviewChecks:
    return ReviewChecks(trees, FixedClock(REPORTED_AT), page)


async def test_a_check_reported_is_held_stamped_and_current_and_every_page_is_told() -> None:
    page = RecordingPage()
    checks = _checks(page, TreesOfTheTest())

    await checks.report(PYTEST_FAILED, round_number=SECOND_ROUND)

    held = Check(report=PYTEST_FAILED, round=SECOND_ROUND, at=REPORTED_AT, tree=THE_TREE, changed_since=[])
    assert checks.held == [held]
    assert not held.out_of_date
    assert page.told == [ChecksChanged(checks=[held])]


async def test_a_check_reported_again_under_its_name_takes_its_place() -> None:
    """The list the reader reads does not reshuffle: the tests stay where they were, green now."""
    checks = _checks(RecordingPage(), TreesOfTheTest())
    await checks.report(PYTEST_FAILED, round_number=SECOND_ROUND)
    await checks.report(RUFF_PASSED, round_number=SECOND_ROUND)

    await checks.report(PYTEST_PASSED, round_number=SECOND_ROUND)

    assert [check.report for check in checks.held] == [PYTEST_PASSED, RUFF_PASSED]


async def test_a_check_a_file_changed_under_is_out_of_date() -> None:
    """A test's result hangs on the whole tree, so any file changed since may have changed it."""
    page = RecordingPage()
    trees = TreesOfTheTest()
    checks = _checks(page, trees)
    await checks.report(TY_FAILED_IN_TWO_FILES, round_number=SECOND_ROUND)

    trees.changed = {THE_TREE: [FAILING_TEST_FILE]}
    await checks.measure()

    [held] = checks.held
    assert (held.out_of_date, held.changed_since, checks.names_out_of_date) == (True, [FAILING_TEST_FILE], ["ty"])
    assert page.told[-1] == ChecksChanged(checks=[held])


async def test_measuring_checks_the_code_has_not_moved_on_from_tells_nobody() -> None:
    """The watch measures at every save: a page told nothing new each time hears noise."""
    page = RecordingPage()
    checks = _checks(page, TreesOfTheTest())
    await checks.report(PYTEST_PASSED, round_number=SECOND_ROUND)

    await checks.measure()

    assert len(page.told) == 1


async def test_a_check_nobody_can_measure_stays_out_of_date_beside_those_measured_current() -> None:
    """Git would not write its tree, or will not read it now: a reader told it is current stops looking."""
    trees = TreesOfTheTest()
    checks = _checks(RecordingPage(), trees)
    trees.tree = None
    await checks.report(PYTEST_FAILED, round_number=SECOND_ROUND)
    trees.tree = THE_TREE
    await checks.report(RUFF_PASSED, round_number=SECOND_ROUND)
    trees.tree = TREE_UNREAD
    await checks.report(TY_PASSED, round_number=SECOND_ROUND)

    await checks.measure()

    assert [(check.report.name, check.out_of_date) for check in checks.held] == [
        ("pytest", True),
        ("ruff", False),
        ("ty", True),
    ]


async def test_a_check_reported_while_a_measuring_waits_on_git_is_not_measured_by_it() -> None:
    """That measuring asked git of the trees held before it: of the one reported since, it knows nothing."""
    trees = TreesOfTheTest()
    checks = _checks(RecordingPage(), trees)
    await checks.report(PYTEST_PASSED, round_number=SECOND_ROUND)
    trees.answer.clear()
    measuring = asyncio.create_task(checks.measure())
    await trees.asked.wait()

    trees.tree = TREE_EDITED
    reporting = asyncio.create_task(checks.report(RUFF_PASSED, round_number=SECOND_ROUND))
    # A turn of the loop, in which the report would land were nothing holding it back
    await asyncio.sleep(0)
    trees.answer.set()
    await asyncio.gather(measuring, reporting)

    assert [(check.report.name, check.out_of_date) for check in checks.held] == [("pytest", False), ("ruff", False)]
