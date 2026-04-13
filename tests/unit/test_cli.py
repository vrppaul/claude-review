"""Tests for CLI argument handling."""

from click.testing import CliRunner

from claude_review.cli import main


def test_help_shows_usage() -> None:
    """--help prints usage without errors."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])

    assert result.exit_code == 0
    assert "Browser-based code review tool" in result.output


def test_diff_subcommand_in_help() -> None:
    """diff subcommand appears in help output."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])

    assert "diff" in result.output
    assert "files" in result.output
    assert "transcript" in result.output


def test_diff_help_shows_base_option() -> None:
    """diff --help shows the --base option."""
    runner = CliRunner()
    result = runner.invoke(main, ["diff", "--help"])

    assert result.exit_code == 0
    assert "--base" in result.output


def test_files_requires_paths() -> None:
    """files subcommand requires at least one path argument."""
    runner = CliRunner()
    result = runner.invoke(main, ["files"])

    assert result.exit_code != 0


def test_transcript_requires_path() -> None:
    """transcript subcommand requires a path argument."""
    runner = CliRunner()
    result = runner.invoke(main, ["transcript"])

    assert result.exit_code != 0
