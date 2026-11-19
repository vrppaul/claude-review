"""The checks the agent reported, as the review's `ReviewChecks` keeps them: their one owner.

Each is stamped as it arrives with the round, the moment and the tree git
writes down; one reported under a name already held takes its place. Each
time the working tree changes, every check is measured against it: one with
a path changed since its tree is out of date, and so is each of its failures
in a file that changed. Every page is told the checks whole, each time they
change.
"""

from typing import override

from claude_review.domain.checks import Check, CheckFailure, CheckReport, CheckStatus
from claude_review.domain.page_events import ChecksChanged
from claude_review.services.review.review_checks import ReviewChecks, TreesWritten
from tests.helpers import FixedClock, RecordingPage

# When the review's clock says the checks arrive
REPORTED_AT = 1_791_000_000_000
# The tree git writes the working tree down as, while nothing changes
THE_TREE = "tree-of-the-change"
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
TY_FAILED_IN_TWO_FILES = CheckReport(
    name="ty",
    status=CheckStatus.FAILED,
    summary="2 errors",
    failures=[
        CheckFailure(path=FAILING_TEST_FILE, line=3, what="unresolved-import", why=None),
        CheckFailure(path=UNTESTED_FILE, line=9, what="invalid-return-type", why=None),
    ],
)


class TreeWrittenAs(TreesWritten):
    """A repository whose working tree git writes down as one tree, or will not write at all.

    What has changed since each tree is the test's to say, as the working tree moves.
    """

    def __init__(self, tree: str | None) -> None:
        self._tree = tree
        self.changed: dict[str, list[str]] = {THE_TREE: []}

    @override
    async def tree_as_it_stands(self) -> str | None:
        return self._tree

    @override
    async def changed_since(self, trees: list[str]) -> dict[str, list[str]]:
        return self.changed


def _checks(page: RecordingPage, trees: TreeWrittenAs) -> ReviewChecks:
    return ReviewChecks(trees, FixedClock(REPORTED_AT), page)


async def test_a_check_reported_is_held_stamped_and_current_and_every_page_is_told() -> None:
    page = RecordingPage()
    checks = _checks(page, TreeWrittenAs(THE_TREE))

    await checks.report(PYTEST_FAILED, round_number=SECOND_ROUND)

    held = Check(
        name="pytest",
        status=CheckStatus.FAILED,
        summary="1 failed, 411 passed",
        failures=PYTEST_FAILED.failures,
        round=SECOND_ROUND,
        at=REPORTED_AT,
        tree=THE_TREE,
        changed_since=[],
    )
    assert checks.held == [held]
    assert not held.out_of_date
    assert page.told == [ChecksChanged(checks=[held])]


async def test_a_check_reported_again_under_its_name_takes_its_place() -> None:
    """The list the reader reads does not reshuffle: the tests stay where they were, green now."""
    checks = _checks(RecordingPage(), TreeWrittenAs(THE_TREE))
    await checks.report(PYTEST_FAILED, round_number=SECOND_ROUND)
    await checks.report(RUFF_PASSED, round_number=SECOND_ROUND)

    await checks.report(PYTEST_PASSED, round_number=SECOND_ROUND)

    assert [(check.name, check.status) for check in checks.held] == [
        ("pytest", CheckStatus.PASSED),
        ("ruff", CheckStatus.PASSED),
    ]


async def test_a_check_a_file_changed_under_is_out_of_date_and_so_is_each_failure_in_that_file() -> None:
    """A failure in a file nobody touched since still stands; one in a file edited since may be fixed."""
    page = RecordingPage()
    trees = TreeWrittenAs(THE_TREE)
    checks = _checks(page, trees)
    await checks.report(TY_FAILED_IN_TWO_FILES, round_number=SECOND_ROUND)

    trees.changed = {THE_TREE: [FAILING_TEST_FILE]}
    await checks.measure()

    [held] = checks.held
    assert (held.out_of_date, held.changed_since, checks.names_out_of_date) == (True, [FAILING_TEST_FILE], ["ty"])
    assert [held.failure_out_of_date(failure) for failure in held.failures] == [True, False]
    assert page.told[-1] == ChecksChanged(checks=[held])


async def test_measuring_checks_the_code_has_not_moved_on_from_tells_nobody() -> None:
    """The watch measures at every save: a page told nothing new each time hears noise."""
    page = RecordingPage()
    checks = _checks(page, TreeWrittenAs(THE_TREE))
    await checks.report(PYTEST_PASSED, round_number=SECOND_ROUND)

    await checks.measure()

    assert len(page.told) == 1


async def test_a_check_nobody_can_measure_is_out_of_date_and_every_failure_with_it() -> None:
    """Git would not write its tree, or will not read it now: a reader told it is current stops looking."""
    unwritten = _checks(RecordingPage(), TreeWrittenAs(None))
    await unwritten.report(PYTEST_FAILED, round_number=SECOND_ROUND)
    unread_trees = TreeWrittenAs(THE_TREE)
    unread = _checks(RecordingPage(), unread_trees)
    await unread.report(PYTEST_FAILED, round_number=SECOND_ROUND)

    unread_trees.changed = {}
    await unread.measure()

    held = [*unwritten.held, *unread.held]
    assert [(check.out_of_date, check.failure_out_of_date(check.failures[0])) for check in held] == [
        (True, True),
        (True, True),
    ]
