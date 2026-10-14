"""Functional requirement tests for a story's document: what keeps it from being told, all of it said at once.

The agent writes a story in one go and sends it whole. Told of one fault at
a time it would send the story again for each, so everything wrong with the
document is found in one reading, each fault at the field it is about, with
where the rest belongs when a text ran long.
"""

import sys
from types import FrameType

import pytest
from hypothesis import given, strategies as strategy
from pydantic import BaseModel, ConfigDict, JsonValue

from claude_review.domain.exceptions import FieldFault, FieldPath
from claude_review.domain.models import MAX_ID_LENGTH, LineSpan
from claude_review.domain.story import TEXT_LIMITS, Step, Story, StoryText
from claude_review.services.story_checks import CHAPTER_ID_RULE, document_faults
from tests.stories import (
    IMAGE_SERVICE,
    IMAGE_STORE,
    KEEPING_CHAPTER,
    PASTE_CHAPTER,
    canvas_story,
    chapter_of,
    field_at,
    planted,
    story_of_chapters,
)

# Where a text of each kind stands in the story the canvas tells
TEXT_PLACES: dict[StoryText, FieldPath] = {
    StoryText.TITLE: ("title",),
    StoryText.TASK: ("overview", "task"),
    StoryText.DONE: ("overview", "done"),
    StoryText.DOUBT: ("overview", "doubt"),
    StoryText.CAPTION: ("overview", "diagram", "caption"),
    StoryText.ITEM: ("overview", "decisions", 0, "text"),
    StoryText.CHAPTER_TITLE: ("chapters", 1, "title"),
    StoryText.CHAPTER_WHY: ("chapters", 1, "why"),
    StoryText.CHAPTER_DOUBT: ("chapters", 1, "doubt"),
    StoryText.STEP_REASON: ("chapters", 1, "steps", 2, "reason"),
}
# The kinds a story may leave out altogether
MAY_BE_LEFT_OUT = [StoryText.DOUBT, StoryText.CAPTION, StoryText.CHAPTER_DOUBT, StoryText.STEP_REASON]
# The lists of the overview, each of whose items is held to the same length
ITEM_LISTS = ["decisions", "turned_down", "later"]
# Every link the overview makes to a chapter
LINKS: list[FieldPath] = [
    ("overview", "decisions", 0, "chapter"),
    ("overview", "turned_down", 1, "chapter"),
    ("overview", "later", 0, "chapter"),
    ("overview", "diagram", "links", "store"),
]
# What the diagram is drawn from
DRAWING: FieldPath = ("overview", "diagram", "mermaid")
# Texts that say nothing: none at all, and blanks alone
BLANKS = ["", "  \n\t"]
# An id no chapter of the story has
NO_CHAPTER = "ch-9"

# The three steps of the second chapter that are told of one file, and the one told of another
FIRST_STEP_LINES: FieldPath = ("chapters", 1, "steps", 0, "lines")
SECOND_STEP_LINES: FieldPath = ("chapters", 1, "steps", 1, "lines")
THIRD_STEP_LINES: FieldPath = ("chapters", 1, "steps", 2, "lines")
OTHER_FILE_STEP_LINES: FieldPath = ("chapters", 1, "steps", 3, "lines")
# The file and the lines of the first chapter's first step
PASTE_STEP_FILE: FieldPath = ("chapters", 0, "steps", 0, "file")
PASTE_STEP_LINES: FieldPath = ("chapters", 0, "steps", 0, "lines")
# Lines well above every step the canvas tells of that file, for steps a test moves about;
# how far a generated step reaches from where it is made; and a line far below them all
ROOM_ABOVE = 60
LONGEST_REACH = 20
FAR_BELOW = 500
# How far past a limit a generated text runs
FAR_OVER = 50
# How far apart the narrow steps of a long story start; how many steps the shorter of two such stories has,
# and how many times as many the longer; and how much more than that many times the work the longer may take,
# for the logarithm: held against one another step by step, it took that many times squared
STRIDE = 4
STEPS_OF_THE_SHORTER = 500
TIMES_AS_LONG = 4
ROOM_FOR_THE_LOGARITHM = 2


