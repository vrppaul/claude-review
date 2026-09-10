"""Tests for CLI argument handling."""

from pathlib import Path

from click.testing import CliRunner

from claude_review.cli import (
    _diff_title,
    _files_title,
    _render_context,
    _stable_port,
    _transcript_title,
    main,
)


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


def test_reopening_the_same_review_lands_on_the_same_port() -> None:
    """The port is the origin, and the origin is where a draft is kept."""
    first = _stable_port(Path("/home/dev/project"), "HEAD~3")
    again = _stable_port(Path("/home/dev/project"), "HEAD~3")

    assert first == again


def test_a_different_review_gets_a_different_port() -> None:
    """Two repositories reopened side by side must not share a draft."""
    project = _stable_port(Path("/home/dev/project"), None)
    other = _stable_port(Path("/home/dev/other"), None)
    since_a_tag = _stable_port(Path("/home/dev/project"), "v1.0.0")

    assert project != other
    assert project != since_a_tag


def test_a_derived_port_stays_out_of_the_way() -> None:
    """High enough to be free of well-known services and of ephemeral ports."""
    port = _stable_port(Path("/home/dev/project"), None)

    assert 40000 <= port <= 60000


def test_round_subcommand_in_help() -> None:
    """The half that retakes the diff is discoverable from the CLI."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])

    assert "round" in result.output


def test_the_panel_commands_are_in_help() -> None:
    """An agent driving the review has to find them without being told."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])

    assert "say" in result.output
    assert "status" in result.output


SEEN = {
    "title": "claude-review: uncommitted changes",
    "round": 3,
    "file_count": 7,
    "answerer_attached": True,
    "agent": {"model": "opus-5", "context": "45% of 1M", "at": 1},
    "threads": [
        {
            "thread_id": "comment-4",
            "file": "src/routes.py",
            "side": "new",
            "start_line": 118,
            "end_line": 130,
            "quote": ["    return event"],
            "body": "Does a round overtake a question?\nAnd if it does, what then?",
            "history": [{"author": "author", "body": "It cannot: one queue.", "round": 2}],
            "severity": "question",
            "resolved": False,
            "outdated": False,
            "raised_by": "reader",
        }
    ],
    "panel": [{"message_id": "panel-1", "author": "reader", "text": "Run the tests", "at": 1}],
}


def test_catching_up_costs_a_line_a_thread() -> None:
    """An index is what makes catching up cheaper than being handed the review."""
    printed = _render_context(SEEN, whole=False)

    assert "round 3 · 7 files" in printed
    assert "1 threads, 1 open · panel: 1 messages" in printed
    assert "comment-4  src/routes.py:118-130  question · 1 turns" in printed
    # The first line of the comment, and not the second
    assert "Does a round overtake a question?" in printed
    assert "And if it does" not in printed
    # Nor what was said in the thread: that is what asking for it is for
    assert "one queue" not in printed


def test_a_thread_asked_for_by_name_comes_in_full() -> None:
    """The index is for choosing what to read; this is the reading."""
    printed = _render_context({**SEEN, "threads": SEEN["threads"]}, whole=True)

    assert "And if it does, what then?" in printed
    assert "author: It cannot: one queue." in printed
    assert "lines:     return event" in printed


def test_a_review_nobody_answers_says_so() -> None:
    """Because it changes what the agent should do next, or whether it can."""
    printed = _render_context({**SEEN, "answerer_attached": False}, whole=False)

    assert "nobody answering" in printed
