"""The names outlining the take's files that hold what the reader typed into the tree's filter, the change's own aside.

The tree lists the names the change touched; a reader filtering it for a
name the change left alone is told where the repository defines it. Each
file is outlined once for the review's life (`Outlines`), and a search reads
a large tree's every name: only those an answer lists are written out.
"""

from pydantic import BaseModel, ConfigDict

from claude_review.domain.code_names import NAMES_FOUND_LISTED, FileNamesTouched, NameDefined, NamesFound
from claude_review.services.code_names.outlines import Outlines

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
    outlines: Outlines, *, text: str, tree: str, touched: list[FileNamesTouched], within_seconds: float
) -> FoundSoFar:
    """The names outlining files of the tree that hold the text whatever its case, the change's own left out, in
    the files outlined within the time given: the first listed, and how many more there are.

    Those starting with the text come first, the way a reader types a name
    from its start; each run in the order of the files' paths and their lines.

    Raises:
        GitError: if git cannot read the tree.
    """
    holding = await outlines.names_holding_text(tree, text, within_seconds=within_seconds)
    listed_in_tree = {file.path: frozenset(name.name for name in file.names) for file in touched}
    # Lower-cased, as the page's filter matches the names the tree lists
    sought = text.lower()
    starting: list[NameDefined] = []
    holding_within: list[NameDefined] = []
    found = 0
    for lowered, path, name in zip(holding.lowered, holding.paths, holding.names, strict=True):
        if sought not in lowered or name.name in listed_in_tree.get(path, NONE_LISTED):
            continue
        found += 1
        run = starting if lowered.startswith(sought) else holding_within
        if len(run) < NAMES_FOUND_LISTED:
            run.append(name.defined_in(path))
    names = [*starting, *holding_within][:NAMES_FOUND_LISTED]
    return FoundSoFar(names=names, more=found - len(names), complete=holding.complete)