def lines(first: int, last: int) -> dict[str, JsonValue]:
    """Lines of a file, as a step's document names them."""
    return {"first": first, "last": last}


def text_of(length: int) -> str:
    """A text of exactly this many characters, all of them saying something."""
    return "x" * length


def paths_of(faults: list[FieldFault]) -> list[FieldPath]:
    return [fault.path for fault in faults]


def test_the_story_the_canvas_tells_may_be_told() -> None:
    assert document_faults(canvas_story()) == []


@pytest.mark.parametrize("kind", StoryText)
def test_a_text_as_long_as_its_limit_is_taken(kind: StoryText) -> None:
    story = planted(canvas_story(), TEXT_PLACES[kind], text_of(TEXT_LIMITS[kind].characters))

    assert document_faults(story) == []


@pytest.mark.parametrize("kind", StoryText)
def test_a_text_one_character_over_its_limit_is_refused_saying_where_the_rest_belongs(kind: StoryText) -> None:
    limit = TEXT_LIMITS[kind]
    story = planted(canvas_story(), TEXT_PLACES[kind], text_of(limit.characters + 1))

    [fault] = document_faults(story)

    assert fault.path == TEXT_PLACES[kind]
    assert str(limit.characters + 1) in fault.reason
    assert str(limit.characters) in fault.reason
    assert limit.hint in fault.reason


@given(kind=strategy.sampled_from(StoryText), over=strategy.integers(min_value=1, max_value=FAR_OVER))
def test_however_far_over_its_limit_a_text_runs_it_is_refused_once_at_its_own_field(kind: StoryText, over: int) -> None:
    story = planted(canvas_story(), TEXT_PLACES[kind], text_of(TEXT_LIMITS[kind].characters + over))

    assert paths_of(document_faults(story)) == [TEXT_PLACES[kind]]


@given(kind=strategy.sampled_from(StoryText), data=strategy.data())
def test_a_text_within_its_limit_is_never_refused(kind: StoryText, data: strategy.DataObject) -> None:
    length = data.draw(strategy.integers(min_value=1, max_value=TEXT_LIMITS[kind].characters))

    assert document_faults(planted(canvas_story(), TEXT_PLACES[kind], text_of(length))) == []


@pytest.mark.parametrize("kind", StoryText)
@pytest.mark.parametrize("blank", BLANKS)
def test_a_text_that_says_nothing_is_refused(kind: StoryText, blank: str) -> None:
    story = planted(canvas_story(), TEXT_PLACES[kind], blank)

    assert paths_of(document_faults(story)) == [TEXT_PLACES[kind]]


@pytest.mark.parametrize("kind", MAY_BE_LEFT_OUT)
def test_a_text_the_story_may_leave_out_is_no_fault_when_it_does(kind: StoryText) -> None:
    story = planted(canvas_story(), TEXT_PLACES[kind], None)

    assert document_faults(story) == []


@pytest.mark.parametrize("blank", BLANKS)
def test_a_diagram_with_nothing_drawn_is_refused(blank: str) -> None:
    """Whether a drawing draws only a browser can say; that an empty one does not, anybody can."""
    story = planted(canvas_story(), DRAWING, blank)

    assert paths_of(document_faults(story)) == [DRAWING]


@pytest.mark.parametrize("item_list", ITEM_LISTS)
def test_every_list_of_the_overview_holds_its_items_to_the_same_length(item_list: str) -> None:
    place: FieldPath = ("overview", item_list, 1, "text")
    story = planted(canvas_story(), place, text_of(TEXT_LIMITS[StoryText.ITEM].characters + 1))

    assert paths_of(document_faults(story)) == [place]


