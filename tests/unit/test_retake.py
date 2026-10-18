"""Taking the diff as the review opens, and again while the agent works: one take at a time, each in its round.

A retake waits on git. A second retake asked for meanwhile must not leave the
older tree on screen once both are done, and a round sent meanwhile must not
tag this take with a round it was not taken in. The repository here holds
every staging until the test lets it say what moved, and the working tree
has moved on between any two stagings of it. And a tree git will not stage
as the review opens leaves the review what the command line read for it.

A story told of one take is followed onto each take after it, always from
the story as it was told: it says whether the code moved on under it, in
which round, and how much it left out when it was told.
"""

import asyncio
import contextlib
from collections.abc import AsyncIterator
from pathlib import Path
from typing import override

from claude_review.domain.interfaces import GitError, ReviewedRepository, StagedTree
from claude_review.domain.models import FIRST_ROUND, FIRST_TAKE, DiffFile, GitRef, ReviewMode
from claude_review.domain.story import CodeMovedOn, LeftOutChanged
from claude_review.services.review.content_sources import ContentSource, content_source
from claude_review.services.review.review_content import ReviewContent, TakesCompared
from claude_review.services.review.round_tracker import RoundTracker
from claude_review.services.review_opening import OpenedRepository, ReviewOpening
from tests.helpers import LOOK_EVERY_SECONDS, SETTLE_SECONDS, TEST_IDENTITY, FixedClock, one_line_file
from tests.stories import (
    FIRST_REWRITTEN,
    NO_TAKES,
    NOTHING_LEFT_OUT,
    ONE_MORE_LEFT_OUT,
    SECOND_ROUND,
    STORIES_OFF,
    THE_FIRST_LINE,
    TOLD_OF,
    TakesComparedByTheirLines,
    changed_file,
    hunk,
    step,
    story_of,
    review_story,
    take_of,
    told_then_followed,
    tree_of,
)

ROOT = Path("/repository")
# The commit the review opened on: its uncommitted changes, as HEAD stood then
OPENED_ON = "commit-at-opening"
# When every mark here is left, on the review's clock
MARKED_AT = 1_791_000_000_000
# The one file each staging finds changed, in the order the stagings are made:
# the opening's, then the first retake's, then the second's
OPENING_FILE = "opening.py"
OLDER_FILE = "older.py"
NEWER_FILE = "newer.py"
# Which staging is the first retake's: the opening's comes before it
FIRST_RETAKES_STAGING = 1
# The round a story's fourth take is taken in, each take after the first in a round of its own
FOURTH_ROUND = SECOND_ROUND + 2
# A file added whole and long, and a story with a step to every other line of it: long in the telling, so it is
# surely still being told when a test that started it follows the story onto a later take, of one line more
LONG_FILE = "src/long.py"
LINES_OF_THE_LONG_FILE = 4000
LONG_FILE_ADDED = [changed_file(LONG_FILE, hunk(0, 1, "+" * LINES_OF_THE_LONG_FILE))]
ONE_LINE_MORE_OF_IT = [changed_file(LONG_FILE, hunk(0, 1, "+" * (LINES_OF_THE_LONG_FILE + 1)))]
A_LONG_STORY = story_of(*[step(LONG_FILE, line, line) for line in range(1, LINES_OF_THE_LONG_FILE, 2)])


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
    """A working tree the agent changes between any two stagings of it."""

    def __init__(self) -> None:
        self.stagings: list[HeldStaging] = []
        self._paths = iter([OPENING_FILE, OLDER_FILE, NEWER_FILE])

    @override
    @contextlib.asynccontextmanager
    async def staged(self, path: Path) -> AsyncIterator[HeldStaging]:
        staging = HeldStaging(next(self._paths))
        self.stagings.append(staging)
        yield staging

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
    async def diff_between(self, path: Path, earlier: str, later: str) -> str:
        return ""

    @override
    async def is_tracked(self, root: Path, relative_path: str) -> bool:
        return True


class TakesGitWillNotCompare(TakesCompared):
    """Takes whose trees git refuses to read, as when the review's object store was taken away under it."""

    @override
    async def changed_between(self, earlier: str, later: str) -> list[DiffFile]:
        refusal = "fatal: bad object"
        raise GitError(refusal)


class RepositoryGitWillNotStage(RepositoryBeingWorkedOn):
    """A working tree git refuses to stage just now, as one whose index another git holds locked."""

    @override
    def staged(self, path: Path) -> contextlib.AbstractAsyncContextManager[HeldStaging]:
        refusal = "the index is locked"
        raise GitError(refusal)


