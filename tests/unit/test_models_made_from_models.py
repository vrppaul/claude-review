"""Functional requirement tests for a model the review makes from another: it says everything the other said.

A piece of a file, a step as it is told, an anchor moved, a message taken
back: each is made from a model the review already holds, and says all of it
again but what was replaced. One that left a field out would still be a
model, and nobody would see what it no longer says — a piece of a file that
became a link, not saying so.
"""

import pytest
from pydantic import BaseModel, ConfigDict

from claude_review.domain.models import DiffFile, FileStatus, Unshown
from tests.stories import hunk


class MadeFrom(BaseModel):
    """A model made from another: which it is, and the fields it says something else in, or gained."""

    model_config = ConfigDict(frozen=True)

    what: str
    source: BaseModel
    made: BaseModel
    replaced: set[str]


# A file with everything a file may say of itself: moved, its mode changed, and why its lines are not shown
FILE = DiffFile(
    path="src/moved.py",
    old_path="src/service.py",
    status=FileStatus.RENAMED,
    hunks=[hunk(10, 10, " -+ ")],
    unshown=Unshown.BINARY,
    old_mode="100644",
    new_mode="100755",
)
OTHER_ROWS = [hunk(3, 3, "+")]

MADE = [
    MadeFrom(what="a piece of a file", source=FILE, made=FILE.showing(OTHER_ROWS), replaced={"hunks"}),
    MadeFrom(
        what="a file too large to show", source=FILE, made=FILE.unshown_for(Unshown.TOO_LARGE), replaced={"unshown"}
    ),
]
EACH_MADE = pytest.mark.parametrize("model", MADE, ids=[model.what for model in MADE])


@EACH_MADE
def test_a_model_made_from_another_says_everything_the_other_said_but_what_was_replaced(model: MadeFrom) -> None:
    assert model.made.model_dump(exclude=model.replaced) == model.source.model_dump(exclude=model.replaced)


@EACH_MADE
def test_a_model_made_from_another_is_given_every_field_it_has(model: MadeFrom) -> None:
    """None is left to a default: a field the model gains later fails here until whoever makes one hands it on."""
    assert model.made.model_fields_set == set(type(model.made).model_fields)