@pytest.mark.parametrize("blank", BLANKS)
def test_a_chapter_whose_id_says_nothing_is_refused_though_a_link_leads_to_it(blank: str) -> None:
    """What the overview and the diagram lead to a chapter by has to be something to lead by."""
    unnamed = planted(canvas_story(), ("chapters", 0, "id"), blank)
    story = planted(unnamed, ("overview", "diagram", "links", "paste"), blank)

    assert paths_of(document_faults(story)) == [("chapters", 0, "id")]


@pytest.mark.parametrize("not_an_id", ["images kept", "images/kept", "x" * (MAX_ID_LENGTH + 1)])
def test_a_chapter_whose_id_no_thread_could_name_is_refused_saying_what_an_id_may_hold(not_an_id: str) -> None:
    """A thread on what the chapter says names it by its id: told, it would offer to be asked about, and fail."""
    renamed = planted(canvas_story(), ("chapters", 0, "id"), not_an_id)
    story = planted(renamed, ("overview", "diagram", "links", "paste"), not_an_id)

    [fault] = document_faults(story)

    assert fault.path == ("chapters", 0, "id")
    assert CHAPTER_ID_RULE in fault.reason


def test_a_story_tells_at_least_one_chapter() -> None:
    told_nothing = planted(planted(canvas_story(), ("chapters",), []), ("overview", "diagram"), None)
    unlinked = planted(told_nothing, ("overview", "decisions"), [])

    assert paths_of(document_faults(unlinked)) == [("chapters",)]


def test_a_chapter_shows_at_least_one_step() -> None:
    story = planted(canvas_story(), ("chapters", 0, "steps"), [])

    assert paths_of(document_faults(story)) == [("chapters", 0, "steps")]


def test_two_chapters_under_one_id_are_refused_at_the_second() -> None:
    """A link to that id could mean either chapter."""
    renamed = planted(canvas_story(), ("chapters", 0, "id"), KEEPING_CHAPTER)
    story = planted(renamed, ("overview", "diagram", "links", "paste"), KEEPING_CHAPTER)

    [fault] = document_faults(story)

    assert fault.path == ("chapters", 1, "id")
    assert KEEPING_CHAPTER in fault.reason


@pytest.mark.parametrize("link", LINKS)
def test_a_link_to_a_chapter_the_story_does_not_have_is_refused(link: FieldPath) -> None:
    story = planted(canvas_story(), link, NO_CHAPTER)

    [fault] = document_faults(story)

    assert fault.path == link
    assert NO_CHAPTER in fault.reason


@pytest.mark.parametrize(("first", "last"), [(0, 5), (-3, -1)])
def test_lines_numbered_from_before_a_files_first_line_are_refused(first: int, last: int) -> None:
    story = planted(canvas_story(), FIRST_STEP_LINES, lines(first, last))

    assert paths_of(document_faults(story)) == [FIRST_STEP_LINES]


def test_lines_that_run_backwards_are_refused() -> None:
    story = planted(canvas_story(), FIRST_STEP_LINES, lines(92, 68))

    [fault] = document_faults(story)

    assert fault.path == FIRST_STEP_LINES
    assert "92" in fault.reason
    assert "68" in fault.reason


def test_a_step_may_be_told_of_one_line() -> None:
    assert document_faults(planted(canvas_story(), FIRST_STEP_LINES, lines(68, 68))) == []


def test_a_step_may_start_at_a_files_first_line() -> None:
    assert document_faults(planted(canvas_story(), FIRST_STEP_LINES, lines(1, 12))) == []


@pytest.mark.parametrize(("first", "last"), [(130, 141), (95, 102)])
def test_a_line_two_steps_both_tell_is_refused_at_each_naming_the_other(first: int, last: int) -> None:
    """Told twice, a thread on the line would be drawn twice, and nobody could say which step it belongs to.

    One line is enough: the last of the other step's, or its first.
    """
    story = planted(canvas_story(), THIRD_STEP_LINES, lines(first, last))

    [second, third] = document_faults(story)

    assert (second.path, third.path) == (SECOND_STEP_LINES, THIRD_STEP_LINES)
    # The lines each meets, and the chapter that tells them, so the agent finds the other step
    assert (f"{first}-{last}" in second.reason, KEEPING_CHAPTER in second.reason) == (True, True)
    assert ("102-130" in third.reason, KEEPING_CHAPTER in third.reason) == (True, True)


