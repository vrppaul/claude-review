"""Refuse an OpenAPI document whose union leaves its label out of what a branch requires.

A union the API takes or sends is told apart by a label — an anchor by its
`kind`, a block of a story by its `at`, an event by its `type` — and the
server refuses a body without one. A label given a default in its wire
schema is written into the document as optional where a request carries
it, so the document says a body with no label is well formed. Whoever is
written from it may send one; the schema fuzzing, drawing such bodies,
finds each fitting several branches at once and throws most of what it
draws away, until Hypothesis gives up on the route. So every branch a
union's mapping names requires the union's label.

Run with a document on stdin, as the hook runs it:

    uv run python -m claude_review.presentation.api_schema http | uv run python scripts/check_union_labels.py

Prints a line for each branch that leaves its label out, and exits 1;
exits 0 where every branch requires it.
"""

import sys

from pydantic import BaseModel, ConfigDict, Field, JsonValue, TypeAdapter

# What a reference to a named schema of the document begins with, before the name
SCHEMA_REFERENCE = "#/components/schemas/"
# Where a union's discriminator stands in a schema
DISCRIMINATOR = "discriminator"
# What the check exits with: a label left out, or every one required
LABEL_LEFT_OUT = 1
EVERY_LABEL_REQUIRED = 0


class Discriminator(BaseModel):
    """What tells a union's branches apart: the label's name, and the branch each of its values names."""

    model_config = ConfigDict(frozen=True)

    property_name: str = Field(alias="propertyName")
    mapping: dict[str, str]


class Branch(BaseModel):
    """A named schema, as far as this check reads it: the properties it requires."""

    model_config = ConfigDict(frozen=True)

    required: list[str] = []


class Components(BaseModel):
    """The document's named schemas."""

    model_config = ConfigDict(frozen=True)

    schemas: dict[str, Branch]


class Document(BaseModel):
    """An OpenAPI document, as far as this check reads it."""

    model_config = ConfigDict(frozen=True)

    components: Components


def _discriminators(node: JsonValue) -> list[Discriminator]:
    """Every union's discriminator in a part of the document, wherever it stands."""
    match node:
        case dict():
            own = [Discriminator.model_validate(node[DISCRIMINATOR])] if DISCRIMINATOR in node else []
            return own + [found for child in node.values() for found in _discriminators(child)]
        case list():
            return [found for child in node for found in _discriminators(child)]
        case _:
            return []


def _labels_left_out(document: JsonValue) -> list[str]:
    """Each branch of a union that does not require the union's label, said once, by the branch's name."""
    branches = Document.model_validate(document).components.schemas
    return sorted(
        {
            f"{name}: does not require `{union.property_name}`, the label of a union it is a branch of: "
            "give the label no default in its schema"
            for union in _discriminators(document)
            for name in (reference.removeprefix(SCHEMA_REFERENCE) for reference in union.mapping.values())
            if union.property_name not in branches[name].required
        }
    )


def main() -> int:
    document = TypeAdapter(JsonValue).validate_json(sys.stdin.buffer.read())
    left_out = _labels_left_out(document)
    for fault in left_out:
        print(fault)
    return LABEL_LEFT_OUT if left_out else EVERY_LABEL_REQUIRED


if __name__ == "__main__":
    sys.exit(main())
