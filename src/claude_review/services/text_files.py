"""Plain text files — plans, docs, configs, source code — read for review, each whole."""

import asyncio
from pathlib import Path

from claude_review.domain.models import DiffFile
from claude_review.services.unreadable_content import UnreadableContentError
from claude_review.services.whole_file import whole_file

# What a file reviewed whole is read as: a file that is not is refused, and named
TEXT_ENCODING = "utf-8"


async def read_text_files(paths: list[Path], *, named_from: Path) -> list[DiffFile]:
    """Each file, read whole on a thread rather than the event loop, and named as seen from `named_from`.

    An empty file has nothing to review, and is left out.

    Raises:
        UnreadableContentError: If a path does not point to a readable text file.
    """
    return await asyncio.to_thread(_read_all, paths, named_from)


def _read_all(paths: list[Path], named_from: Path) -> list[DiffFile]:
    files: list[DiffFile] = []
    for path in paths:
        text = _read_text(path)
        if text:
            files.append(whole_file(_name_of(path, named_from), text))
    return files


def _name_of(path: Path, named_from: Path) -> str:
    """The file as the reader would name it.

    A path under the directory the review was opened from reads as
    "docs/plan.md" rather than its full location; one outside it keeps the
    full path, since "../../elsewhere.md" would say less.
    """
    try:
        return str(path.relative_to(named_from))
    except ValueError:
        return str(path)


def _read_text(path: Path) -> str:
    """The file's content as UTF-8 text.

    Raises:
        UnreadableContentError: If the path is missing, is a directory,
            cannot be read, or is not UTF-8 text.
    """
    try:
        return path.read_text(encoding=TEXT_ENCODING)
    except (OSError, UnicodeDecodeError) as error:
        msg = f"Not a readable text file: {path}"
        raise UnreadableContentError(msg) from error