def test_steps_that_follow_one_another_line_after_line_share_none() -> None:
    story = planted(canvas_story(), THIRD_STEP_LINES, lines(131, 131))

    assert document_faults(story) == []


def test_the_same_lines_of_two_files_are_two_different_things() -> None:
    story = planted(canvas_story(), OTHER_FILE_STEP_LINES, lines(102, 130))

    assert document_faults(story) == []


def test_a_file_may_stand_in_two_chapters_with_different_lines() -> None:
    story = planted(canvas_story(), PASTE_STEP_FILE, IMAGE_SERVICE)

    assert document_faults(story) == []


def test_a_line_told_in_two_chapters_is_refused_at_each_naming_the_chapter_that_tells_the_other() -> None:
    moved = planted(canvas_story(), PASTE_STEP_FILE, IMAGE_STORE)
    story = planted(moved, PASTE_STEP_LINES, lines(20, 40))

    [in_paste, in_keeping] = document_faults(story)

    assert (in_paste.path, in_keeping.path) == (PASTE_STEP_LINES, OTHER_FILE_STEP_LINES)
    assert ("7-23" in in_paste.reason, KEEPING_CHAPTER in in_paste.reason) == (True, True)
    assert ("20-40" in in_keeping.reason, PASTE_CHAPTER in in_keeping.reason) == (True, True)


def test_a_step_is_held_against_every_other_step_of_its_file_not_only_the_one_beside_it() -> None:
    """A long step with a short one inside it: a third further down still meets the long one, past the short."""
    story = planted(two_steps_of_one_file(lines(1, 100), lines(2, 3)), THIRD_STEP_LINES, lines(50, 60))

    [first, second, third] = document_faults(story)

    assert (first.path, second.path, third.path) == (FIRST_STEP_LINES, SECOND_STEP_LINES, THIRD_STEP_LINES)
    assert "1-100" in second.reason
    assert "1-100" in third.reason


def test_every_step_of_a_chain_of_steps_that_meet_is_refused_in_one_answer() -> None:
    """The second meets the first, and the third only the second: all that is wrong is said at once."""
    story = planted(two_steps_of_one_file(lines(1, 10), lines(5, 20)), THIRD_STEP_LINES, lines(15, 18))

    [first, second, third] = document_faults(story)

    assert (first.path, second.path, third.path) == (FIRST_STEP_LINES, SECOND_STEP_LINES, THIRD_STEP_LINES)
    assert "5-20" in first.reason
    assert "5-20" in third.reason


def test_in_a_knot_of_three_steps_every_one_is_refused_in_one_answer_naming_one_it_meets() -> None:
    """The second shares lines with the first, and the third lies across both: refused for one step at a
    time, the agent would send the story once more for each."""
    story = planted(two_steps_of_one_file(lines(10, 20), lines(15, 30)), THIRD_STEP_LINES, lines(1, 100))

    [first, second, third] = document_faults(story)

    assert (first.path, second.path, third.path) == (FIRST_STEP_LINES, SECOND_STEP_LINES, THIRD_STEP_LINES)
    assert any(met in first.reason for met in ["15-30", "1-100"])
    assert any(met in second.reason for met in ["10-20", "1-100"])
    assert any(met in third.reason for met in ["10-20", "15-30"])


class CallsCounted:
    """How many calls Python made while this stood as its profiler: the work done, whatever the machine."""

    def __init__(self) -> None:
        self.made = 0

    def __call__(self, frame: FrameType, event: str, argument: object) -> None:
        self.made += 1


def work_of_checking(story: Story[Step]) -> int:
    """How many calls checking a story's document takes."""
    counted = CallsCounted()
    sys.setprofile(counted)
    try:
        document_faults(story)
    finally:
        sys.setprofile(None)
    return counted.made


