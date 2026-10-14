"""One take of what is under review: its files, their lines as anchors read them, and the tree they were taken from."""

from claude_review.domain.models import DiffFile, TreeState
from claude_review.services.anchor_service import LineAnchorHandler

# The take a review is made with, from what its opening read: every take
# after it is counted on from here. A review of a repository takes its diff
# again as it opens, so the first take its page reads is the one after.
FIRST_TAKE = 1


class ReviewContent:
    """What the review holds between two takes of it, replaced whole by the next.

    Whatever reads it reads one take: the files and the line anchors read
    against them are never from two different ones. Takes are numbered as
    they are made, by the take before: what is cut out of one and kept past
    it — the pieces a story shows — says which take it is of, and whoever
    holds it beside a later one can tell.
    """

    def __init__(self, files: list[DiffFile], tree: TreeState, *, take: int) -> None:
        self._files = files
        self._line_anchors = LineAnchorHandler(files)
        # The working tree as it stood when these files were taken; what the
        # watcher compares against. Empty for content no repository holds.
        self._tree = tree
        self._take = take

    @classmethod
    def opening_on(cls, files: list[DiffFile]) -> ReviewContent:
        """The take a review is made with: what its opening read, before any tree was read beside it."""
        return cls(files, tree=frozenset(), take=FIRST_TAKE)

    def on_tree(self, tree: TreeState) -> ReviewContent:
        """This take, with the working tree it is of read at last: the same files, and the same take."""
        return ReviewContent(self._files, tree, take=self._take)

    def taken_again(self, files: list[DiffFile], tree: TreeState) -> ReviewContent:
        """The take after this one: the files as they now are, and the tree they were taken from."""
        return ReviewContent(files, tree, take=self._take + 1)

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
