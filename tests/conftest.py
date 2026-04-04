"""Shared fixtures for tests."""

from pathlib import Path

import pytest

from tests.helpers import git


@pytest.fixture
def tmp_git_repo(tmp_path: Path) -> Path:
    """Create a temporary git repo with an initial commit."""
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.email", "test@test.com")
    git(tmp_path, "config", "user.name", "Test")

    (tmp_path / "initial.txt").write_text("initial content\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "initial")

    return tmp_path
