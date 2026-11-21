"""The names outlining the take's files that hold what the reader typed into the tree's filter, the change's own aside.

The tree lists the names the change touched; a reader filtering it for a
name the change left alone is told where the repository defines it. Git
narrows the files to those holding the text, and each is outlined once for
the review's life (`Outlines`).
"""

from pydantic import BaseModel, ConfigDict

from claude_review.domain.code_names import FileNamesTouched, NameDefined
from claude_review.services.code_names.outlines import Outlines


class NameInFile(BaseModel):
    """A name by the file it outlines and itself: how a name the tree lists is known, never found again outside it."""

    model_config = ConfigDict(frozen=True)

    path: str
    name: str


async def read_names_found(
    outlines: Outlines, *, text: str, tree: str, touched: list[FileNamesTouched]
) -> list[NameDefined]:
    """The names outlining files of the tree that hold the text whatever its case, the change's own left out.

    Those starting with the text come first, the way a reader types a name
    from its start; each run in the order of the files' paths and their lines.

    Raises:
        GitError: if git cannot read the tree.
    """
    holding = await outlines.holding_text(tree, text)
    listed = {NameInFile(path=file.path, name=name.name) for file in touched for name in file.names}
    # Lower-cased, as the page's filter matches the names the tree lists
    sought = text.lower()
    found = [
        name.defined_in(path)
        for path in sorted(holding.outlined)
        # A file whose parse was given up outlines nothing that can be said
        for name in holding.outline_of(path) or []
        if sought in name.name.lower() and NameInFile(path=path, name=name.name) not in listed
    ]
    return sorted(found, key=lambda name: not name.name.lower().startswith(sought))
