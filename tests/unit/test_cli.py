"""Tests for CLI argument handling."""

from pathlib import Path

from click.testing import CliRunner

from claude_review.cli import _diff_title, _files_title, _transcript_title, main


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


def test_diff_title_names_the_repository_and_the_range() -> None:
    """The UI header says which repository is under review, and against what."""
    assert _diff_title(Path("/home/pavel/projects/claude-review"), None) == ("claude-review: uncommitted changes")
    assert _diff_title(Path("/home/pavel/projects/claude-review"), "HEAD~3") == ("claude-review: changes since HEAD~3")


def test_files_title_counts_what_was_opened() -> None:
    assert _files_title([Path("plan.md")]) == "1 file"
    assert _files_title([Path("a.md"), Path("b.py")]) == "2 files"


def test_transcript_title_names_the_conversation() -> None:
    assert _transcript_title(Path("/tmp/sessions/abc123.jsonl")) == "Conversation abc123"
