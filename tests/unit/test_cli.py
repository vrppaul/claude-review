"""Tests for CLI argument handling."""

from click.testing import CliRunner

from claude_review.cli import main


def test_help_shows_usage() -> None:
    """--help prints usage without errors."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])

    assert result.exit_code == 0
    assert "Browser-based code review tool" in result.output


def test_files_and_path_mutually_exclusive() -> None:
    """--files and positional path cannot be used together."""
    runner = CliRunner()
    # Both __file__ (exists) and "." (exists) to bypass click.Path validation
    result = runner.invoke(main, ["--files", __file__, "."])

    assert result.exit_code != 0
    assert "cannot be used together" in result.output
