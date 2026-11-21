"""The names outlining files' contents, kept in one SQLite file every review of the user reads and writes.

SQLite, as reviews of the same user may run at once and each writes what it
outlined: the file's own locking keeps their writes whole, where a file per
content would leave thousands of files and a JSON file one writer at a time.
"""

import asyncio
import sqlite3
from contextlib import closing
from itertools import batched
from pathlib import Path
from typing import override

import structlog

from claude_review.domain.interfaces import OutlinesKept

log = structlog.get_logger()

# Who may enter the directory the file is in: the user alone, as the names come from files nobody committed too
ONLY_THE_USER = 0o700
# What the file holds, and how it lets a review read while another writes
SCHEMA = "CREATE TABLE IF NOT EXISTS outlines (key TEXT PRIMARY KEY, outline BLOB NOT NULL)"
READ_WHILE_WRITTEN = "PRAGMA journal_mode=WAL"
READ = "SELECT key, outline FROM outlines WHERE key IN ({marks})"
KEEP = "INSERT OR REPLACE INTO outlines (key, outline) VALUES (?, ?)"
# How many keys one query asks about: well under the most variables SQLite takes in one statement
KEYS_ASKED_AT_ONCE = 500
# How long a review waits for another writing the file before it gives up the write, in seconds
WAITS_FOR_ANOTHER_SECONDS = 5.0


class OutlinesFile(OutlinesKept):
    """Outlines kept in a SQLite file, made the first time anything is kept."""

    def __init__(self, path: Path) -> None:
        self._path = path

    @override
    async def read(self, keys: list[str]) -> dict[str, bytes]:
        """Nothing where the file cannot be read: what was kept is outlined again."""
        try:
            return await asyncio.to_thread(self._read, keys)
        except sqlite3.Error:
            log.warning("outlines_unread", path=str(self._path), exc_info=True)
            return {}

    @override
    async def keep(self, kept: dict[str, bytes]) -> None:
        """Kept nowhere where the file cannot be written: the next review outlines the same files again."""
        try:
            await asyncio.to_thread(self._keep, kept)
        except sqlite3.Error:
            log.warning("outlines_not_kept", path=str(self._path), exc_info=True)

    def _read(self, keys: list[str]) -> dict[str, bytes]:
        """What is kept under each key, nothing where the file is not made yet."""
        if not keys or not self._path.exists():
            return {}
        with closing(self._connected()) as connection:
            return {
                key: outline
                for asked in batched(keys, KEYS_ASKED_AT_ONCE, strict=False)
                for key, outline in connection.execute(READ.format(marks=", ".join("?" * len(asked))), asked)
            }

    def _keep(self, kept: dict[str, bytes]) -> None:
        """Keep each under its key, making the file and its directory the first time."""
        if not kept:
            return
        self._path.parent.mkdir(mode=ONLY_THE_USER, parents=True, exist_ok=True)
        with closing(self._connected()) as connection, connection:
            connection.executemany(KEEP, kept.items())

    def _connected(self) -> sqlite3.Connection:
        """A connection to the file, its table made if another review made the file and not yet the table."""
        connection = sqlite3.connect(self._path, timeout=WAITS_FOR_ANOTHER_SECONDS)
        connection.execute(READ_WHILE_WRITTEN)
        connection.execute(SCHEMA)
        return connection
