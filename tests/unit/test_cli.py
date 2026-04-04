"""Tests for CLI argument parsing."""

from claude_review.cli import parse_args


def test_default_args() -> None:
    """Default args: port=0, no_open=False, path='.'."""
    args = parse_args([])
    assert args.port == 0
    assert args.no_open is False
    assert args.path == "."


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
