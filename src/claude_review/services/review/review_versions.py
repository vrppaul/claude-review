"""What one review's diff can be compared against, and the marks it leaves to make that possible."""

from pathlib import Path

import structlog

from claude_review.domain.exceptions import GitError, UnknownVersionError
from claude_review.domain.models import ChangesSince, ReviewVersion, TreeSnapshot, VersionKind
from claude_review.domain.protocols import Clock, GitRepositoryProtocol

log = structlog.get_logger()

REVIEW_KEY = "review"
ROUND_PREFIX = "round:"
REF_PREFIX = "ref:"
UNCOMMITTED = "uncommitted changes"
# The ref every repository with a commit has, offered first among the refs
HEAD = "HEAD"


class ReviewVersions:
    """The bases one review offers, and what has moved since each of them.

    The right-hand side of a review's diff is always the working tree, so a
    base is the only thing there is to choose. A ref is there to be chosen
    already; a round is not, until the tree it was read at has been written
    down — which is what `mark` does, each time the diff is taken.

    Everything here answers "if it can be said": a repository that will not
    write a tree — one mid-merge, whose index has unresolved entries — costs
    the review its versions, never the review itself.
    """

    def __init__(
        self, git_repository: GitRepositoryProtocol, clock: Clock, root: Path, review_base: str | None
    ) -> None:
        self._git = git_repository
        self._clock = clock
        self._root = root
        # What the review was opened against; None for uncommitted changes
        self._review_base = review_base
        # The tree behind every diff this review has taken, oldest first. The
        # first of each round is a base the reader can go back to.
        self._marks: list[TreeSnapshot] = []

    async def mark(self, round_number: int) -> None:
        """Write down the tree the diff has just been taken from, as part of a round."""
        try:
            tree = await self._git.snapshot(self._root)
        except GitError as e:
            log.warning("snapshot_refused", round=round_number, reason=str(e))
            return
        self._marks.append(TreeSnapshot(round=round_number, tree=tree, at=self._clock.now()))

    async def changed_since_round_began(self, round_number: int) -> ChangesSince | None:
        """Which files have moved since a round began, if it can be said.

        None is not an empty list: one says nothing has changed, the other
        that there is no way to know — and a reader who is told nothing
        changed stops looking.
        """
        began = self._began(round_number)
        if began is None:
            return None
        try:
            paths = (await self._git.changed_since(self._root, [began.tree])).get(began.tree)
        except GitError as e:
            log.warning("changed_since_refused", tree=began.tree, reason=str(e))
            return None
        return ChangesSince(since_round=began.round, paths=paths) if paths is not None else None

    def phrase_of(self, key: str) -> str:
        """What the header says while this base is the one in force.

        Written here rather than in the browser, and answered without asking
        git anything, so a review can say what it is showing before it has
        looked up everything it could show instead.
        """
        if key == REVIEW_KEY:
            return f"changes since {self._review_base}" if self._review_base else UNCOMMITTED
        if key.startswith(ROUND_PREFIX):
            return f"changes since round {key.removeprefix(ROUND_PREFIX)}"
        name = key.removeprefix(REF_PREFIX)
        return UNCOMMITTED if name == HEAD else f"changes since {name}"

    async def offer(self) -> list[ReviewVersion]:
        """Every base this review can be compared against, in reading order.

        What it opened with comes first — it is the review, and everything
        else is a way of reading part of it — then its own rounds, newest
        knowledge last, then what the repository had before any of this.
        """
        review = ReviewVersion(
            key=REVIEW_KEY,
            kind=VersionKind.REVIEW,
            label=self._review_base or UNCOMMITTED,
            phrase=self.phrase_of(REVIEW_KEY),
        )
        rounds = self._rounds()
        # A ref the review already opened against is that first entry; it is
        # not a second way of looking at the same thing
        refs = [ref for ref in await self._refs() if ref.label != (self._review_base or HEAD)]

        trees = self._trees()
        counted = await self._counts(
            {REVIEW_KEY: self._review_base or HEAD} | {version.key: trees[version.key] for version in rounds}
        )
        review.changed = counted.get(REVIEW_KEY)
        for version in rounds:
            version.changed = counted.get(version.key)

        # A round nothing has happened since would open an empty screen. The
        # review's own base is never dropped, however little it shows: it is
        # the way back.
        return [review, *[version for version in rounds if version.changed != 0], *refs]

    async def resolve(self, key: str) -> str | None:
        """The revision a key names, as git will understand it.

        Nothing from the query string reaches git as a revision: a round is
        answered from the marks this review left, and a ref has to be one the
        repository actually has.

        Raises:
            UnknownVersionError: when nothing this review offers answers to it.
        """
        if key == REVIEW_KEY:
            return self._review_base

        if key.startswith(ROUND_PREFIX):
            tree = self._trees().get(key)
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
            if name != HEAD and name not in {ref.name for ref in await self._git.list_refs(self._root)}:
                msg = f"{name} is not a branch or tag of this repository"
                raise UnknownVersionError(msg)
            return name

        msg = f"nothing here is compared against {key}"
        raise UnknownVersionError(msg)

    def _began(self, round_number: int) -> TreeSnapshot | None:
        """The mark a round is measured from, and offered as a base.

        The round's own first mark once it has one; before that, the last
        mark left behind, which is where the round began. It has to be the
        same tree `round:N` resolves to, or the count and the screen the
        reader is sent to disagree — "3 files changed since round 2" opening
        a diff of five.
        """
        for mark in self._marks:
            if mark.round == round_number:
                return mark
        return self._marks[-1] if self._marks else None

    def _rounds(self) -> list[ReviewVersion]:
        """One base per round, as that round found the tree.

        The agent may retake the diff several times while one round is being
        written; the round still began once, so the first mark of each is the
        one worth going back to. Whether a round is worth offering is a
        different question, and only what has changed since can answer it.
        """
        began: dict[int, TreeSnapshot] = {}
        for mark in self._marks:
            began.setdefault(mark.round, mark)

        return [
            ReviewVersion(
                key=f"{ROUND_PREFIX}{mark.round}",
                kind=VersionKind.ROUND,
                label=f"round {mark.round}",
                phrase=self.phrase_of(f"{ROUND_PREFIX}{mark.round}"),
                at=mark.at,
            )
            for mark in began.values()
        ]

    async def _refs(self) -> list[ReviewVersion]:
        """The branches and tags this repository can be read against, HEAD first."""
        head = ReviewVersion(
            key=f"{REF_PREFIX}{HEAD}", kind=VersionKind.REF, label=HEAD, phrase=self.phrase_of(f"{REF_PREFIX}{HEAD}")
        )
        listed = [
            ReviewVersion(
                key=f"{REF_PREFIX}{ref.name}",
                kind=VersionKind.REF,
                label=ref.name,
                phrase=self.phrase_of(f"{REF_PREFIX}{ref.name}"),
                at=ref.at,
            )
            for ref in await self._git.list_refs(self._root)
        ]
        return [head, *listed]

    def _trees(self) -> dict[str, str]:
        """The tree each round's key stands for."""
        trees: dict[str, str] = {}
        for mark in self._marks:
            trees.setdefault(f"{ROUND_PREFIX}{mark.round}", mark.tree)
        return trees

    async def _counts(self, bases: dict[str, str]) -> dict[str, int]:
        """How many files differ from each base, when git will say.

        The count is the reason to pick one base over another, so it is worth
        one pass over the tree — but only one, which is why every base is
        asked at once.
        """
        try:
            # Asked once each: two rounds whose tree never moved are one tree
            changed = await self._git.changed_since(self._root, list(dict.fromkeys(bases.values())))
        except GitError as e:
            log.warning("counts_refused", reason=str(e))
            return {}
        return {key: len(changed[base]) for key, base in bases.items() if base in changed}
