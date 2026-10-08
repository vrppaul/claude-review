"""Tests for CLI argument handling."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from claude_review.cli import (
    _diff_seed,
    _diff_title,
    _files_seed,
    _files_title,
    _reader_files,
    _render_context,
    _stable_port,
    _transcript_title,
    main,
)
from claude_review.domain.models import CommentSeverity, Turn, TurnAuthor
from tests.helpers import line_anchor, thread


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


def test_files_title_names_what_was_opened() -> None:
    assert _files_title([Path("docs/plan.md")]) == "plan.md"
    assert _files_title([Path("b.py"), Path("a.md")]) == "a.md, b.py"
    assert (
        _files_title([Path(name) for name in ("e.md", "d.md", "c.md", "b.md", "a.md")]) == "a.md, b.md, c.md + 2 more"
    )


def test_transcript_title_names_the_conversation() -> None:
    assert _transcript_title(Path("/tmp/sessions/abc123.jsonl")) == "Conversation abc123"


def test_reopening_the_same_review_lands_on_the_same_port() -> None:
    """The port is the origin, and the origin is where a draft is kept."""
    first = _stable_port(_diff_seed(Path("/home/dev/project"), "HEAD~3"))
    again = _stable_port(_diff_seed(Path("/home/dev/project"), "HEAD~3"))

    assert first == again


def test_a_different_review_gets_a_different_port() -> None:
    """Two repositories reopened side by side must not share a draft."""
    project = _stable_port(_diff_seed(Path("/home/dev/project"), None))
    other = _stable_port(_diff_seed(Path("/home/dev/other"), None))
    since_a_tag = _stable_port(_diff_seed(Path("/home/dev/project"), "v1.0.0"))

    assert project != other
    assert project != since_a_tag


def test_the_same_files_in_another_order_are_the_same_review() -> None:
    assert _files_seed([Path("/docs/a.md"), Path("/docs/b.md")]) == _files_seed(
        [Path("/docs/b.md"), Path("/docs/a.md")]
    )


def test_files_that_start_alike_are_a_different_review() -> None:
    """Same first file, same count: still another set of files, and another draft."""
    assert _files_seed([Path("/docs/a.md"), Path("/docs/b.md")]) != _files_seed(
        [Path("/docs/a.md"), Path("/docs/c.md")]
    )


def test_a_derived_port_stays_out_of_the_way() -> None:
    """High enough to be free of well-known services and of ephemeral ports."""
    port = _stable_port(_diff_seed(Path("/home/dev/project"), None))

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
    # A thread as the server tells it, so this reads what the agent is handed
    "threads": [
        thread(
            line_anchor("src/routes.py", 118, 130, quote=["    return event"]),
            "Does a round overtake a question?\nAnd if it does, what then?",
            thread_id="comment-4",
            severity=CommentSeverity.QUESTION,
            turns=[Turn(author=TurnAuthor.AUTHOR, body="It cannot: one queue.", round=2)],
        ).model_dump(mode="json")
    ],
    "panel": [{"message_id": "panel-1", "author": "reader", "text": "Run the tests", "at": 1, "images": []}],
}


def test_catching_up_costs_a_line_a_thread() -> None:
    """An index is what makes catching up cheaper than being handed the review."""
    printed = _render_context(SEEN, whole=False)

    assert "round 3 · 7 files" in printed
    assert "1 threads, 1 open · panel: 1 messages" in printed
    assert "comment-4  `src/routes.py`:118-130  question · 1 turns" in printed
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


def test_an_image_said_in_the_panel_is_listed_as_a_file_to_open() -> None:
    """The words alone would leave "look at this" pointing at nothing."""
    image = "/tmp/tmp0a1b.claude-review/images/0a1b.png"
    said = {"message_id": "panel-1", "author": "reader", "text": "", "at": 1, "images": [image]}

    printed = _render_context({**SEEN, "panel": [said]}, whole=False)

    assert "you: (image)" in printed
    assert f"image: {image}" in printed


def test_the_reader_files_follow_the_base_directories_the_environment_names(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))

    files = _reader_files()

    assert files.settings == tmp_path / "config" / "claude-review" / "settings.json"
    assert files.guide == tmp_path / "state" / "claude-review" / "guide.json"


def test_a_relative_base_directory_is_ignored_for_the_home_directory(monkeypatch: pytest.MonkeyPatch) -> None:
    """A relative one would point somewhere different from every directory a review starts in."""
    monkeypatch.setenv("XDG_CONFIG_HOME", "config")
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)

    files = _reader_files()

    assert files.settings == Path.home() / ".config" / "claude-review" / "settings.json"
    assert files.guide == Path.home() / ".local" / "state" / "claude-review" / "guide.json"
