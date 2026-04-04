"""Shared test utilities."""

import subprocess
from pathlib import Path


def git(repo: Path, *args: str) -> None:
    """Run a git command in the given repo."""
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)