async def _opened_on(
    read_for_it: list[DiffFile], repository: RepositoryBeingWorkedOn, rounds: RoundTracker
) -> ContentSource:
    """A review of the repository's uncommitted changes, opened as the server opens it on what was read for it."""
    opening = ReviewOpening(
        mode=ReviewMode.DIFF,
        diff_files=read_for_it,
        title="",
        identity=TEST_IDENTITY,
        repository=OpenedRepository(root=ROOT, named_base=None, pinned_base=OPENED_ON),
    )
    source = content_source(opening, repository=repository, clock=FixedClock(MARKED_AT), rounds=rounds)
    await source.open()
    return source


async def _opened(repository: RepositoryBeingWorkedOn, rounds: RoundTracker) -> ContentSource:
    """A review opened with nothing read for it yet: what is on screen is whatever its stagings find."""
    return await _opened_on([], repository, rounds)


async def _until_asked(repository: RepositoryBeingWorkedOn, staging_number: int) -> HeldStaging:
    """Return a staging, by the order it was made in, once it is asked what moved."""
    async with asyncio.timeout(SETTLE_SECONDS):
        while len(repository.stagings) <= staging_number:
            await asyncio.sleep(LOOK_EVERY_SECONDS)
        staging = repository.stagings[staging_number]
        await staging.asked.wait()
        return staging


async def _answer_newest_first(repository: RepositoryBeingWorkedOn, retakes: list[asyncio.Task]) -> None:
    """Let the stagings asked about answer, the one made last first, until every retake is done."""
    async with asyncio.timeout(SETTLE_SECONDS):
        while not all(retake.done() for retake in retakes):
            waiting = [
                staging for staging in repository.stagings if staging.asked.is_set() and not staging.answer.is_set()
            ]
            if waiting:
                waiting[-1].answer.set()
            await asyncio.sleep(LOOK_EVERY_SECONDS)


async def test_two_retakes_at_once_leave_the_newer_tree_on_screen() -> None:
    repository = RepositoryBeingWorkedOn()
    source = await _opened(repository, RoundTracker())
    older = asyncio.create_task(source.retake())
    await _until_asked(repository, FIRST_RETAKES_STAGING)

    newer = asyncio.create_task(source.retake())
    # Long enough for the second retake to stage the tree, if nothing holds it back
    await asyncio.sleep(LOOK_EVERY_SECONDS)
    await _answer_newest_first(repository, [older, newer])

    assert [file.path for file in source.content.files] == [NEWER_FILE]


async def test_a_round_sent_while_the_diff_is_taken_again_leaves_the_take_in_the_round_it_began_in() -> None:
    rounds = RoundTracker()
    repository = RepositoryBeingWorkedOn()
    source = await _opened(repository, rounds)
    retaking = asyncio.create_task(source.retake())
    staging = await _until_asked(repository, FIRST_RETAKES_STAGING)

    rounds.begin_next()
    staging.answer.set()
    retaken = await retaking

    assert retaken.round == FIRST_ROUND


async def test_a_tree_git_will_not_stage_as_the_review_opens_leaves_on_screen_what_was_read_for_it() -> None:
    """It costs the review its first mark, never the review: what is on screen is still the take it opened on."""
    read_for_it = [one_line_file(OPENING_FILE)]

    source = await _opened_on(read_for_it, RepositoryGitWillNotStage(), RoundTracker())

    assert source.content.files == read_for_it
    assert source.content.take == FIRST_TAKE


async def test_a_story_followed_onto_a_later_take_is_of_that_take_and_still_of_the_round_that_told_it() -> None:
    held = (await told_then_followed(TOLD_OF, ONE_MORE_LEFT_OUT)).held

    assert held is not None
    assert (held.take, held.round) == (FIRST_TAKE + 1, FIRST_ROUND)


async def test_a_story_more_is_left_out_of_says_the_round_it_moved_on_in_and_what_was_left_out_then_and_now() -> None:
    held = (await told_then_followed(TOLD_OF, ONE_MORE_LEFT_OUT)).held

    assert held is not None
    assert held.moved_on == CodeMovedOn(round=SECOND_ROUND, left_out=LeftOutChanged(when_told=1, now=2))


async def test_a_story_that_moved_on_leaving_out_as_much_as_when_it_was_told_says_nothing_of_what_is_left_out() -> None:
    """The counts are said only where the round changed them: "1 → 1" would say nothing."""
    held = (await told_then_followed(TOLD_OF, FIRST_REWRITTEN)).held

    assert held is not None
    assert held.moved_on == CodeMovedOn(round=SECOND_ROUND, left_out=None)


