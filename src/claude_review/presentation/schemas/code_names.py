"""What the page is told of a name in the code: the name at the place the reader points at, and where it stands."""

from typing import Self

from pydantic import StrictBool

from claude_review.domain import code_names
from claude_review.domain.code_names import DefinitionKind, FoundAs
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
    # The name of the definition the place stands inside; null at a file's top level, or found as text
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
