"""The checks the agent reported, as the review's `ReviewChecks` keeps them: their one owner.

Each is stamped as it arrives with the round, the moment and the tree git
writes down; one reported under a name already held takes its place, and
every page is told the checks whole each time.
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

PYTEST_FAILED = CheckReport(
    name="pytest",
    status=CheckStatus.FAILED,
    summary="1 failed, 411 passed",
    failures=[CheckFailure(path="tests/test_a.py", line=42, what="test_rename", why="AssertionError")],
)
PYTEST_PASSED = CheckReport(name="pytest", status=CheckStatus.PASSED, summary="412 passed", failures=[])
RUFF_PASSED = CheckReport(name="ruff", status=CheckStatus.PASSED, summary=None, failures=[])


class TreeWrittenAs(TreesWritten):
    """A repository whose working tree git writes down as one tree, or will not write at all."""

    def __init__(self, tree: str | None) -> None:
        self._tree = tree

    @override
    async def tree_as_it_stands(self) -> str | None:
        return self._tree


def _checks(page: RecordingPage, tree: str | None = THE_TREE) -> ReviewChecks:
    return ReviewChecks(TreeWrittenAs(tree), FixedClock(REPORTED_AT), page)


async def test_a_check_reported_is_held_stamped_and_current_and_every_page_is_told() -> None:
    page = RecordingPage()
    checks = _checks(page)

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
    checks = _checks(RecordingPage())
    await checks.report(PYTEST_FAILED, round_number=SECOND_ROUND)
    await checks.report(RUFF_PASSED, round_number=SECOND_ROUND)

    await checks.report(PYTEST_PASSED, round_number=SECOND_ROUND)

    assert [(check.name, check.status) for check in checks.held] == [
        ("pytest", CheckStatus.PASSED),
        ("ruff", CheckStatus.PASSED),
    ]


async def test_a_check_whose_tree_git_would_not_write_is_out_of_date_and_every_failure_with_it() -> None:
    """Nobody can say what it ran on, and a reader told it is current stops looking."""
    checks = _checks(RecordingPage(), tree=None)

    await checks.report(PYTEST_FAILED, round_number=SECOND_ROUND)

    [held] = checks.held
    assert held.out_of_date
    assert [held.failure_out_of_date(failure) for failure in held.failures] == [True]
