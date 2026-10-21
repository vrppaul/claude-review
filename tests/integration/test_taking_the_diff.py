"""Taking the diff as the review opens, and again while the agent works: one take at a time, each in its round.

A retake waits on git. A second retake asked for meanwhile waits for the
first, so the newer tree is the one left on screen. A round sent while git
works does not become the round of the take under way, and a retake that
waits its turn meanwhile is taken in the round current as its turn comes.
The repository here holds every staging until the test lets it say what
moved, and the working tree has moved on between any two stagings of it.
And a tree git will not stage as the review opens leaves the review what the
command line read for it.

These are integration tests with a repository that is not git. The review
is put together by `host_review`, as the command line puts it together, with
a workspace and the reader's settings file it reads at each retake: I/O,
which `tests/unit/` holds none of. And git cannot be held between staging a
tree and saying what moved in it, which every test here needs, so the
repository is one that holds each staging until the test lets it go.
"""

import asyncio
import contextlib
from collections.abc import AsyncIterator
from pathlib import Path
from typing import override

from claude_review.domain.interfaces import GitError, ReviewedRepository, StagedTree
from claude_review.domain.models import (
    FIRST_ROUND,
    FIRST_TAKE,
    Checkout,
    DiffFile,
    GitRef,
    OnBranch,
)
from claude_review.services.review.review import Review
from claude_review.services.review_opening import OpenedRepository, ReviewOpening
from tests.helpers import LOOK_EVERY_SECONDS, SETTLE_SECONDS, TEST_IDENTITY, FixedClock, ReviewFactory, one_line_file

ROOT = Path("/repository")
# The commit the review opened on: its uncommitted changes, as HEAD stood then
OPENED_ON = "commit-at-opening"
# What the repository had checked out as the review opened
CHECKED_OUT = OnBranch(branch="main")
# When every mark here is left, on the review's clock
MARKED_AT = 1_791_000_000_000
# The one file each staging finds changed, in the order the stagings are made:
# the opening's, then the first retake's, then the second's
OPENING_FILE = "opening.py"
OLDER_FILE = "older.py"
NEWER_FILE = "newer.py"
# What the command line read for a review opened with nothing read for it yet: what is on screen is whatever
# its stagings find
NOTHING_READ: list[DiffFile] = []
# What the reader sends as a round while the diff is taken again
A_ROUND = "Another word for it, please."


def _diff_adding(path: str) -> str:
    """What git says of a file added with one line in it."""
    return f"diff --git a/{path} b/{path}\nnew file mode 100644\n--- /dev/null\n+++ b/{path}\n@@ -0,0 +1 @@\n+x\n"


class HeldStaging(StagedTree):
    """The tree as it stood when it was staged, which says what moved since a base only once it is let."""

    def __init__(self, path: str) -> None:
        self._path = path
        self.asked = asyncio.Event()
        self.answer = asyncio.Event()

    @override
    async def diff(self, base: str, *, ignore_whitespace: bool) -> str:
        return _diff_adding(self._path)

    @override
    async def write_tree(self) -> str:
        return f"tree-of-{self._path}"

    @override
    async def names_changed_since(self, bases: list[str]) -> dict[str, list[str]]:
        self.asked.set()
        await self.answer.wait()
        return {base: [self._path] for base in bases}

    @override
    async def too_large_to_show(self, base: str, files: list[DiffFile]) -> set[str]:
        return set()


class RepositoryBeingWorkedOn(ReviewedRepository):
    """A working tree the agent changes between any two stagings of it: the opening's, then two retakes'."""

    def __init__(self) -> None:
        # Made before any is staged, so a test holds each from the start
        self.stagings = [HeldStaging(path) for path in (OPENING_FILE, OLDER_FILE, NEWER_FILE)]
        self._next = iter(self.stagings)

    @override
    @contextlib.asynccontextmanager
    async def staged(self, path: Path) -> AsyncIterator[HeldStaging]:
        yield next(self._next)

    @override
    async def top_level(self, path: Path) -> Path | None:
        return path

    @override
    async def changed_paths(self, path: Path) -> list[str]:
        return []

    @override
    async def list_refs(self, path: Path) -> list[GitRef]:
        return []

    @override
    async def commit_named(self, path: Path, revision: str) -> str | None:
        return OPENED_ON

    @override
    async def empty_tree(self, path: Path) -> str:
        return "empty-tree"

    @override
    async def checked_out(self, path: Path) -> Checkout:
        return CHECKED_OUT

    @override
    async def diff_between(self, path: Path, earlier: str, later: str) -> str:
        return ""

    @override
    async def is_tracked(self, root: Path, relative_path: str) -> bool:
        return True


