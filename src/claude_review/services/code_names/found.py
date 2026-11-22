"""The names outlining the take's files that hold what the reader typed into the tree's filter, the change's own aside.

The tree lists the names the change touched; a reader filtering it for a
name the change left alone is told where the repository defines it. Each
file is outlined once for the review's life (`Outlines`), and a search reads
a large tree's every name: only those an answer lists are written out.
"""

import asyncio

from pydantic import BaseModel, ConfigDict

from claude_review.domain.code_names import NAMES_FOUND_LISTED, FileNamesTouched, NameDefined, NamesFound
from claude_review.services.code_names.outlines import FilesOutlined, Outlines, SearchWaits
from claude_review.services.code_names.reading import OutlinedName

# The names the tree lists of a file the change did not touch
NONE_LISTED: frozenset[str] = frozenset()


class FoundSoFar(BaseModel):
    """The names found in the files outlined by now, as many listed as one answer lists, how many more there are,
    and whether those files are every one that holds the text."""

    model_config = ConfigDict(frozen=True)

    names: list[NameDefined]
    more: int
    complete: bool

    def in_take(self, take: int) -> NamesFound:
        """The names found, as found in the files of this take."""
        return NamesFound(take=take, names=self.names, more=self.more, complete=self.complete)


async def read_names_found(
    outlines: Outlines, *, text: str, tree: str, touched: list[FileNamesTouched], waits: SearchWaits
) -> FoundSoFar:
    """The names outlining files of the tree that hold the text whatever its case, the change's own left out, in
    the files outlined by the time the search waits: the first listed, and how many more there are.

    Those starting with the text come first, the way a reader types a name
    from its start; each run in the order of the files' paths and their lines.

    Raises:
        GitError: if git cannot read the tree.
    """
    holding = await outlines.holding_text(tree, text, waits=waits)
    listed_in_tree = {file.path: frozenset(name.name for name in file.names) for file in touched}
    # Off the loop: a large tree's every name is read
    return await asyncio.to_thread(_found_in, holding, text, listed_in_tree)


def _found_in(holding: FilesOutlined, text: str, listed_in_tree: dict[str, frozenset[str]]) -> FoundSoFar:
    """The names outlining these files that hold the text, those the tree lists left out."""
    # Lower-cased, as the page's filter matches the names the tree lists
    sought = text.lower()
    starting: list[NameDefined] = []
    holding_within: list[NameDefined] = []
    found_count = 0
    # A file whose parse was given up outlines nothing that can be said
    for path, held in holding.outlined.items():
        if held is None or sought not in held.lowered_together:
            continue
        left_to_tree = listed_in_tree.get(path, NONE_LISTED)
        # Made only where one of its names is listed, and once for all of them
        outlining: list[OutlinedName] | None = None
        # By position, as the names stand beside their models
        for position, lowered in enumerate(held.lowered):
            if sought not in lowered or held.names[position] in left_to_tree:
                continue
            found_count += 1
            run = starting if lowered.startswith(sought) else holding_within
            if len(run) < NAMES_FOUND_LISTED:
                if outlining is None:
                    outlining = held.outlining()
                run.append(outlining[position].defined_in(path))
    names = [*starting, *holding_within][:NAMES_FOUND_LISTED]
    return FoundSoFar(names=names, more=found_count - len(names), complete=holding.complete)
