"""The checks the agent reported, for the review's life: the reader cannot otherwise see that one ran, nor on what.

Each is stamped with the tree git writes down, never the files' times,
which a commit made after the check would move without changing a line it
ran on.
"""

import asyncio
from abc import ABC, abstractmethod

import structlog

from claude_review.domain.checks import Check, CheckReport
from claude_review.domain.interfaces import Clock, PageChannel
from claude_review.domain.page_events import ChecksChanged

log = structlog.get_logger()


class TreesWritten(ABC):
    """The working tree written down by git, as a check is stamped with it, and measured against it later."""

    @abstractmethod
    async def tree_as_it_stands(self) -> str | None:
        """The working tree as it stands now, written down: None if git would not write it.

        Raises:
            NoRepositoryError: if no repository holds the content.
        """

    @abstractmethod
    async def changed_since(self, trees: list[str]) -> dict[str, list[str]]:
        """The paths that differ between each tree and the working tree now, for each git will say it of.

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
        # Held while git is asked, so a measuring never lands on a check
        # reported after it asked
        self._asking_git = asyncio.Lock()

    @property
    def held(self) -> list[Check]:
        return list(self._held.values())

    @property
    def names_out_of_date(self) -> list[str]:
        """The names of the checks the code may have moved on from, to run again."""
        return [check.report.name for check in self._held.values() if check.out_of_date]

    async def report(self, report: CheckReport, *, round_number: int) -> None:
        """Take a check, stamped with the tree as it stands, in place of any under its name, and tell the pages.

        Raises:
            NoRepositoryError: if no repository holds the content: there is no tree to stamp it with.
        """
        async with self._asking_git:
            tree = await self._trees.tree_as_it_stands()
            self._held[report.name] = report.stamped(round_number=round_number, at=self._clock.now(), tree=tree)
        self._page.tell(ChecksChanged(checks=self.held))
        log.info("check_reported", name=report.name, status=report.status, failures=len(report.failures))

    async def measure(self) -> None:
        """Measure every check against the working tree as it stands, and tell the pages where any changed.

        With no tree to measure, git is not asked.
        """
        async with self._asking_git:
            trees = [check.tree for check in self._held.values() if check.tree is not None]
            if not trees:
                return
            changed_since = await self._trees.changed_since(trees)
            measured = {name: check.measured(changed_since) for name, check in self._held.items()}
            if measured == self._held:
                return
            self._held = measured
        self._page.tell(ChecksChanged(checks=self.held))
        log.info("checks_measured", out_of_date=len(self.names_out_of_date))
