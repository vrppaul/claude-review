"""One take of what is under review: its files, their lines as anchors read them, and the tree they were taken from."""

from abc import ABC, abstractmethod

from claude_review.domain.models import FIRST_TAKE, DiffFile, TreeState
from claude_review.services.anchor_service import LineAnchorHandler


class ReviewContent:
    """What the review holds between two takes of it, replaced whole by the next.

    Whatever reads it reads one take: the files and the line anchors read
    against them are never from two different ones. Takes are numbered as
    they are made, by the take before: what is cut out of one and kept past
    it — the pieces a story shows — says which take it is of, and whoever
    holds it beside a later one can tell.
    """

    def __init__(self, files: list[DiffFile], tree: TreeState, *, take: int, written_as: str | None) -> None:
        self._files = files
        self._line_anchors = LineAnchorHandler(files)
        # The working tree as it stood when these files were taken; what the
        # watcher compares against. Empty for content no repository holds.
        self._tree = tree
        self._take = take
        # The tree git wrote these files' working tree down as, which a later
        # take is compared with: None where none was written
        self._written_as = written_as

    @classmethod
    def opening_on(cls, files: list[DiffFile]) -> ReviewContent:
        """The take a review is made with: what its opening read, before any tree was read or written beside it."""
        return cls(files, tree=frozenset(), take=FIRST_TAKE, written_as=None)

    def on_tree(self, tree: TreeState) -> ReviewContent:
        """This take, with the working tree it is of read at last: the same files, and the same take."""
        return ReviewContent(self._files, tree, take=self._take, written_as=self._written_as)

    def taken_again(self, files: list[DiffFile], tree: TreeState, *, written_as: str | None) -> ReviewContent:
        """The take after this one: the files as they now are, the tree they were taken from, and how it was written."""
        return ReviewContent(files, tree, take=self._take + 1, written_as=written_as)

    @property
    def files(self) -> list[DiffFile]:
        return list(self._files)

    @property
    def paths(self) -> frozenset[str]:
        return frozenset(file.path for file in self._files)

    @property
    def line_anchors(self) -> LineAnchorHandler:
        return self._line_anchors

    @property
    def tree(self) -> TreeState:
        return self._tree

    @property
    def take(self) -> int:
        """Which take of the review this is, counted from the one it was made with."""
        return self._take

    @property
    def written_as(self) -> str | None:
        """The tree this take's working tree was written down as: None where git wrote none."""
        return self._written_as


class TakesCompared(ABC):
    """What changed between two takes of the review's content, by the trees they were written down as.

    The content's source is the one reader of the repository — where it is,
    and how a diff of it is read — so whoever needs two takes compared, the
    story following its code, asks the source and never sees git.
    """

    @abstractmethod
    async def changed_between(self, earlier: str, later: str) -> list[DiffFile]:
        """The diff from one take's tree to another's, file by file.

        Raises:
            GitError: if git cannot say it.
            NoRepositoryError: if no repository holds the content.
        """
