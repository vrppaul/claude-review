"""The checks the agent ran, as the review holds them: the reader cannot otherwise see that one ran, nor on what."""

from collections.abc import Sequence
from enum import StrEnum, auto

from pydantic import BaseModel, ConfigDict, Field

from claude_review.domain.models import FIRST_LINE, EpochMillis, FilePath


class CheckStatus(StrEnum):
    """How a check ended.

    PASSED — it found nothing wrong.
    FAILED — it found something wrong, or could not run.
    """

    PASSED = auto()
    FAILED = auto()


def passed_with_failures(status: CheckStatus, failures: Sequence[object]) -> bool:
    """Whether a check says it passed and names places it failed: one of the two is wrong."""
    return status is CheckStatus.PASSED and bool(failures)


class CheckFailure(BaseModel):
    """One place a check failed: a line of a file, what failed there, and why, where the tool says."""

    model_config = ConfigDict(frozen=True)

    # From the repository's root, as the paths of the change are
    path: FilePath
    line: int = Field(ge=FIRST_LINE)
    what: str
    why: str | None


class CheckReport(BaseModel):
    """A check as the agent reports it: the tool's name, how it ended, what it said in short, and where it failed."""

    model_config = ConfigDict(frozen=True)

    name: str
    status: CheckStatus
    summary: str | None
    failures: list[CheckFailure]

    def stamped(self, *, round_number: int, at: EpochMillis, tree: str | None) -> Check:
        """The report as the review holds it, stamped with when it came and the tree it ran on: current, by its tree."""
        return Check(report=self, round=round_number, at=at, tree=tree, changed_since=None if tree is None else [])


class Check(BaseModel):
    """A check as the review holds it: as reported, stamped, and measured against the working tree."""

    model_config = ConfigDict(frozen=True)

    report: CheckReport
    # The round being written when it was reported, and the moment
    round: int
    at: EpochMillis
    # The working tree as it stood when the check was reported, written down
    # by git: None where git would not write it
    tree: str | None
    # The paths that differ between that tree and the working tree now: None
    # where that cannot be said, which is no ground to call the check current
    changed_since: list[str] | None

    @property
    def out_of_date(self) -> bool:
        """Whether the code may have moved on since the check ran: a file changed, or nobody can say none did."""
        return self.changed_since != []

    def measured(self, changed_since: dict[str, list[str]]) -> Check:
        """The check against the working tree, from the paths changed since each tree: unknown where its tree is not."""
        return Check(
            report=self.report,
            round=self.round,
            at=self.at,
            tree=self.tree,
            changed_since=None if self.tree is None else changed_since.get(self.tree),
        )

    def failure_out_of_date(self, failure: CheckFailure) -> bool:
        """Whether the file a failure is in may have changed since the check ran."""
        return self.changed_since is None or failure.path in self.changed_since