def story_with_one_step_across_the_rest(steps: int) -> Story[Step]:
    """A story of this many steps of one file: narrow ones that stand apart, and a last one told across them all."""
    narrow = [
        Step(file=IMAGE_SERVICE, lines=LineSpan(first=place * STRIDE + 1, last=place * STRIDE + 2))
        for place in range(steps - 1)
    ]
    across_them_all = Step(file=IMAGE_SERVICE, lines=LineSpan(first=1, last=steps * STRIDE))
    return story_of_chapters(chapter_of(KEEPING_CHAPTER, *narrow, across_them_all))


def test_a_story_four_times_as_long_takes_little_more_than_four_times_the_work_to_check() -> None:
    """Each step held against every other, it took sixteen times: a story as long as a request may carry, a minute."""
    work_of_the_shorter = work_of_checking(story_with_one_step_across_the_rest(STEPS_OF_THE_SHORTER))
    work_of_the_longer = work_of_checking(story_with_one_step_across_the_rest(STEPS_OF_THE_SHORTER * TIMES_AS_LONG))

    assert work_of_the_longer < work_of_the_shorter * TIMES_AS_LONG * ROOM_FOR_THE_LOGARITHM


def test_steps_that_meet_in_two_files_are_each_refused_in_the_order_the_story_tells_them() -> None:
    """The store is told of first, and its steps meet at the story's last step: the service's are said between."""
    other_file = planted(canvas_story(), ("chapters", 0, "steps", 1, "file"), IMAGE_STORE)
    met_there = planted(other_file, ("chapters", 0, "steps", 1, "lines"), lines(20, 40))
    story = planted(met_there, THIRD_STEP_LINES, lines(120, 141))

    assert paths_of(document_faults(story)) == [
        ("chapters", 0, "steps", 1, "lines"),
        SECOND_STEP_LINES,
        THIRD_STEP_LINES,
        OTHER_FILE_STEP_LINES,
    ]


def test_lines_already_refused_for_their_numbers_are_not_held_to_meet_others_too() -> None:
    story = planted(canvas_story(), SECOND_STEP_LINES, lines(92, 68))

    assert paths_of(document_faults(story)) == [SECOND_STEP_LINES]


def two_steps_of_one_file(earlier: dict[str, JsonValue], later: dict[str, JsonValue]) -> Story[Step]:
    """The canvas's story with two steps of one file told of these lines, and its third moved out of their way."""
    out_of_the_way = planted(canvas_story(), THIRD_STEP_LINES, lines(FAR_BELOW, FAR_BELOW))
    return planted(planted(out_of_the_way, FIRST_STEP_LINES, earlier), SECOND_STEP_LINES, later)


@strategy.composite
def stories_whose_steps_share_a_line(draw: strategy.DrawFn) -> Story[Step]:
    """Two steps of one file made around a line both tell: each starts no later than it and ends no sooner."""
    shared = draw(strategy.integers(min_value=LONGEST_REACH + 1, max_value=ROOM_ABOVE))
    reaches = strategy.integers(min_value=0, max_value=LONGEST_REACH)
    earlier = lines(shared - draw(reaches), shared + draw(reaches))
    later = lines(shared - draw(reaches), shared + draw(reaches))
    return two_steps_of_one_file(earlier, later)


@strategy.composite
def stories_whose_steps_stand_apart(draw: strategy.DrawFn) -> Story[Step]:
    """Two steps of one file, one ending before the other starts, told in either order."""
    reaches = strategy.integers(min_value=0, max_value=LONGEST_REACH)
    upper_first = draw(strategy.integers(min_value=1, max_value=ROOM_ABOVE))
    upper_last = upper_first + draw(reaches)
    lower_first = upper_last + 1 + draw(reaches)
    lower_last = lower_first + draw(reaches)
    earlier, later = draw(strategy.permutations([lines(upper_first, upper_last), lines(lower_first, lower_last)]))
    return two_steps_of_one_file(earlier, later)


