"""Where every review on the machine keeps what it remembers about its reader, by the XDG base directory rules."""

from pathlib import Path

import pytest

from claude_review.cli.workspace import reader_files


def test_the_reader_files_follow_the_base_directories_the_environment_names(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))

    files = reader_files()

    assert files.settings == tmp_path / "config" / "claude-review" / "settings.json"
    assert files.guide == tmp_path / "state" / "claude-review" / "guide.json"


def test_a_relative_base_directory_is_ignored_for_the_home_directory(monkeypatch: pytest.MonkeyPatch) -> None:
    """A relative one would point somewhere different from every directory a review starts in."""
    monkeypatch.setenv("XDG_CONFIG_HOME", "config")
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)

    files = reader_files()

    assert files.settings == Path.home() / ".config" / "claude-review" / "settings.json"
    assert files.guide == Path.home() / ".local" / "state" / "claude-review" / "guide.json"
