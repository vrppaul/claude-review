"""What a review leaves behind when it ends.

The trees written at every round go: they hold a copy of every untracked
file. The images pasted into it stay: the last round names them, and the
agent reads that round only after the review has ended.
"""

import tempfile
from pathlib import Path
from typing import override

import pytest

from claude_review.cli.terminal_announcer import TerminalAnnouncer
from claude_review.hosting.announcer import ReviewAnnouncer
from claude_review.hosting.workspace import review_workspace
from tests.helpers import PNG


class ImagesNoted(ReviewAnnouncer):
    """Whoever started the review, as a test: it notes where the images were left, and hears nothing else."""

    def __init__(self) -> None:
        self.left_in: list[Path] = []

    @override
    async def listening_at(self, url: str) -> None:
        """These reviews are never served."""

    @override
    def images_left_in(self, directory: Path) -> None:
        self.left_in.append(directory)


@pytest.fixture(autouse=True)
def temporary_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Keep what the review writes under this test's own directory."""
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    return tmp_path


def test_pasted_images_outlive_the_review_and_the_trees_do_not() -> None:
    """Whoever started the review is told where the images are, since the agent opens them later."""
    told = ImagesNoted()
    with review_workspace(writes_trees=True, announcer=told) as workspace:
        assert workspace.objects is not None
        (workspace.objects / "blob").write_bytes(b"a copy of an untracked file")
        (workspace.images / "shot.png").write_bytes(PNG)

    assert not workspace.objects.exists()
    assert (workspace.images / "shot.png").exists()
    assert told.left_in == [workspace.images]


def test_a_review_nobody_pasted_into_leaves_nothing_and_says_nothing() -> None:
    told = ImagesNoted()
    with review_workspace(writes_trees=False, announcer=told) as workspace:
        assert workspace.objects is None

    assert not workspace.images.exists()
    assert told.left_in == []


def test_the_terminal_is_told_where_the_images_stay(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    TerminalAnnouncer(open_browser=False).images_left_in(tmp_path)

    assert str(tmp_path) in capsys.readouterr().err
