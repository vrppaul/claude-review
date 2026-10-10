"""Functional requirement tests for what a review remembers about its reader.

A reader's choices — the theme, how a diff is laid out — belong to them,
not to one review: every review on the machine starts from them, and a
change in one is there in the next.
"""

import asyncio
from typing import override

from pydantic import BaseModel

from claude_review.domain.models import DiffLayout, ReaderSettings, Theme
from claude_review.domain.protocols import RecordStoreProtocol
from claude_review.services.reader_record_service import ReaderRecordService


class SettingsChanged(BaseModel):
    """Some of the reader's choices, changed; the rest left as they are."""

    theme: Theme | None = None
    diff_layout: DiffLayout | None = None
    ignore_whitespace: bool | None = None


class KeptInMemory(RecordStoreProtocol[ReaderSettings]):
    """A store that keeps its one record for as long as the test runs."""

    def __init__(self, record: ReaderSettings | None = None) -> None:
        self.record = record

    @override
    async def read(self) -> ReaderSettings | None:
        return self.record

    @override
    async def write(self, record: ReaderSettings) -> None:
        self.record = record


async def test_a_reader_who_never_chose_gets_nothing_back() -> None:
    assert await ReaderRecordService(KeptInMemory(), ReaderSettings).read() is None


async def test_changing_one_choice_keeps_the_others() -> None:
    store = KeptInMemory(ReaderSettings(theme=Theme.DARK))

    changed = await ReaderRecordService(store, ReaderSettings).change(SettingsChanged(diff_layout=DiffLayout.SPLIT))

    assert (changed.theme, changed.diff_layout) == (Theme.DARK, DiffLayout.SPLIT)
    assert store.record == changed


async def test_the_first_choice_starts_from_what_a_new_reader_gets() -> None:
    store = KeptInMemory()

    changed = await ReaderRecordService(store, ReaderSettings).change(SettingsChanged(ignore_whitespace=True))

    assert changed == ReaderSettings(ignore_whitespace=True)


async def test_two_changes_at_once_both_stay() -> None:
    """Two clicks in quick succession must not put back what the first one changed."""
    store = SlowToWrite()
    service = ReaderRecordService(store, ReaderSettings)

    await asyncio.gather(
        service.change(SettingsChanged(theme=Theme.DARK)), service.change(SettingsChanged(diff_layout=DiffLayout.SPLIT))
    )

    assert store.record == ReaderSettings(theme=Theme.DARK, diff_layout=DiffLayout.SPLIT)


class SlowToWrite(KeptInMemory):
    """A store whose write lets everything else run first, as a disk write does."""

    @override
    async def write(self, record: ReaderSettings) -> None:
        await asyncio.sleep(0)
        self.record = record
