"""The checks the agent reported, each the last reported under its name, stamped with the tree it ran on.

The reader cannot see that the agent's tests ran, nor on which code: the
agent says so, and the review keeps it for its life and tells every page.
The tree is git's, written from a staging as the report arrives, never the
files' times, which a commit made after the check would move without
changing a line it ran on.
"""

from abc import ABC, abstractmethod

import structlog

from claude_review.domain.checks import Check, CheckReport
from claude_review.domain.interfaces import Clock, PageChannel
from claude_review.domain.page_events import ChecksChanged

log = structlog.get_logger()


class TreesWritten(ABC):
    """The working tree written down by git, as a check is stamped with it."""

    @abstractmethod
    async def tree_as_it_stands(self) -> str | None:
        """The working tree as it stands now, written down: None if git would not write it.

        Raises:
            NoRepositoryError: if no repository holds the content.
        """


class ReviewChecks:
    """Every check the agent reported, by its name."""

    def __init__(self, trees: TreesWritten, clock: Clock, page: PageChannel) -> None:
        self._trees = trees
        self._clock = clock
        self._page = page
        # In the order first reported: one reported again keeps its place, so
        # the list the reader reads does not reshuffle under them
        self._held: dict[str, Check] = {}

    @property
    def held(self) -> list[Check]:
        return list(self._held.values())

    async def report(self, report: CheckReport, *, round_number: int) -> None:
        """Take a check, stamped with the tree as it stands, in place of any under its name, and tell the pages.

        Raises:
            NoRepositoryError: if no repository holds the content: there is no tree to stamp it with.
        """
        tree = await self._trees.tree_as_it_stands()
        self._held[report.name] = report.stamped(round_number=round_number, at=self._clock.now(), tree=tree)
        self._page.tell(ChecksChanged(checks=self.held))
        log.info("check_reported", name=report.name, status=report.status, failures=len(report.failures))