async def test_a_story_the_code_stays_moved_on_under_says_the_round_it_first_moved_on_in() -> None:
    """Taken again in a later round with nothing more changed under it, it moved on when it first did."""
    held = (await told_then_followed(TOLD_OF, FIRST_REWRITTEN, FIRST_REWRITTEN)).held

    assert held is not None
    assert held.moved_on is not None
    assert held.moved_on.round == SECOND_ROUND


async def test_a_story_current_again_then_moved_on_again_says_the_round_it_moved_on_in_the_second_time() -> None:
    held = (await told_then_followed(TOLD_OF, FIRST_REWRITTEN, TOLD_OF, FIRST_REWRITTEN)).held

    assert held is not None
    assert held.moved_on is not None
    assert held.moved_on.round == FOURTH_ROUND


async def test_a_story_whose_step_changed_has_moved_on() -> None:
    held = (await told_then_followed(TOLD_OF, FIRST_REWRITTEN)).held

    assert held is not None
    assert held.moved_on is not None


async def test_a_story_less_is_left_out_of_with_no_step_changed_is_current() -> None:
    held = (await told_then_followed(TOLD_OF, NOTHING_LEFT_OUT)).held

    assert held is not None
    assert held.moved_on is None


async def test_a_story_whose_code_was_put_back_as_it_was_told_is_current_again() -> None:
    """Followed from the story as it was told, never from the take before."""
    held = (await told_then_followed(TOLD_OF, FIRST_REWRITTEN, TOLD_OF)).held

    assert held is not None
    assert held.moved_on is None
    assert [told_step.now.changed_since_told for told_step in held.story.chapters[0].steps] == [False]


async def test_a_story_told_while_the_diff_is_taken_again_is_followed_onto_the_new_take_once_it_is_held() -> None:
    """The take waits for the telling under way: followed before it, the story told would stay on the take before.

    Followed from the very take it was told of: one line added below every
    step leaves each on the lines it was told on.
    """
    told_of, now = take_of(LONG_FILE_ADDED, FIRST_TAKE), take_of(ONE_LINE_MORE_OF_IT, FIRST_TAKE + 1)
    takes = TakesComparedByTheirLines(
        {tree_of(FIRST_TAKE): LONG_FILE_ADDED, tree_of(FIRST_TAKE + 1): ONE_LINE_MORE_OF_IT}
    )
    story = review_story(takes)
    telling = asyncio.create_task(story.tell(A_LONG_STORY, told_of, round_number=FIRST_ROUND))
    # A turn of the loop, in which the telling begins
    await asyncio.sleep(0)

    await story.follow(now, round_number=SECOND_ROUND, stories_on=STORIES_OFF)
    await telling

    assert story.held is not None
    assert story.held.take == FIRST_TAKE + 1
    assert [told_step.now.lines for told_step in story.held.story.chapters[0].steps] == [
        told_step.lines for told_step in A_LONG_STORY.chapters[0].steps
    ]


async def test_a_story_told_of_a_take_git_never_wrote_down_is_followed_onto_no_code() -> None:
    """What changed since it was told cannot be said: no step is drawn on code guessed at."""
    story = review_story(NO_TAKES)
    await story.tell(THE_FIRST_LINE, ReviewContent.opening_on(TOLD_OF), round_number=FIRST_ROUND)

    await story.follow(take_of(TOLD_OF, FIRST_TAKE + 1), round_number=SECOND_ROUND, stories_on=STORIES_OFF)

    assert story.held is not None
    assert [told_step.now for told_step in story.held.story.chapters[0].steps] == [None]


async def test_a_story_whose_takes_git_will_not_compare_is_followed_onto_no_code() -> None:
    story = review_story(TakesGitWillNotCompare())
    await story.tell(THE_FIRST_LINE, take_of(TOLD_OF, FIRST_TAKE), round_number=FIRST_ROUND)

    await story.follow(take_of(TOLD_OF, FIRST_TAKE + 1), round_number=SECOND_ROUND, stories_on=STORIES_OFF)

    assert story.held is not None
    assert [told_step.now for told_step in story.held.story.chapters[0].steps] == [None]


async def test_a_take_with_no_story_told_holds_none() -> None:
    story = review_story(NO_TAKES)

    await story.follow(take_of(ONE_MORE_LEFT_OUT, FIRST_TAKE + 1), round_number=SECOND_ROUND, stories_on=STORIES_OFF)

    assert story.held is None
