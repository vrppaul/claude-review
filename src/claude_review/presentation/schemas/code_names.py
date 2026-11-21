"""What the page is told of names in the code: the one pointed at and where it stands, and those a change touched."""

from typing import Self

from pydantic import StrictBool

from claude_review.domain import code_names
from claude_review.domain.code_names import DefinitionKind, FoundAs, NameChange
from claude_review.domain.models import LineSide
from claude_review.presentation.schemas.base import Schema


class NamePlace(Schema):
    """One place a name stands in the take on screen: where, the line it is on, and what it does there."""

    path: str
    line: int
    # Counted in characters, the line's first being 0
    column: int
    # The whole line the name stands on
    text: str
    # What the place defines the name as; null where it uses the name, or was found as text
    defined_as: DefinitionKind | None
    # The name of the innermost class, interface, enum, function or method the place stands inside; null
    # outside any, or found as text
    inside: str | None
    # Whether the change wrote the line: one the review's own diff shows added
    added: StrictBool
    found_as: FoundAs

    @classmethod
    def from_domain(cls, place: code_names.NamePlace) -> Self:
        return cls(
            path=place.path,
            line=place.line,
            column=place.column,
            text=place.text,
            defined_as=place.defined_as,
            inside=place.inside,
            added=place.added,
            found_as=place.found_as,
        )


class NameResponse(Schema):
    """Response for GET /api/name — the word at a place, and every place it stands as a name in the take on screen.

    No place means nothing in the code is called so.
    """

    name: str
    places: list[NamePlace]

    @classmethod
    def from_domain(cls, found: code_names.NameFound) -> Self:
        return cls(name=found.name, places=[NamePlace.from_domain(place) for place in found.places])


class LinesOnSide(Schema):
    """Lines of a file on one side of the diff, the first and the last both among them."""

    side: LineSide
    first: int
    last: int

    @classmethod
    def from_domain(cls, lines: code_names.LinesOnSide) -> Self:
        return cls(side=lines.side, first=lines.first, last=lines.last)


class TouchedName(Schema):
    """A name outlining a file on either side that the change touched: what it is and became, and where it stands."""

    name: str
    defined_as: DefinitionKind
    change: NameChange
    # The side its place is numbered on: the old for a name the change removed, the new for any other
    side: LineSide
    # Where the name is written, as `GET /api/name` is asked a place: lines from 1, columns in characters from 0
    line: int
    column: int
    # The lines it is defined on, first to last, on each side it stands on: the new, the old, or both for a name
    # the change modified
    stands_on: list[LinesOnSide]

    @classmethod
    def from_domain(cls, touched: code_names.TouchedName) -> Self:
        return cls(
            name=touched.name,
            defined_as=touched.defined_as,
            change=touched.change,
            side=touched.side,
            line=touched.line,
            column=touched.column,
            stands_on=[LinesOnSide.from_domain(lines) for lines in touched.stands_on],
        )


class FileNamesTouched(Schema):
    """The names outlining a file of the change that the change touched, in the order a reader meets them down
    its diff: a removed name where its lines were removed."""

    path: str
    names: list[TouchedName]

    @classmethod
    def from_domain(cls, file: code_names.FileNamesTouched) -> Self:
        return cls(path=file.path, names=[TouchedName.from_domain(touched) for touched in file.names])


class NamesTouchedResponse(Schema):
    """Response for GET /api/names-touched — the names the change touched, file by file in the order of its diff.

    A file with none is left out: one of no grammar here, not text, too
    large, or whose change touched no name standing at its top.
    """

    # The take the names were read in: a page holds them only while its diff is of the same take, read the same way
    take: int
    files: list[FileNamesTouched]

    @classmethod
    def from_domain(cls, touched: code_names.NamesTouched) -> Self:
        return cls(take=touched.take, files=[FileNamesTouched.from_domain(file) for file in touched.files])
