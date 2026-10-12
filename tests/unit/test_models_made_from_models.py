"""Functional requirement tests for a model the review makes from another: it says everything the other said.

A piece of a file, a step as it is told, an anchor moved, a message taken
back: each is made from a model the review already holds, and says all of it
again but what was replaced. One that left a field out would still be a
model, and nobody would see what it no longer says — a piece of a file that
became a link, not saying so.
"""

import pytest
from pydantic import BaseModel, ConfigDict

from claude_review.domain.models import DiffFile, FileStatus, LineSide, LineSpan, SaidInPanel, TurnAuthor, Unshown
from claude_review.domain.story import Chapter, LeftOut, Step
from tests.helpers import line_anchor
from tests.stories import canvas_story, hunk


class MadeFrom(BaseModel):
    """A model made from another: which it is, and the fields its making writes anew, or adds."""

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
# An anchor on what the review holds, and the same one marked outdated: making one writes that mark anew,
# and which of the two it is made from shows it
QUOTE = ["def walk():", "    run()"]
ANCHOR = line_anchor("src/moved.py", 11, 12, side=LineSide.OLD, quote=QUOTE)
OUTDATED_ANCHOR = line_anchor("src/moved.py", 11, 12, side=LineSide.OLD, quote=QUOTE, outdated=True)
SAID = SaidInPanel(
    said_id="message-1",
    message_id="message-1",
    author=TurnAuthor.READER,
    body="Is the store closed on every path?",
    at=1_760_000_000_000,
    images=["image-1"],
    threads=["thread-1"],
    files=["src/moved.py"],
    taken_back=False,
)
STEP = Step(file="src/moved.py", lines=LineSpan(first=11, last=12), reason="The store closes before the reply is sent.")
CHAPTER = Chapter[Step](
    id="ch-1",
    title="The store closes",
    why="Both changes are about when the store closes.",
    doubt="Whether a cancelled reply still closes it.",
    steps=[STEP],
)
STORY = canvas_story()
TOLD_STEP = STEP.told(FILE)
TOLD_CHAPTER = CHAPTER.told([TOLD_STEP])
LEFT_OUT = LeftOut(piece=FILE, changed_lines=2)

MADE = [
    MadeFrom(what="a piece of a file", source=FILE, made=FILE.showing(OTHER_ROWS), replaced={"hunks"}),
    MadeFrom(
        what="a file too large to show", source=FILE, made=FILE.unshown_for(Unshown.TOO_LARGE), replaced={"unshown"}
    ),
    MadeFrom(
        what="an anchor quoting its lines",
        source=OUTDATED_ANCHOR,
        made=OUTDATED_ANCHOR.quoting(["def run():"]),
        replaced={"quote", "outdated"},
    ),
    MadeFrom(
        what="an anchor found again",
        source=OUTDATED_ANCHOR,
        made=OUTDATED_ANCHOR.current_at(14, 15),
        replaced={"start_line", "end_line", "outdated"},
    ),
    MadeFrom(what="an anchor lost", source=ANCHOR, made=ANCHOR.lost(), replaced={"outdated"}),
    MadeFrom(what="a message taken back", source=SAID, made=SAID.withdrawn(), replaced={"taken_back"}),
    MadeFrom(what="a step told", source=STEP, made=TOLD_STEP, replaced={"piece"}),
    MadeFrom(what="a chapter told", source=CHAPTER, made=TOLD_CHAPTER, replaced={"steps"}),
    MadeFrom(
        what="a story told",
        source=STORY,
        made=STORY.told([TOLD_CHAPTER], [LEFT_OUT]),
        replaced={"chapters", "left_out"},
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
