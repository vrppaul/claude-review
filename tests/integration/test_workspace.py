"""What a review leaves behind when it ends.

The trees written at every round go: they hold a copy of every untracked
file. The images pasted into it stay: the last round names them, and the
agent reads that round only after the review has ended.
"""

import tempfile
from pathlib import Path

import pytest

from claude_review.cli import _workspace


@pytest.fixture(autouse=True)
def temporary_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Keep what the review writes under this test's own directory."""
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    return tmp_path


def test_pasted_images_outlive_the_review_and_the_trees_do_not(
    tmp_git_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with _workspace(tmp_git_repo) as workspace:
        assert workspace.objects is not None
        (workspace.objects / "blob").write_bytes(b"a copy of an untracked file")
        (workspace.images / "shot.png").write_bytes(b"\x89PNG")

    assert not workspace.objects.exists()
    assert (workspace.images / "shot.png").exists()
    assert str(workspace.images) in capsys.readouterr().err


def test_a_review_nobody_pasted_into_leaves_nothing(capsys: pytest.CaptureFixture[str]) -> None:
    with _workspace(None) as workspace:
        assert workspace.objects is None

    assert not workspace.images.exists()
    assert capsys.readouterr().err == ""
