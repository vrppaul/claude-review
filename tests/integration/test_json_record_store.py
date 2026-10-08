"""A record about the reader kept as a file, shared by every review on the machine.

Several reviews may be open at once, each its own process, and any of them
may write while another reads. A reader must never find half a file.
"""

import asyncio
from pathlib import Path

from claude_review.domain.models import ReaderSettings, Theme
from claude_review.repositories.json_record_store import JsonRecordStore


def _names_in(directory: Path) -> list[str]:
    return sorted(entry.name for entry in directory.iterdir())


async def test_nothing_written_yet_reads_as_nothing(tmp_path: Path) -> None:
    store = JsonRecordStore(tmp_path / "claude-review" / "settings.json", ReaderSettings)

    assert await store.read() is None


async def test_what_was_written_is_read_back(tmp_path: Path) -> None:
    path = tmp_path / "claude-review" / "settings.json"

    await JsonRecordStore(path, ReaderSettings).write(ReaderSettings(theme=Theme.LIGHT))

    assert await JsonRecordStore(path, ReaderSettings).read() == ReaderSettings(theme=Theme.LIGHT)


async def test_a_write_leaves_only_the_record_behind(tmp_path: Path) -> None:
    directory = tmp_path / "claude-review"

    await JsonRecordStore(directory / "settings.json", ReaderSettings).write(ReaderSettings())

    assert _names_in(directory) == ["settings.json"]


async def test_a_file_that_cannot_be_read_counts_as_nothing_written(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text("{ not json")

    assert await JsonRecordStore(path, ReaderSettings).read() is None


async def test_a_choice_a_later_release_added_does_not_spoil_the_rest(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text('{"theme": "dark", "something_new": true}')

    assert await JsonRecordStore(path, ReaderSettings).read() == ReaderSettings(theme=Theme.DARK)


async def test_a_file_that_is_not_text_counts_as_nothing_written(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_bytes(b"\xff\xfe\x00 not utf-8")

    assert await JsonRecordStore(path, ReaderSettings).read() is None


async def test_writes_at_once_leave_one_whole_record(tmp_path: Path) -> None:
    """Every write takes a name of its own before it takes the record's."""
    path = tmp_path / "settings.json"
    store = JsonRecordStore(path, ReaderSettings)

    await asyncio.gather(*(store.write(ReaderSettings(theme=theme)) for theme in Theme))

    assert await store.read() in [ReaderSettings(theme=theme) for theme in Theme]
    assert _names_in(tmp_path) == ["settings.json"]
