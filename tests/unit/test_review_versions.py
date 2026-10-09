"""Which bases a review offers, out of the marks it has left.

The right-hand side of the diff is always the working tree, so a base is the
only thing there is to choose — and the only ones worth offering are the ones
that would show something. The repository here writes down a new tree each
time it is asked and says one file differs from every base, so what is
offered depends on the marks alone.
"""

from pathlib import Path

from claude_review.domain.models import GitRef, VersionKind
from claude_review.services.review.review_versions import ReviewVersions
from tests.helpers import FixedClock

ROOT = Path("/repository")
# When every mark here is left, on the review's clock
MARKED_AT = 1_791_000_000_000
# The one file the repository says differs from any base
MOVED_FILE = "moved.py"


class RepositoryThatMoves:
    """A repository whose tree is a new one every time it is written down, one file away from any base."""

    def __init__(self) -> None:
        self._written = 0

    async def snapshot(self, path: Path) -> str:
        self._written += 1
        return f"tree-{self._written}"

    async def changed_since(self, path: Path, bases: list[str]) -> dict[str, list[str]]:
        return {base: [MOVED_FILE] for base in bases}

    async def list_refs(self, path: Path) -> list[GitRef]:
        return []

    async def get_raw_diff(self, path: Path, base: str | None = None, *, ignore_whitespace: bool = False) -> str:
        return ""

    async def top_level(self, path: Path) -> Path | None:
        return path

    async def changed_paths(self, path: Path) -> list[str]:
        return []


def _versions() -> ReviewVersions:
    return ReviewVersions(RepositoryThatMoves(), FixedClock(MARKED_AT), ROOT, review_base=None)


async def _rounds_offered(versions: ReviewVersions) -> list[tuple[str, str, str]]:
    """The rounds on offer, each by its key, its menu label and the header's phrase for it."""
    return [
        (version.key, version.label, version.phrase)
        for version in await versions.offer()
        if version.kind == VersionKind.ROUND
    ]


async def test_every_round_that_has_a_mark_is_on_offer() -> None:
    versions = _versions()
    for round_number in (1, 2, 3):
        await versions.mark(round_number)

    assert await _rounds_offered(versions) == [
        ("round:1", "round 1", "changes since round 1"),
        ("round:2", "round 2", "changes since round 2"),
        ("round:3", "round 3", "changes since round 3"),
    ]


async def test_a_round_is_remembered_as_it_began() -> None:
    """The agent may retake the diff twice in one round; the round started once."""
    versions = _versions()
    await versions.mark(1)
    await versions.mark(2)
    await versions.mark(2)

    assert [key for key, _, _ in await _rounds_offered(versions)] == ["round:1", "round:2"]
    assert await versions.resolve("round:2") == "tree-2"


async def test_a_round_is_dated_when_it_was_read() -> None:
    versions = _versions()
    await versions.mark(1)

    [offered] = [version for version in await versions.offer() if version.kind == VersionKind.ROUND]
    assert offered.at == MARKED_AT


async def test_a_review_that_has_left_no_marks_offers_no_rounds() -> None:
    assert await _rounds_offered(_versions()) == []


async def test_a_review_that_has_left_no_marks_cannot_say_what_changed() -> None:
    """Nothing to compare against is not nothing having changed."""
    assert await _versions().changed_since_round_began(1) is None
