"""Which bases a review offers, out of the marks it has left.

The right-hand side of the diff is always the working tree, so a base is the
only thing there is to choose — and the only ones worth offering are the ones
that would show something. The repository here writes down a new tree each
time it is asked and says one file differs from every base, so what is
offered depends on the marks alone.
"""

import contextlib
from collections.abc import AsyncIterator
from pathlib import Path
from typing import override

from claude_review.domain.interfaces import Repository, StagedTree
from claude_review.domain.models import ChangedSinceRound, GitRef, RoundKey, VersionOnOffer
from claude_review.services.review.review_versions import ReviewVersions
from claude_review.services.review_opening import OpenedRepository
from tests.helpers import FixedClock

ROOT = Path("/repository")
# The commit the review opened on: its uncommitted changes, as HEAD stood then
OPENED_ON = "commit-at-opening"
# When every mark here is left, on the review's clock
MARKED_AT = 1_791_000_000_000
# What the repository says differs from a base: one file, named after the base
MOVED_SINCE = "moved-since-{base}.py"


class TreeThatMoves(StagedTree):
    """A staged tree that is a new one each time it is written down, one file away from any base, named for it."""

    def __init__(self, repository: RepositoryThatMoves) -> None:
        self._repository = repository

    @override
    async def diff(self, base: str, *, ignore_whitespace: bool) -> str:
        return ""

    @override
    async def write_tree(self) -> str:
        return self._repository.next_tree()

    @override
    async def names_changed_since(self, bases: list[str]) -> dict[str, list[str]]:
        return {base: [MOVED_SINCE.format(base=base)] for base in bases}


class RepositoryThatMoves(Repository):
    """A repository whose working tree moves between any two stagings."""

    def __init__(self) -> None:
        self._written = 0

    def next_tree(self) -> str:
        self._written += 1
        return f"tree-{self._written}"

    @override
    @contextlib.asynccontextmanager
    async def staged(self, path: Path) -> AsyncIterator[TreeThatMoves]:
        yield TreeThatMoves(self)

    @override
    async def list_refs(self, path: Path) -> list[GitRef]:
        return []

    @override
    async def top_level(self, path: Path) -> Path | None:
        return path

    @override
    async def changed_paths(self, path: Path) -> list[str]:
        return []

    @override
    async def commit_named(self, path: Path, revision: str) -> str | None:
        return OPENED_ON

    @override
    async def empty_tree(self, path: Path) -> str:
        return "empty-tree"


class MarkingReview:
    """The bases of one review over a repository that moves, and its marks left one round at a time."""

    def __init__(self) -> None:
        self._repository = RepositoryThatMoves()
        self.versions = ReviewVersions(
            self._repository,
            FixedClock(MARKED_AT),
            OpenedRepository(root=ROOT, named_base=None, pinned_base=OPENED_ON),
        )

    async def mark(self, round_number: int) -> None:
        async with self._repository.staged(ROOT) as staged:
            await self.versions.mark(round_number, staged)

    async def changed_since_round_began(self, round_number: int) -> ChangedSinceRound | None:
        async with self._repository.staged(ROOT) as staged:
            return await self.versions.changed_since_round_began(round_number, staged)


async def _rounds_offered(review: MarkingReview) -> list[VersionOnOffer]:
    """The rounds on offer."""
    return [version for version in await review.versions.offer() if isinstance(version.key, RoundKey)]


async def test_every_round_that_has_a_mark_is_on_offer() -> None:
    review = MarkingReview()
    for round_number in (1, 2, 3):
        await review.mark(round_number)

    assert [version.key for version in await _rounds_offered(review)] == [
        RoundKey(round=1),
        RoundKey(round=2),
        RoundKey(round=3),
    ]


async def test_a_round_is_remembered_as_it_began() -> None:
    """The agent may retake the diff twice in one round; the round started once."""
    review = MarkingReview()
    await review.mark(1)
    await review.mark(2)
    await review.mark(2)

    assert [version.key for version in await _rounds_offered(review)] == [RoundKey(round=1), RoundKey(round=2)]
    assert await review.versions.resolve(RoundKey(round=2)) == "tree-2"


async def test_a_round_is_dated_when_it_was_read() -> None:
    review = MarkingReview()
    await review.mark(1)

    [offered] = await _rounds_offered(review)
    assert offered.at == MARKED_AT


async def test_a_review_that_has_left_no_marks_offers_no_rounds() -> None:
    assert await _rounds_offered(MarkingReview()) == []


async def test_a_review_that_has_left_no_marks_cannot_say_what_changed() -> None:
    """Nothing to compare against is not nothing having changed."""
    assert await MarkingReview().changed_since_round_began(1) is None


async def test_what_changed_is_counted_from_where_the_round_began() -> None:
    review = MarkingReview()
    await review.mark(1)
    await review.mark(1)

    assert await review.changed_since_round_began(1) == ChangedSinceRound(
        round=1, paths=[MOVED_SINCE.format(base="tree-1")]
    )


async def test_a_round_not_yet_marked_is_counted_from_the_base_its_count_names() -> None:
    """The count and the base it opens agree: "changed since round 1" counts from where `round:1` opens."""
    review = MarkingReview()
    await review.mark(1)
    await review.mark(1)

    changes = await review.changed_since_round_began(2)

    assert changes is not None
    named = await review.versions.resolve(RoundKey(round=changes.round))
    assert changes == ChangedSinceRound(round=1, paths=[MOVED_SINCE.format(base=named)])
