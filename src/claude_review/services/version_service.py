"""Service for what a review's diff can be compared against."""

import time
from pathlib import Path

import structlog

from claude_review.domain.exceptions import GitError, UnknownVersionError
from claude_review.domain.models import ReviewVersion, TreeSnapshot, VersionKind
from claude_review.domain.protocols import GitRepositoryProtocol

log = structlog.get_logger()

REVIEW_KEY = "review"
ROUND_PREFIX = "round:"
REF_PREFIX = "ref:"
UNCOMMITTED = "uncommitted changes"


class VersionService:
    """The bases on offer, and what has moved since each of them.

    The right-hand side of a review's diff is always the working tree, so a
    base is the only thing there is to choose. A ref is there to be chosen
    already; a round is not, until the tree it was read at has been written
    down.

    Everything here answers "if it can be said": a repository that will not
    write a tree — one mid-merge, whose index has unresolved entries — costs
    the review its versions, never the review itself.
    """

    def __init__(self, git_repository: GitRepositoryProtocol) -> None:
        self._git = git_repository

    async def take(self, path: Path, *, round_number: int) -> TreeSnapshot | None:
        """Write down the tree the diff has just been taken from."""
        try:
            tree = await self._git.snapshot(path)
        except GitError as e:
            log.warning("snapshot_refused", round=round_number, reason=str(e))
            return None
        return TreeSnapshot(round=round_number, tree=tree, at=int(time.time() * 1000))

    async def changed_since(self, path: Path, snapshot: TreeSnapshot | None) -> list[str] | None:
        """Which files have moved since a mark was left, if it can be said.

        None is not an empty list: one says nothing has changed, the other
        that there is no way to know — and a reader who is told nothing
        changed stops looking.
        """
        if snapshot is None:
            return None
        try:
            return (await self._git.changed_since(path, [snapshot.tree])).get(snapshot.tree)
        except GitError as e:
            log.warning("changed_since_refused", tree=snapshot.tree, reason=str(e))
            return None

    def began(self, snapshots: list[TreeSnapshot], round_number: int) -> TreeSnapshot | None:
        """The mark a round is measured from, and offered as a base.

        The round's own first mark once it has one; before that, the last
        mark left behind, which is where the round began. It has to be the
        same tree `round:N` resolves to, or the count and the screen the
        reader is sent to disagree — "3 files changed since round 2" opening
        a diff of five.
        """
        for mark in snapshots:
            if mark.round == round_number:
                return mark
        return snapshots[-1] if snapshots else None

    def phrase_of(self, key: str, *, review_base: str | None) -> str:
        """What the header says while this base is the one in force.

        Written here rather than in the browser, and answered without asking
        git anything, so a review can say what it is showing before it has
        looked up everything it could show instead.
        """
        if key == REVIEW_KEY:
            return f"changes since {review_base}" if review_base else UNCOMMITTED
        if key.startswith(ROUND_PREFIX):
            return f"changes since round {key.removeprefix(ROUND_PREFIX)}"
        name = key.removeprefix(REF_PREFIX)
        return UNCOMMITTED if name == "HEAD" else f"changes since {name}"

    def rounds(self, snapshots: list[TreeSnapshot]) -> list[ReviewVersion]:
        """One base per round, as that round found the tree.

        The agent may retake the diff several times while one round is being
        written; the round still began once, so the first mark of each is the
        one worth going back to. Whether a round is worth offering is a
        different question, and only what has changed since can answer it.
        """
        began: dict[int, TreeSnapshot] = {}
        for mark in snapshots:
            began.setdefault(mark.round, mark)

        return [
            ReviewVersion(
                key=f"{ROUND_PREFIX}{mark.round}",
                kind=VersionKind.ROUND,
                label=f"round {mark.round}",
                phrase=self.phrase_of(f"{ROUND_PREFIX}{mark.round}", review_base=None),
                at=mark.at,
            )
            for mark in began.values()
        ]

    async def refs(self, path: Path) -> list[ReviewVersion]:
        """The branches and tags this repository can be read against."""
        head = ReviewVersion(
            key=f"{REF_PREFIX}HEAD",
            kind=VersionKind.REF,
            label="HEAD",
            phrase=self.phrase_of(f"{REF_PREFIX}HEAD", review_base=None),
        )
        listed = [
            ReviewVersion(
                key=f"{REF_PREFIX}{ref.name}",
                kind=VersionKind.REF,
                label=ref.name,
                phrase=self.phrase_of(f"{REF_PREFIX}{ref.name}", review_base=None),
                at=ref.at * 1000,
            )
            for ref in await self._git.list_refs(path)
        ]
        return [head, *listed]

    async def offer(self, path: Path, *, review_base: str | None, snapshots: list[TreeSnapshot]) -> list[ReviewVersion]:
        """Every base this review can be compared against, in reading order.

        What it opened with comes first — it is the review, and everything
        else is a way of reading part of it — then its own rounds, newest
        knowledge last, then what the repository had before any of this.
        """
        review = ReviewVersion(
            key=REVIEW_KEY,
            kind=VersionKind.REVIEW,
            label=review_base or UNCOMMITTED,
            phrase=self.phrase_of(REVIEW_KEY, review_base=review_base),
        )
        rounds = self.rounds(snapshots)
        # A ref the review already opened against is that first entry; it is
        # not a second way of looking at the same thing
        refs = [ref for ref in await self.refs(path) if ref.label != (review_base or "HEAD")]

        trees = self._trees(snapshots)
        counted = await self._counts(path, {REVIEW_KEY: review_base or "HEAD"} | {v.key: trees[v.key] for v in rounds})
        review.changed = counted.get(REVIEW_KEY)
        for version in rounds:
            version.changed = counted.get(version.key)

        # A round nothing has happened since would open an empty screen. The
        # review's own base is never dropped, however little it shows: it is
        # the way back.
        return [review, *[v for v in rounds if v.changed != 0], *refs]

    async def resolve(
        self, path: Path, key: str, *, review_base: str | None, snapshots: list[TreeSnapshot]
    ) -> str | None:
        """The revision a key names, as git will understand it.

        Nothing from the query string reaches git as a revision: a round is
        answered from the marks this review left, and a ref has to be one the
        repository actually has.

        Raises:
            UnknownVersionError: when nothing this review offers answers to it.
        """
        if key == REVIEW_KEY:
            return review_base

        if key.startswith(ROUND_PREFIX):
            tree = self._trees(snapshots).get(key)
            if tree is None:
                msg = f"this review has no mark for {key}"
                raise UnknownVersionError(msg)
            return tree

        if key.startswith(REF_PREFIX):
            name = key.removeprefix(REF_PREFIX)
            # Checked here as well as when the refs are listed: what reaches
            # `git diff` must never be able to arrive as an option, and a ref
            # can be written between the listing and the asking
            if name.startswith("-"):
                msg = f"{name} cannot be a base: a revision may not begin with a dash"
                raise UnknownVersionError(msg)
            if name != "HEAD" and name not in {ref.name for ref in await self._git.list_refs(path)}:
                msg = f"{name} is not a branch or tag of this repository"
                raise UnknownVersionError(msg)
            return name

        msg = f"nothing here is compared against {key}"
        raise UnknownVersionError(msg)

    def _trees(self, snapshots: list[TreeSnapshot]) -> dict[str, str]:
        """The tree each round's key stands for."""
        trees: dict[str, str] = {}
        for mark in snapshots:
            trees.setdefault(f"{ROUND_PREFIX}{mark.round}", mark.tree)
        return trees

    async def _counts(self, path: Path, bases: dict[str, str]) -> dict[str, int]:
        """How many files differ from each base, when git will say.

        The count is the reason to pick one base over another, so it is worth
        one pass over the tree — but only one, which is why every base is
        asked at once.
        """
        try:
            # Asked once each: two rounds whose tree never moved are one tree
            changed = await self._git.changed_since(path, list(dict.fromkeys(bases.values())))
        except GitError as e:
            log.warning("counts_refused", reason=str(e))
            return {}
        return {key: len(changed[base]) for key, base in bases.items() if base in changed}
