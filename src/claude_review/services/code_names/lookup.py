"""Where a name stands in the take on screen, read from the tree git wrote it down as.

No index is kept, and no language server runs: each lookup asks git which
of the take's files hold the word, and reads only those. A usual name is in
a handful of files and a frequent one in a few hundred, and an index of the
whole tree would go stale with every round.
"""

import asyncio
import time
from pathlib import Path
from typing import assert_never

import structlog

from claude_review.domain.code_names import CodePlace, NameFound, NamePlace
from claude_review.domain.exceptions import FileNotInReviewError
from claude_review.domain.interfaces import TreesRead
from claude_review.domain.models import DiffFile, LineSide
from claude_review.services.code_names.reading import places_of, word_at
from claude_review.services.code_names.timing import milliseconds_between

log = structlog.get_logger()


class NameLookup:
    """Looks names up in the takes of one repository's review."""

    def __init__(self, repository: TreesRead, root: Path) -> None:
        self._repository = repository
        self._root = root

    async def name_at(self, place: CodePlace, *, tree: str, base: str, files: list[DiffFile]) -> NameFound:
        """The name at a place of the take, and every place it stands in the take's tree.

        `tree` is what the take was written down as, `base` what the review
        reads it against, and `files` the take's own diff. A place on the old
        side stands in the base, under the path its file had there; the name
        read there is looked for in the take all the same.

        Raises:
            FileNotInReviewError: if the side asked about has no file to read there.
            NoWordHereError: if the place holds no word.
        """
        started = time.perf_counter()
        match place.side:
            case LineSide.NEW:
                revision, path = tree, place.path
            case LineSide.OLD:
                revision, path = base, _old_path_of(place.path, files)
            case _:
                assert_never(place.side)
        asked = (await self._repository.files_of(self._root, revision, [path])).contents.get(path)
        if asked is None:
            msg = f"no file to read at {path} on the {place.side} side"
            raise FileNotInReviewError(msg)
        name = await asyncio.to_thread(word_at, path, asked, place.line, place.column)

        named = time.perf_counter()
        holding = await self._repository.paths_holding(self._root, tree, name)
        searched = time.perf_counter()
        contents = (await self._repository.files_of(self._root, tree, holding)).contents
        read = time.perf_counter()
        places = await asyncio.to_thread(_places_in, contents, name, _added_lines(files))
        log.debug(
            "name_looked_up",
            files=len(holding),
            places=len(places),
            named_ms=milliseconds_between(started, named),
            searched_ms=milliseconds_between(named, searched),
            read_ms=milliseconds_between(searched, read),
            parsed_ms=milliseconds_between(read, time.perf_counter()),
        )
        return NameFound(name=name, places=places)


def _old_path_of(path: str, files: list[DiffFile]) -> str:
    """Where a file stood before the change: where it moved from, if the take's diff says it moved."""
    return next((file.path_before for file in files if file.path == path), path)


def _added_lines(files: list[DiffFile]) -> dict[str, frozenset[int]]:
    """The lines the change wrote, file by file, by their number on the new side."""
    return {file.path: file.lines_touched().added for file in files}


def _places_in(contents: dict[str, bytes], name: str, added_lines: dict[str, frozenset[int]]) -> list[NamePlace]:
    """Every place a name stands in these files, file by file in the order of their paths."""
    return [
        place
        for path in sorted(contents)
        for place in places_of(path, contents[path], name, added_lines.get(path, frozenset()))
    ]