class RepositoryGitWillNotStage(RepositoryBeingWorkedOn):
    """A working tree git refuses to stage just now, as one whose index another git holds locked."""

    @override
    def staged(self, path: Path) -> contextlib.AbstractAsyncContextManager[HeldStaging]:
        refusal = "the index is locked"
        raise GitError(refusal)


async def _opened(reviews: ReviewFactory, repository: RepositoryBeingWorkedOn, read_for_it: list[DiffFile]) -> Review:
    """A review of the repository's uncommitted changes, put together and opened as the server opens it."""
    opening = ReviewOpening(
        source=OpenedRepository(
            root=ROOT,
            named_base=None,
            pinned_base=OPENED_ON,
            checkout=CHECKED_OUT,
        ),
        diff_files=read_for_it,
        title="",
        identity=TEST_IDENTITY,
    )
    review = reviews.hosted(opening, clock=FixedClock(MARKED_AT), repository=repository).review
    await review.open()
    return review


async def _until_asked(staging: HeldStaging) -> None:
    """Return once a staging is asked what moved."""
    async with asyncio.timeout(SETTLE_SECONDS):
        await staging.asked.wait()


async def _on_screen(review: Review) -> list[str]:
    """The files of the review's own diff, as its page reads it."""
    return [file.path for file in (await review.view(None, ignore_whitespace=False)).files]


async def test_a_retake_asked_for_while_one_is_under_way_waits_for_it_and_leaves_the_newer_tree_on_screen(
    reviews: ReviewFactory,
) -> None:
    repository = RepositoryBeingWorkedOn()
    [_, first, second] = repository.stagings
    review = await _opened(reviews, repository, NOTHING_READ)
    older = asyncio.create_task(review.retake())
    await _until_asked(first)

    newer = asyncio.create_task(review.retake())
    # Long enough for the second retake to stage the tree, if nothing holds it back
    await asyncio.sleep(LOOK_EVERY_SECONDS)
    staged_beside_the_first = second.asked.is_set()
    first.answer.set()
    await _until_asked(second)
    second.answer.set()
    await asyncio.gather(older, newer)

    assert (staged_beside_the_first, await _on_screen(review)) == (False, [NEWER_FILE])


async def test_a_round_sent_while_the_diff_is_taken_again_leaves_the_take_in_the_round_it_began_in(
    reviews: ReviewFactory,
) -> None:
    repository = RepositoryBeingWorkedOn()
    [_, first, _] = repository.stagings
    review = await _opened(reviews, repository, NOTHING_READ)
    retaking = asyncio.create_task(review.retake())
    await _until_asked(first)

    review.submit(threads=[], body=A_ROUND, ends=False)
    first.answer.set()

    assert (await retaking).round == FIRST_ROUND


async def test_a_retake_waiting_its_turn_while_a_round_is_sent_is_taken_in_that_round(reviews: ReviewFactory) -> None:
    """It stages the tree once the retake before it is done, in the round sent meanwhile."""
    repository = RepositoryBeingWorkedOn()
    [_, first, second] = repository.stagings
    review = await _opened(reviews, repository, NOTHING_READ)
    older = asyncio.create_task(review.retake())
    await _until_asked(first)
    newer = asyncio.create_task(review.retake())
    # A turn of the loop, in which the second retake is asked for
    await asyncio.sleep(0)

    review.submit(threads=[], body=A_ROUND, ends=False)
    first.answer.set()
    await _until_asked(second)
    second.answer.set()

    assert ((await older).round, (await newer).round) == (FIRST_ROUND, FIRST_ROUND + 1)


async def test_a_tree_git_will_not_stage_as_the_review_opens_leaves_on_screen_what_was_read_for_it(
    reviews: ReviewFactory,
) -> None:
    """It costs the review its first mark, never the review: what is on screen is still the take it opened on."""
    read_for_it = [one_line_file(OPENING_FILE)]

    review = await _opened(reviews, RepositoryGitWillNotStage(), read_for_it)

    view = await review.view(None, ignore_whitespace=False)
    assert (view.files, view.take) == (read_for_it, FIRST_TAKE)
