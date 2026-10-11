"""What one review's diff can be compared against, and the marks it leaves to make that possible."""

from typing import assert_never

import structlog

from claude_review.domain.exceptions import UnknownVersionError
from claude_review.domain.interfaces import Clock, GitError, Repository, StagedTree
from claude_review.domain.models import (
    HEAD,
    ChangedSinceRound,
    RefKey,
    ReviewKey,
    RoundKey,
    TreeSnapshot,
    VersionKey,
    VersionOnOffer,
)
from claude_review.services.review_opening import OpenedRepository

log = structlog.get_logger()

# What an option begins with, which a revision the review reads against never may
OPTION_MARK = "-"


class ReviewVersions:
    """The bases one review offers, and what has moved since each of them.

    The right-hand side of a review's diff is always the working tree, so a
    base is the only thing there is to choose. A ref is there to be chosen
    already; a round is not, until the tree it was read at has been written
    down — which is what `mark` does, each time the diff is taken.

    Everything here answers "if it can be said": a repository git will not
    stage or write a tree for just now costs the review its versions, never
    the review itself.
    """

    def __init__(self, repository: Repository, clock: Clock, opened: OpenedRepository) -> None:
        self._repository = repository
        self._clock = clock
        # Where the repository is, and the review's own base: by the name the
        # reader gave it, and by what that named as the review opened
        self._opened = opened
        # The tree behind every diff this review has taken, oldest first. The
        # first of each round is a base the reader can go back to.
        self._marks: list[TreeSnapshot] = []

    @property
    def pinned_base(self) -> str:
        """What every take of the review's own diff is read against: its base as the review opened on it."""
        return self._opened.pinned_base

    async def mark(self, round_number: int, staged: StagedTree) -> None:
        """Write down the tree the diff has just been taken from, as part of a round."""
        try:
            tree = await staged.write_tree()
        except GitError as refusal:
            log.warning("snapshot_refused", round=round_number, reason=str(refusal))
            return
        self._marks.append(TreeSnapshot(round=round_number, tree=tree, at=self._clock.now()))

    async def changed_since_round_began(self, round_number: int, staged: StagedTree) -> ChangedSinceRound | None:
        """Which files have moved since a round began, if it can be said.

        None is not an empty list: one says nothing has changed, the other
        that there is no way to know — and a reader who is told nothing
        changed stops looking.
        """
        began = self._began(round_number)
        if began is None:
            return None
        paths = (await staged.names_changed_since([began.tree])).get(began.tree)
        return ChangedSinceRound(round=began.round, paths=paths) if paths is not None else None

    async def offer(self) -> list[VersionOnOffer]:
        """Every base this review can be compared against, in reading order.

        What it opened with comes first — it is the review, and everything
        else is a way of reading part of it — then its own rounds, newest
        knowledge last, then what the repository had before any of this.
        """
        rounds = self._rounds_began()
        # The ref the reader opened the review against is that first entry,
        # under the name they gave it; offered again, it would be a second row
        # of the same name
        refs = [ref for ref in await self._refs() if ref.key != RefKey(name=self._opened.named_base or HEAD)]
        counted = await self._counts([self._opened.pinned_base, *(mark.tree for mark in rounds)])

        review = VersionOnOffer(key=ReviewKey(), at=None, changed=counted.get(self._opened.pinned_base))
        offered_rounds = [
            VersionOnOffer(key=RoundKey(round=mark.round), at=mark.at, changed=counted.get(mark.tree))
            for mark in rounds
        ]
        # A round nothing has happened since would open an empty screen. The
        # review's own base is never dropped, however little it shows: it is
        # the way back.
        return [review, *[version for version in offered_rounds if version.changed != 0], *refs]

    async def resolve(self, key: VersionKey) -> str:
        """The revision a base names, as git will understand it.

        Nothing the page asks for reaches git as a revision unchecked: the
        review's own is the base it opened on, a round is answered from the
        marks this review left, and a ref has to be one the repository
        actually has, on a commit.

        Raises:
            UnknownVersionError: when nothing this review offers answers to it.
        """
        match key:
            case ReviewKey():
                return self._opened.pinned_base
            case RoundKey():
                began = next((mark for mark in self._marks if mark.round == key.round), None)
                if began is None:
                    msg = f"this review has no mark for round {key.round}"
                    raise UnknownVersionError(msg)
                return began.tree
            case RefKey():
                return await self._ref_named(key.name)
            case _:
                assert_never(key)

    async def _ref_named(self, name: str) -> str:
        """The commit a ref the repository has names now, checked as it is asked for.

        Checked here as well as when the refs are listed: what reaches `git
        diff` must never be able to arrive as an option, and a ref can be
        written between the listing and the asking. Read as the commit it
        names, the way the review's own base was when it opened, so the diff
        is taken against what was checked.

        Raises:
            UnknownVersionError: if it could be read as an option, the
                repository has no such ref, or it is on no commit.
        """
        if name.startswith(OPTION_MARK):
            msg = f"{name} cannot be a base: a revision may not begin with a dash"
            raise UnknownVersionError(msg)
        root = self._opened.root
        if name != HEAD and name not in {ref.name for ref in await self._repository.list_refs(root)}:
            msg = f"{name} is not a branch or tag of this repository"
            raise UnknownVersionError(msg)
        commit = await self._repository.commit_named(root, name)
        if commit is None:
            msg = f"{name} is not on a commit: nothing can be compared against it"
            raise UnknownVersionError(msg)
        return commit

    def _began(self, round_number: int) -> TreeSnapshot | None:
        """The mark a round is measured from, and offered as a base.

        The round's own first mark once it has one; before that, the last
        mark left behind, which is where the round began. It has to be the
        same tree the round's base resolves to, or the count and the screen
        the reader is sent to disagree — "3 files changed since round 2"
        opening a diff of five.
        """
        for mark in self._marks:
            if mark.round == round_number:
                return mark
        return self._marks[-1] if self._marks else None

    def _rounds_began(self) -> list[TreeSnapshot]:
        """The first mark of each round, in order.

        The agent may retake the diff several times while one round is being
        written; the round still began once, so the first mark of each is the
        one worth going back to.
        """
        began: dict[int, TreeSnapshot] = {}
        for mark in self._marks:
            began.setdefault(mark.round, mark)
        return list(began.values())

    async def _refs(self) -> list[VersionOnOffer]:
        """The branches and tags this repository can be read against, HEAD first, left uncounted."""
        listed = [
            VersionOnOffer(key=RefKey(name=ref.name), at=ref.at, changed=None)
            for ref in await self._repository.list_refs(self._opened.root)
        ]
        return [VersionOnOffer(key=RefKey(name=HEAD), at=None, changed=None), *listed]

    async def _counts(self, bases: list[str]) -> dict[str, int]:
        """How many files differ from each base, when git will say.

        The count is the reason to pick one base over another, so it is worth
        one staging of the tree — but only one, which is why every base is
        asked at once, and each only once: two rounds whose tree never moved
        are one tree.
        """
        try:
            async with self._repository.staged(self._opened.root) as staged:
                changed = await staged.names_changed_since(list(dict.fromkeys(bases)))
        except GitError as refusal:
            log.warning("counts_refused", reason=str(refusal))
            return {}
        return {base: len(paths) for base, paths in changed.items()}
