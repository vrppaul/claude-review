"""A name in the code under review: the place the reader asks about, and every place the name stands in the take.

The review, never the page, decides what a name is: a language's grammar
reads one where the review has the grammar, and a file of no grammar is read
as text, a whole word taken for a name. What the reader is after is where
a name is defined and where it is used, the uses the change did not write
set apart: those are what the agent may have forgotten.
"""

from enum import StrEnum, auto

from pydantic import BaseModel, ConfigDict

from claude_review.domain.models import LineSide

# The number of a line's first character: a column counts characters from it
FIRST_COLUMN = 0


class CodePlace(BaseModel):
    """A character of a file the reader points at: the file as the review names it, its side, the line, the column.

    The column counts the line's characters, not its bytes, from `FIRST_COLUMN`.
    """

    model_config = ConfigDict(frozen=True)

    path: str
    side: LineSide
    line: int
    column: int


class DefinitionKind(StrEnum):
    """What a definition of a name defines, as the grammars tell them apart."""

    CLASS = auto()
    INTERFACE = auto()
    TYPE = auto()
    ENUM = auto()
    FUNCTION = auto()
    METHOD = auto()
    # A name a class's body, an interface, or a method's assignment to `self` gives its instances
    FIELD = auto()
    # A name a function takes a value by
    PARAMETER = auto()
    # A name a declaration or an assignment gives a value, in any scope
    VARIABLE = auto()


# What a place can stand inside: a definition that holds code, never one that names a value or a type
HOLDS_CODE = frozenset(
    {
        DefinitionKind.CLASS,
        DefinitionKind.INTERFACE,
        DefinitionKind.ENUM,
        DefinitionKind.FUNCTION,
        DefinitionKind.METHOD,
    }
)


class FoundAs(StrEnum):
    """How a place was found.

    NAME — its language's grammar read it as the name it is.
    TEXT — it is a whole word in text no grammar reads: a file of no grammar,
    or a Svelte component's markup.
    """

    NAME = auto()
    TEXT = auto()


class NamePlace(BaseModel):
    """One place a name stands in the take on screen: where, the line it is on, and what it does there."""

    model_config = ConfigDict(frozen=True)

    path: str
    line: int
    column: int
    # The whole line the name stands on
    text: str
    # What the place defines the name as; None where it uses the name, or was found as text
    defined_as: DefinitionKind | None
    # The name of the innermost definition holding code the place stands inside (`HOLDS_CODE`); None outside
    # any, or found as text
    inside: str | None
    # Whether the change wrote the line: one the review's own diff shows added
    added: bool
    found_as: FoundAs


class NameFound(BaseModel):
    """The word at the place the reader asked about, and every place the code of the take calls something so.

    The word is looked for wherever it stands, a comment or a string too: no
    place means nothing in the code is called so.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    places: list[NamePlace]
