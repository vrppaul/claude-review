"""Functional requirement tests for a story on the wire: the document the agent writes, and the story a page is told.

The agent writes a story's document by hand, as JSON. What it wrote is read
as the story it means, or refused naming the field: a field the document
does not have is never passed over, since a reason or a doubt written under
the wrong name would be a story that says less than its author thinks.
"""

import pytest
from pydantic import JsonValue, ValidationError

from claude_review.domain.exceptions import FieldPath
from claude_review.domain.story import ToldFrom
from claude_review.presentation.wire.story import StoryRequest, ToldStory
from claude_review.services.story_telling import as_told, tell
from tests.stories import as_the_agent_writes, canvas_story, changed_file, hunk, step, story_of, without_field

SERVICE = "src/service.py"
CHANGE = [changed_file(SERVICE, hunk(10, 10, "  -++ -- "))]
FIRST_STEP: FieldPath = ("chapters", 0, "steps", 0)
# A part of a document the agent writes fields into: every part reads its fields by one rule
A_CHAPTER: FieldPath = ("chapters", 0)
# What is no way to write a step's lines: words, a number, the first and the last apart
NOT_LINES: list[JsonValue] = ["all of it", 42, {"first": 42, "last": 47}, "42 - 47", ""]
# What a story must say, and nothing it may leave out
THE_LEAST_A_STORY_SAYS: dict[str, JsonValue] = {
    "title": "A change",
    "told_from": "commits",
    "overview": {"task": "Change it.", "done": "It is changed."},
    "chapters": [
        {
            "id": "ch-1",
            "title": "The change",
            "why": "It belongs together.",
            "steps": [{"file": SERVICE, "lines": "12"}],
        }
    ],
}


def written_with(document: dict[str, JsonValue], path: FieldPath, value: JsonValue) -> dict[str, JsonValue]:
    """The document with one field written anew, or one more written into it: the field its path leads to."""
    *way, field = path
    holder = document
    for part in way:
        holder = holder[part]
    holder[field] = value
    return document


def refused_at(document: dict[str, JsonValue]) -> list[FieldPath]:
    """Where a document is refused as it is read, field by field."""
    with pytest.raises(ValidationError) as refused:
        StoryRequest.model_validate(document)
    return [error["loc"] for error in refused.value.errors()]


def test_a_document_is_read_as_the_story_it_writes() -> None:
    document = as_the_agent_writes(canvas_story())

    assert StoryRequest.model_validate(document).in_the_review() == canvas_story()


def test_a_story_the_review_holds_is_written_as_the_document_that_says_it() -> None:
    """Lines the review holds as lines are taken as they are, and written as a person writes them."""
    document = StoryRequest.of(canvas_story())

    assert document.in_the_review() == canvas_story()
    assert document.model_dump(mode="json")["chapters"][0]["steps"][0]["lines"] == "30-47"


def test_what_a_story_may_leave_out_is_read_as_left_out() -> None:
    story = StoryRequest.model_validate(THE_LEAST_A_STORY_SAYS).in_the_review()

    assert story.told_from == ToldFrom.COMMITS
    assert (story.overview.doubt, story.overview.diagram, story.chapters[0].doubt) == (None, None, None)
    assert (story.overview.decisions, story.overview.turned_down, story.overview.later) == ([], [], [])
    assert (story.housekeeping, story.chapters[0].steps[0].reason) == ([], None)


@pytest.mark.parametrize("left_out", ["title", "told_from", "overview", "chapters"])
def test_what_a_story_must_say_is_asked_for_by_name(left_out: str) -> None:
    """Whether it is told from memory or read back from commits most of all: unsaid, a reconstruction would pass for memory."""
    assert refused_at(without_field(THE_LEAST_A_STORY_SAYS, left_out)) == [(left_out,)]


def test_a_field_the_document_does_not_have_is_refused_by_name() -> None:
    """A doubt written as "doubts" would be a story that says less than its author thinks."""
    document = written_with(as_the_agent_writes(canvas_story()), (*A_CHAPTER, "doubts"), "Whether it holds.")

    assert refused_at(document) == [(*A_CHAPTER, "doubts")]


@pytest.mark.parametrize("written", NOT_LINES)
def test_lines_not_written_as_lines_are_refused_at_the_step(written: JsonValue) -> None:
    document = written_with(as_the_agent_writes(canvas_story()), (*FIRST_STEP, "lines"), written)

    assert refused_at(document) == [(*FIRST_STEP, "lines")]


def test_lines_that_run_backwards_are_read_and_left_to_the_storys_checks() -> None:
    """Refused here, they would be refused alone, and everything else wrong with the story heard only afterwards."""
    document = written_with(as_the_agent_writes(canvas_story()), (*FIRST_STEP, "lines"), "47-30")

    lines = StoryRequest.model_validate(document).in_the_review().chapters[0].steps[0].lines

    assert (lines.first, lines.last) == (47, 30)


@pytest.mark.parametrize("lines", ["42", "30-47", "47-30"])
def test_a_document_written_out_again_is_the_document_that_was_read(lines: str) -> None:
    """The command reads the agent's file and sends what it read: lines go out as they came in."""
    document = written_with(as_the_agent_writes(canvas_story()), (*FIRST_STEP, "lines"), lines)
    read = StoryRequest.model_validate(document)

    assert read.model_dump(mode="json") == document
    assert StoryRequest.model_validate_json(read.model_dump_json()) == read


def test_a_told_story_reaches_a_page_with_every_piece_and_every_line_it_was_told_with() -> None:
    told = as_told(tell(story_of(step(SERVICE, 12, 13)), CHANGE))

    on_the_wire = ToldStory.of(told)

    # A step and a piece on the wire say whether a thread may name their file, and a chapter how many of its steps
    # show code changed since it was told, which the review's own answer from the path and from the steps
    whether_commentable = {"piece": {"commentable"}}
    as_the_review_holds_it = on_the_wire.model_dump(
        exclude={
            "chapters": {
                "__all__": {
                    "changed_steps": True,
                    "steps": {"__all__": {"commentable": True, "now": whether_commentable}},
                }
            },
            "left_out": {"__all__": whether_commentable},
        }
    )
    assert as_the_review_holds_it == told.model_dump()
