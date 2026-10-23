"""What a review leaves behind when it ends.

What it kept of itself stays until it is finished: the trees written at
every round hold a copy of every untracked file, and the story told is
followed from them when the review is opened again. So they are kept where
only the user can reach. The images pasted into it stay: the last round
names them, and the agent reads that round only after the review has ended.
"""

import os
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import override

import pytest

from claude_review.cli.terminal_announcer import TerminalAnnouncer
from claude_review.hosting.announcer import ReviewAnnouncer
from claude_review.hosting.errors import WorkspaceRefusedError
from claude_review.hosting.workspace import KEPT_BY_EVERY_REVIEW, ONLY_THE_USER, review_workspace
from tests.helpers import PNG

# Two reviews, by the short names of their identities, as the command line names each
A_REVIEW = "5e1f0c2a"
ANOTHER_REVIEW = "9a7b3d64"
# A copy of an untracked file, as the trees of a review of a repository hold one
UNTRACKED_COPY = "blob"
# What a directory anybody may enter and read is made with
OPEN_TO_EVERYONE = 0o755


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

    @override
    def never_opened(self) -> None:
        """These reviews are never served."""


@pytest.fixture(autouse=True)
def temporary_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Keep what the review writes under this test's own directory."""
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    return tmp_path


async def test_pasted_images_outlive_the_review() -> None:
    """Whoever started the review is told where the images are, since the agent opens them later."""
    told = ImagesNoted()
    async with review_workspace(A_REVIEW, writes_trees=True, announcer=told) as workspace:
        (workspace.images / "shot.png").write_bytes(PNG)

    assert (workspace.images / "shot.png").exists()
    assert told.left_in == [workspace.images]


async def test_a_review_opened_again_finds_the_trees_it_wrote_and_no_other_review_does() -> None:
    """The story told is followed from them: the review is the same one until its reader finishes it."""
    async with review_workspace(A_REVIEW, writes_trees=True, announcer=ImagesNoted()) as first:
        (first.objects / UNTRACKED_COPY).write_bytes(b"a copy of an untracked file")

    async with (
        review_workspace(A_REVIEW, writes_trees=True, announcer=ImagesNoted()) as again,
        review_workspace(ANOTHER_REVIEW, writes_trees=True, announcer=ImagesNoted()) as another,
    ):
        found = {
            "again": (again.objects / UNTRACKED_COPY).exists(),
            "another": (another.objects / UNTRACKED_COPY).exists(),
        }

    assert found == {"again": True, "another": False}


async def test_a_review_nobody_pasted_into_leaves_no_images_and_says_nothing() -> None:
    told = ImagesNoted()
    async with review_workspace(A_REVIEW, writes_trees=False, announcer=told) as workspace:
        assert workspace.objects is None

    assert not workspace.images.exists()
    assert told.left_in == []


def _kept_by_every_review_in(temporary: Path) -> Path:
    """Where every review of the user the review runs as keeps its own, in this temporary directory."""
    return temporary / KEPT_BY_EVERY_REVIEW.format(user=os.getuid())


def _a_link_in_its_place(temporary: Path, _monkeypatch: pytest.MonkeyPatch) -> None:
    """A link where every review keeps its own, to wherever its maker chose."""
    elsewhere = temporary / "elsewhere"
    elsewhere.mkdir()
    _kept_by_every_review_in(temporary).symlink_to(elsewhere)


def _made_by_another_user(temporary: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The directory as another user made it first: made here, and the review run as a user of the next id."""
    this_user = os.getuid()
    monkeypatch.setattr(os, "getuid", lambda: this_user + 1)
    _kept_by_every_review_in(temporary).mkdir(mode=ONLY_THE_USER)


def _left_open_to_other_users(temporary: Path, _monkeypatch: pytest.MonkeyPatch) -> None:
    """The user's own directory, which anybody may enter and read."""
    kept = _kept_by_every_review_in(temporary)
    kept.mkdir()
    kept.chmod(OPEN_TO_EVERYONE)


# Where every review keeps its own as another user could have left it, by the name a failing case is reported by
LEFT_FOR_A_REVIEW = {
    "a link in its place": _a_link_in_its_place,
    "another user's directory": _made_by_another_user,
    "a directory open to other users": _left_open_to_other_users,
}


@pytest.mark.parametrize("left", LEFT_FOR_A_REVIEW.values(), ids=LEFT_FOR_A_REVIEW.keys())
async def test_what_a_review_keeps_is_never_kept_where_another_user_could_reach_it(
    left: Callable[[Path, pytest.MonkeyPatch], None], temporary_directory: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """It holds copies of files nobody committed, so nothing is written there."""
    left(temporary_directory, monkeypatch)

    with pytest.raises(WorkspaceRefusedError):
        async with review_workspace(A_REVIEW, writes_trees=True, announcer=ImagesNoted()):
            pass


def test_the_terminal_is_told_where_the_images_stay(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    TerminalAnnouncer(open_browser=False).images_left_in(tmp_path)

    assert str(tmp_path) in capsys.readouterr().err
