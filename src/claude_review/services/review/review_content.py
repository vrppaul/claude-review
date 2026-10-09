"""One take of what is under review: its files, the anchors read against them, and the tree they were taken from."""

from claude_review.domain.models import DiffFile, TreeState
from claude_review.services.anchor_service import AnchorService


class ReviewContent:
    """What the review holds between two takes of it, replaced whole by the next.

    Whatever reads it reads one take: the files and the anchors read against
    them are never from two different ones.
    """

    def __init__(self, files: list[DiffFile], tree: TreeState) -> None:
        self._files = files
        self._anchors = AnchorService.of_diff(files)
        # The working tree as it stood when these files were taken; what the
        # watcher compares against. Empty for content no repository holds.
        self._tree = tree

    @property
    def files(self) -> list[DiffFile]:
        return list(self._files)

    @property
    def paths(self) -> frozenset[str]:
        return frozenset(file.path for file in self._files)

    @property
    def anchors(self) -> AnchorService:
        return self._anchors

    @property
    def tree(self) -> TreeState:
        return self._tree
