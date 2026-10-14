"""Functional requirement tests for a story on the wire: the document the agent writes, and the story a page is told.

The agent writes a story's document by hand, as JSON. What it wrote is read
as the story it means, or refused naming the field: a field the document
does not have is never passed over, since a reason or a doubt written under
the wrong name would be a story that says less than its author thinks.
"""

import pytest
from pydantic import JsonValue, ValidationError

from claude_review.domain.exceptions import FieldPath
from claude_review.domain.models import MAX_ID_LENGTH, MAX_PATH_LENGTH
from claude_review.domain.story import ToldFrom
from claude_review.presentation.wire.base import MAX_TEXT_LENGTH
from claude_review.presentation.wire.story import (
    MAX_CHAPTERS,
    MAX_DIAGRAM_LINKS,
    MAX_HOUSEKEEPING_FILES,
    MAX_OVERVIEW_ITEMS,
    MAX_STEPS_IN_CHAPTER,
    StoryRequest,
    ToldStory,
)
from claude_review.services.story_telling import as_told, tell
from tests.stories import as_the_agent_writes, canvas_story, changed_file, hunk, step, story_of, without_field

SERVICE = "src/service.py"
CHANGE = [changed_file(SERVICE, hunk(10, 10, "  -++ -- "))]
FIRST_STEP: FieldPath = ("chapters", 0, "steps", 0)
# Every part of a document the agent may write a field into
PARTS: list[FieldPath] = [
    (),
    ("overview",),
    ("overview", "diagram"),
    ("overview", "decisions", 0),
    ("chapters", 0),
    FIRST_STEP,
]
# What is no way to write a step's lines: words, a number, the first and the last apart
NOT_LINES: list[JsonValue] = ["all of it", 42, {"first": 42, "last": 47}, "42 - 47", ""]
# What an agent might write where lines are wanted, and no lines are named by
NOT_LINES_AT_ALL = "the whole function"
# Each list of the document, and the most it may hold
CAPPED_LISTS: list[tuple[FieldPath, int]] = [
    (("chapters",), MAX_CHAPTERS),
    (("chapters", 0, "steps"), MAX_STEPS_IN_CHAPTER),
    (("overview", "decisions"), MAX_OVERVIEW_ITEMS),
    (("overview", "turned_down"), MAX_OVERVIEW_ITEMS),
    (("overview", "later"), MAX_OVERVIEW_ITEMS),
    (("housekeeping",), MAX_HOUSEKEEPING_FILES),
]
# Each text of the document, and the most characters a request may hold in it: a text of the story,
# a name a chapter or a part of the diagram goes by, a file's path
CAPPED_TEXTS: list[tuple[FieldPath, int]] = [
    (("title",), MAX_TEXT_LENGTH),
    (("overview", "task"), MAX_TEXT_LENGTH),
    (("overview", "done"), MAX_TEXT_LENGTH),
    (("overview", "doubt"), MAX_TEXT_LENGTH),
    (("overview", "diagram", "mermaid"), MAX_TEXT_LENGTH),
    (("overview", "diagram", "caption"), MAX_TEXT_LENGTH),
    (("overview", "diagram", "links", "paste"), MAX_ID_LENGTH),
    (("overview", "decisions", 0, "text"), MAX_TEXT_LENGTH),
    (("overview", "decisions", 0, "chapter"), MAX_ID_LENGTH),
    (("chapters", 1, "id"), MAX_ID_LENGTH),
    (("chapters", 1, "title"), MAX_TEXT_LENGTH),
    (("chapters", 1, "why"), MAX_TEXT_LENGTH),
    (("chapters", 1, "doubt"), MAX_TEXT_LENGTH),
    ((*FIRST_STEP, "file"), MAX_PATH_LENGTH),
    ((*FIRST_STEP, "reason"), MAX_TEXT_LENGTH),
    (("housekeeping", 0), MAX_PATH_LENGTH),
]
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


