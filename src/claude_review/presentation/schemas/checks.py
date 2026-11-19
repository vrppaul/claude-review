"""What passes about the checks the agent ran: its report of one, and each as the review holds it."""

from pathlib import PurePosixPath
from typing import Annotated, Self

from pydantic import AfterValidator, ConfigDict, Field, StrictBool, StrictInt, model_validator

from claude_review.domain import checks
from claude_review.domain.checks import CheckStatus, passed_with_failures
from claude_review.domain.models import FIRST_LINE, EpochMillis, FilePath
from claude_review.presentation.schemas.base import SaidWords, Schema

# The longest a check's name may be: a tool's name, a line on a chip, never its output
MAX_CHECK_NAME_LENGTH = 200
# The most places one check may say it failed: a band under each line, past which a summary says it better
MAX_CHECK_FAILURES = 100

# What a check is called: the tool that ran, which a report under the same name replaces
CheckName = Annotated[SaidWords, Field(max_length=MAX_CHECK_NAME_LENGTH)]


def _from_the_repository(path: str) -> str:
    """Refuse a path written from the file system's root: the change names its files from the repository's.

    Raises:
        ValueError: if the path is absolute, which no file of the change would ever match.
    """
    if PurePosixPath(path).is_absolute():
        msg = "is written from the file system's root, not the repository's"
        raise ValueError(msg)
    return path


# A file a check failed in, as the change names it
RepositoryPath = Annotated[FilePath, AfterValidator(_from_the_repository)]


class FailureReported(Schema):
    """One place a check failed, as the agent reports it: a line of a file, what failed there, and why."""

    # Told apart by what it says, so a place typed twice is sent once
    model_config = ConfigDict(frozen=True)

    path: RepositoryPath
    line: StrictInt = Field(ge=FIRST_LINE)
    what: SaidWords
    # Why it failed, where the tool says
    why: SaidWords | None = None

    def to_domain(self) -> checks.CheckFailure:
        return checks.CheckFailure(path=self.path, line=self.line, what=self.what, why=self.why)


class CheckRequest(Schema):
    """Request body for POST /api/check — a check the agent ran, as it ended."""

    name: CheckName
    status: CheckStatus
    # What it said in short: "412 passed", "3 errors"
    summary: SaidWords | None = None
    failures: list[FailureReported] = Field(default_factory=list, max_length=MAX_CHECK_FAILURES)

    @model_validator(mode="after")
    def failed_where_it_says(self) -> Self:
        if passed_with_failures(self.status, self.failures):
            msg = "names where it failed, and says it passed"
            raise ValueError(msg)
        return self

    def to_domain(self) -> checks.CheckReport:
        return checks.CheckReport(
            name=self.name,
            status=self.status,
            summary=self.summary,
            failures=[failure.to_domain() for failure in self.failures],
        )


class CheckFailure(Schema):
    """One place a check failed, and whether its file changed since the check ran."""

    path: str
    line: int
    what: str
    why: str | None
    # The server's to decide, never the page's: its file is among those changed, or nobody can say it is not
    out_of_date: StrictBool

    @classmethod
    def from_domain(cls, failure: checks.CheckFailure, *, check: checks.Check) -> Self:
        return cls(
            path=failure.path,
            line=failure.line,
            what=failure.what,
            why=failure.why,
            out_of_date=check.failure_out_of_date(failure),
        )


class Check(Schema):
    """A check the agent ran, as the review holds it: as it ended, when, and whether the code moved on since."""

    name: str
    status: CheckStatus
    summary: str | None
    failures: list[CheckFailure]
    # The round being written when it was reported, and the moment
    round: int
    at: EpochMillis
    # The files that differ from the tree it ran on; null where that cannot be said
    changed_since: list[str] | None
    # Worth running again: files changed since it ran, or nobody can say none did
    out_of_date: StrictBool

    @classmethod
    def from_domain(cls, check: checks.Check) -> Self:
        return cls(
            name=check.name,
            status=check.status,
            summary=check.summary,
            failures=[CheckFailure.from_domain(failure, check=check) for failure in check.failures],
            round=check.round,
            at=check.at,
            changed_since=check.changed_since,
            out_of_date=check.out_of_date,
        )
