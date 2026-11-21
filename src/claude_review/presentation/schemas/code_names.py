"""What the page is told of names in the code: the one pointed at and where it stands, and those a change touched."""

from typing import Self

from pydantic import StrictBool

from claude_review.domain import code_names
from claude_review.domain.code_names import DefinitionKind, FoundAs, NameChange
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


class TouchedName(Schema):
    """A name outlining a file that the change touched: what it is, where it stands, and what became of it."""

    name: str
    defined_as: DefinitionKind
    # Where the name stands on the new side, as `GET /api/name` is asked a place: lines from 1, columns in
    # characters from 0
    line: int
    column: int
    change: NameChange

    @classmethod
    def from_domain(cls, touched: code_names.TouchedName) -> Self:
        return cls(
            name=touched.name,
            defined_as=touched.defined_as,
            line=touched.line,
            column=touched.column,
            change=touched.change,
        )


class FileNamesTouched(Schema):
    """The names a file of the change outlines that the change touched, in the order of the file."""

    path: str
    names: list[TouchedName]

    @classmethod
    def from_domain(cls, file: code_names.FileNamesTouched) -> Self:
        return cls(path=file.path, names=[TouchedName.from_domain(touched) for touched in file.names])


class NamesTouchedResponse(Schema):
    """Response for GET /api/names-touched — the names the change touched, file by file in the order of its diff.

    A file with none is left out: one of no grammar here, not text, too
    large, deleted, or whose change touched no name standing at its top.
    """

    # The take the names were read in: a page holds them only while its diff is of the same take
    take: int
    files: list[FileNamesTouched]

    @classmethod
    def from_domain(cls, touched: code_names.NamesTouched) -> Self:
        return cls(take=touched.take, files=[FileNamesTouched.from_domain(file) for file in touched.files])