def read_at(document: dict[str, JsonValue], path: FieldPath) -> JsonValue:
    found = document
    for part in path:
        found = found[part]
    return found


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


@pytest.mark.parametrize("part", PARTS)
def test_a_field_the_document_does_not_have_is_refused_by_name(part: FieldPath) -> None:
    """A doubt written as "doubts" would be a story that says less than its author thinks."""
    document = written_with(as_the_agent_writes(canvas_story()), (*part, "doubts"), "Whether it holds.")

    assert refused_at(document) == [(*part, "doubts")]


@pytest.mark.parametrize("written", NOT_LINES)
def test_lines_not_written_as_lines_are_refused_at_the_step(written: JsonValue) -> None:
    document = written_with(as_the_agent_writes(canvas_story()), (*FIRST_STEP, "lines"), written)

    assert refused_at(document) == [(*FIRST_STEP, "lines")]


def test_lines_refused_are_not_said_back_to_whoever_sent_them() -> None:
    """A refusal says where and why, never what was sent: lines of any length would come back whole in it."""
    document = written_with(as_the_agent_writes(canvas_story()), (*FIRST_STEP, "lines"), NOT_LINES_AT_ALL)

    with pytest.raises(ValidationError) as refused:
        StoryRequest.model_validate(document)

    assert [NOT_LINES_AT_ALL in error["msg"] for error in refused.value.errors()] == [False]


def test_lines_that_run_backwards_are_read_and_left_to_the_storys_checks() -> None:
    """Refused here, they would be refused alone, and everything else wrong with the story heard only afterwards."""
    document = written_with(as_the_agent_writes(canvas_story()), (*FIRST_STEP, "lines"), "47-30")

    lines = StoryRequest.model_validate(document).in_the_review().chapters[0].steps[0].lines

    assert (lines.first, lines.last) == (47, 30)


@pytest.mark.parametrize(("capped", "most"), CAPPED_LISTS)
def test_a_list_holds_no_more_than_a_request_may(capped: FieldPath, most: int) -> None:
    document = as_the_agent_writes(canvas_story())
    one = read_at(document, (*capped, 0))

    assert refused_at(written_with(document, capped, [one] * (most + 1))) == [capped]


def test_a_diagram_links_no_more_parts_than_a_request_may() -> None:
    document = as_the_agent_writes(canvas_story())
    links = {f"part-{number}": "ch-1" for number in range(MAX_DIAGRAM_LINKS + 1)}

    assert refused_at(written_with(document, ("overview", "diagram", "links"), links)) == [
        ("overview", "diagram", "links")
    ]


@pytest.mark.parametrize(("capped", "most"), CAPPED_TEXTS)
def test_a_text_is_as_long_as_a_request_may_hold_and_no_longer(capped: FieldPath, most: int) -> None:
    """Far past the length a story holds a text to, which its checks say with a hint: this is only a request's bound."""
    longest = written_with(as_the_agent_writes(canvas_story()), capped, "x" * most)
    longer = written_with(as_the_agent_writes(canvas_story()), capped, "x" * (most + 1))

    assert read_at(StoryRequest.model_validate(longest).model_dump(mode="json"), capped) == "x" * most
    assert refused_at(longer) == [capped]


def test_a_part_of_the_diagram_has_a_name_no_longer_than_a_request_may_hold() -> None:
    named_at_length = {"x" * (MAX_ID_LENGTH + 1): "ch-1"}
    document = written_with(as_the_agent_writes(canvas_story()), ("overview", "diagram", "links"), named_at_length)

    assert len(refused_at(document)) == 1


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

    # A step and a piece on the wire say whether a thread may name their file, which the review's own answer from
    # the path
    whether_commentable = {"piece": {"commentable"}}
    as_the_review_holds_it = on_the_wire.model_dump(
        exclude={
            "chapters": {"__all__": {"steps": {"__all__": {"commentable": True, **whether_commentable}}}},
            "left_out": {"__all__": whether_commentable},
        }
    )
    assert as_the_review_holds_it == told.model_dump()
