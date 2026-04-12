"""Tests for CLI argument parsing."""

from pathlib import Path

import pytest

from claude_review.cli import parse_args


def test_default_args() -> None:
    """Default args: port=0, no_open=False, path=None, files=None."""
    args = parse_args([])
    assert args.port == 0
    assert args.no_open is False
    assert args.path is None
    assert args.files is None


def test_custom_port() -> None:
    """--port sets the port."""
    args = parse_args(["--port", "8080"])
    assert args.port == 8080


def test_no_open_flag() -> None:
    """--no-open disables browser opening."""
    args = parse_args(["--no-open"])
    assert args.no_open is True


def test_custom_path() -> None:
    """Positional path argument."""
    args = parse_args(["/some/repo"])
    assert args.path == "/some/repo"


def test_all_args_combined() -> None:
    """All args together."""
    args = parse_args(["--port", "3000", "--no-open", "/my/project"])
    assert args.port == 3000
    assert args.no_open is True
    assert args.path == "/my/project"


def test_files_flag_single() -> None:
    """--files with a single file."""
    args = parse_args(["--files", "plan.md"])
    assert args.files == [Path("plan.md")]
    assert args.path is None


def test_files_flag_multiple() -> None:
    """--files with multiple files."""
    args = parse_args(["--files", "a.md", "b.md", "c.md"])
    assert args.files == [Path("a.md"), Path("b.md"), Path("c.md")]


def test_files_and_path_mutually_exclusive() -> None:
    """--files and positional path cannot be used together."""
    with pytest.raises(SystemExit):
        parse_args(["/some/repo", "--files", "plan.md"])
