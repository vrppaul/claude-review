"""A record about the reader, kept as one JSON file shared by every review."""

import asyncio
import os
import tempfile
from pathlib import Path
from typing import override

import structlog
from pydantic import BaseModel, ValidationError

from claude_review.domain.protocols import RecordStoreProtocol

log = structlog.get_logger()

# What every record is written in, whatever the machine's locale says
RECORD_ENCODING = "utf-8"


class JsonRecordStore[Record: BaseModel](RecordStoreProtocol[Record]):
    """Keeps one record as a JSON file, replaced whole on every write.

    Several reviews can be open at once, each in its own process. A write goes
    to a file of its own first and then takes the record's name in one step,
    so whoever reads finds the old record or the new one, never half of one.
    """

    def __init__(self, path: Path, record_type: type[Record]) -> None:
        self._path = path
        self._record_type = record_type

    @override
    async def read(self) -> Record | None:
        try:
            text = await asyncio.to_thread(self._path.read_text, encoding=RECORD_ENCODING)
        except FileNotFoundError:
            return None
        except (OSError, UnicodeDecodeError) as error:
            log.warning("record_unreadable", path=str(self._path), reason=str(error))
            return None
        try:
            return self._record_type.model_validate_json(text)
        except ValidationError as error:
            # A file edited by hand into nonsense costs the reader their
            # choices, not the review
            log.warning("record_unreadable", path=str(self._path), reason=str(error))
            return None

    @override
    async def write(self, record: Record) -> None:
        await asyncio.to_thread(self._replace, record.model_dump_json(indent=2))

    def _replace(self, text: str) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        # A name no other write can share, beside the record so the rename
        # stays on one file system
        handle, written = tempfile.mkstemp(dir=self._path.parent, prefix=f".{self._path.name}.")
        try:
            with os.fdopen(handle, "w", encoding=RECORD_ENCODING) as file:
                file.write(text)
            Path(written).replace(self._path)
        except BaseException:
            Path(written).unlink(missing_ok=True)
            raise