@given(story=stories_whose_steps_share_a_line())
def test_two_steps_of_a_file_that_share_a_line_are_always_refused_at_both(story: Story[Step]) -> None:
    assert paths_of(document_faults(story)) == [FIRST_STEP_LINES, SECOND_STEP_LINES]


@given(story=stories_whose_steps_stand_apart())
def test_two_steps_of_a_file_that_share_no_line_are_never_refused(story: Story[Step]) -> None:
    assert document_faults(story) == []


def test_a_file_named_twice_as_housekeeping_is_refused_the_second_time() -> None:
    story = planted(canvas_story(), ("housekeeping",), ["CHANGELOG.md", "uv.lock", "CHANGELOG.md"])

    [fault] = document_faults(story)

    assert fault.path == ("housekeeping", 2)
    assert "CHANGELOG.md" in fault.reason


class Planting(BaseModel):
    """Something written into a story's document that keeps it from being told, and the fields its faults are said at."""

    model_config = ConfigDict(frozen=True)

    at: FieldPath
    written: JsonValue
    faulted_at: list[FieldPath]


# Faults of many kinds in one document. None of them makes another: the
# chapter that loses its id is the one nothing but the diagram led to
EVERYTHING_WRONG = [
    Planting(at=("title",), written="", faulted_at=[("title",)]),
    Planting(
        at=("overview", "task"),
        written=text_of(TEXT_LIMITS[StoryText.TASK].characters + 1),
        faulted_at=[("overview", "task")],
    ),
    Planting(
        at=("overview", "later", 1, "chapter"), written=NO_CHAPTER, faulted_at=[("overview", "later", 1, "chapter")]
    ),
    Planting(
        at=("overview", "diagram", "links", "paste"),
        written=NO_CHAPTER,
        faulted_at=[("overview", "diagram", "links", "paste")],
    ),
    Planting(at=DRAWING, written="", faulted_at=[DRAWING]),
    Planting(at=("chapters", 0, "id"), written=KEEPING_CHAPTER, faulted_at=[("chapters", 1, "id")]),
    Planting(at=("chapters", 0, "steps"), written=[], faulted_at=[("chapters", 0, "steps")]),
    Planting(at=FIRST_STEP_LINES, written=lines(0, 3), faulted_at=[FIRST_STEP_LINES]),
    # Lines the second step tells too: said at both
    Planting(at=THIRD_STEP_LINES, written=lines(120, 141), faulted_at=[SECOND_STEP_LINES, THIRD_STEP_LINES]),
    Planting(
        at=("chapters", 1, "steps", 3, "reason"),
        written=text_of(TEXT_LIMITS[StoryText.STEP_REASON].characters + 1),
        faulted_at=[("chapters", 1, "steps", 3, "reason")],
    ),
    Planting(
        at=("housekeeping",), written=["CHANGELOG.md", "uv.lock", "CHANGELOG.md"], faulted_at=[("housekeeping", 2)]
    ),
]
# Every field a fault of those is said at
FAULTED_AT = [path for planting in EVERYTHING_WRONG for path in planting.faulted_at]


def story_with_everything_wrong() -> Story[Step]:
    story = canvas_story()
    for planting in EVERYTHING_WRONG:
        story = planted(story, planting.at, planting.written)
    return story


def test_everything_wrong_with_a_story_is_said_at_once_each_fault_at_its_own_field() -> None:
    said_at = paths_of(document_faults(story_with_everything_wrong()))

    assert len(said_at) == len(FAULTED_AT)
    assert set(said_at) == set(FAULTED_AT)


def test_every_fault_is_at_a_field_the_document_has() -> None:
    """A fault names its field as the agent's JSON nests it, or the agent could not find what to put right."""
    story = story_with_everything_wrong()

    found = [field_at(story, fault.path) for fault in document_faults(story)]

    assert len(found) == len(FAULTED_AT)
