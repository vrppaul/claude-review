"""Functional requirement tests for telling a story of a change: placed on it, or refused with everything wrong.

A story that may be told carries, step by step, the piece of the change each
step shows. Whatever the change did that no step tells is set beside it, so
a story cannot hide a line; and one told of something the change does not
hold is refused, with all of it said at once.
"""

import pytest

from claude_review.domain.models import DiffFile, FileStatus, Unshown
from claude_review.domain.story import FieldPath, Step, Story, StoryFault, StoryRefusedError
from claude_review.services.story_telling import tell
from tests.stories import ONLY_CHAPTER, changed_file, changed_in, hunk, lines_of, planted, rows_of, step, story_of

SERVICE = "src/service.py"
STORE = "src/store.py"
LOCK = "uv.lock"
LOGO = "docs/logo.png"

# The change every test here tells: one line replaced by two and two removed in a service, a store added
# whole, a lock file rewritten, and a picture the change shows no line of
SERVICE_FILE = changed_file(SERVICE, hunk(10, 10, "  -++ -- "))
STORE_FILE = changed_file(STORE, hunk(0, 1, "+++"), status=FileStatus.ADDED)
LOCK_FILE = changed_file(LOCK, hunk(3, 3, " -+ "))
LOGO_FILE = DiffFile(path=LOGO, status=FileStatus.ADDED, hunks=[], unshown=Unshown.BINARY)
CHANGE = [SERVICE_FILE, STORE_FILE, LOCK_FILE, LOGO_FILE]
# Steps that between them tell everything the service and the store changed
WHOLE_SERVICE = [step(SERVICE, 12, 13), step(SERVICE, 15, 15)]
WHOLE_STORE = step(STORE, 1, 3)
# Where the first step of a story of one chapter stands, and the first file it names as housekeeping
FIRST_STEP: FieldPath = ("chapters", 0, "steps", 0)
FIRST_HOUSEKEEPING: FieldPath = ("housekeeping", 0)


def changed_lines(files: list[DiffFile]) -> int:
    """How many lines the change added or removed in these files."""
    return sum(changed_in(lines_of(file)) for file in files)


def refusal_of(story: Story[Step]) -> list[StoryFault]:
    """What a story is refused with against the change: every fault, as it was found."""
    with pytest.raises(StoryRefusedError) as refused:
        tell(story, CHANGE)
    return refused.value.faults


def paths_of(faults: list[StoryFault]) -> list[FieldPath]:
    return [fault.path for fault in faults]


def test_a_story_is_told_with_the_piece_of_the_change_each_step_shows() -> None:
    told = tell(story_of(*WHOLE_SERVICE, WHOLE_STORE, housekeeping=(LOCK, LOGO)), CHANGE)

    assert [rows_of(told_step.piece) for told_step in told.chapters[0].steps] == [
        ["-12/", "+/12", "+/13"],
        ["-14/", "-15/", " 16/15"],
        ["+/1", "+/2", "+/3"],
    ]


def test_a_told_story_says_everything_the_story_said() -> None:
    story = story_of(*WHOLE_SERVICE, WHOLE_STORE, housekeeping=(LOCK, LOGO))

    told = tell(story, CHANGE)

    assert (told.title, told.overview, told.housekeeping) == (story.title, story.overview, story.housekeeping)
    assert [(chapter.id, chapter.title, chapter.why, chapter.doubt) for chapter in told.chapters] == [
        (chapter.id, chapter.title, chapter.why, chapter.doubt) for chapter in story.chapters
    ]
    assert [(told_step.file, told_step.lines) for told_step in told.chapters[0].steps] == [
        (written.file, written.lines) for written in story.chapters[0].steps
    ]


def test_a_story_that_tells_or_names_everything_leaves_nothing_out() -> None:
    told = tell(story_of(*WHOLE_SERVICE, WHOLE_STORE, housekeeping=(LOCK, LOGO)), CHANGE)

    assert told.left_out == []


def test_what_no_step_tells_of_a_file_is_left_out_beside_the_story_and_counted() -> None:
    told = tell(story_of(step(SERVICE, 12, 13), WHOLE_STORE, housekeeping=(LOCK, LOGO)), CHANGE)

    [left] = told.left_out

    assert left.piece.path == SERVICE
    assert rows_of(left.piece) == [" 13/14", "-14/", "-15/", " 16/15"]
    assert left.changed_lines == 2


def test_a_file_no_step_tells_and_nobody_named_is_left_out_whole_in_the_order_of_the_change() -> None:
    told = tell(story_of(*WHOLE_SERVICE), CHANGE)

    assert [(left.piece.path, left.changed_lines) for left in told.left_out] == [(STORE, 3), (LOCK, 2), (LOGO, 0)]
    assert rows_of(told.left_out[0].piece) == ["+/1", "+/2", "+/3"]


def test_a_step_tells_lines_of_its_own_file_and_of_no_other() -> None:
    """The store's step is of lines 1 to 3; the lock file's line 3 is not told for that."""
    told = tell(story_of(WHOLE_STORE, housekeeping=(LOGO,)), CHANGE)

    assert [(left.piece.path, rows_of(left.piece)) for left in told.left_out] == [
        (SERVICE, rows_of(SERVICE_FILE)),
        (LOCK, rows_of(LOCK_FILE)),
    ]


def test_a_file_the_change_shows_no_line_of_is_left_out_as_the_file_it_is() -> None:
    """Nothing of it can be told in a step, and it changed all the same: it is shown as the review shows it."""
    told = tell(story_of(*WHOLE_SERVICE, WHOLE_STORE, housekeeping=(LOCK,)), CHANGE)

    [left] = told.left_out

    assert left.piece == LOGO_FILE
    assert left.changed_lines == 0


def test_every_line_the_change_added_or_removed_is_told_left_out_or_housekeeping() -> None:
    told = tell(story_of(step(SERVICE, 12, 13), housekeeping=(LOCK,)), CHANGE)

    told_lines = changed_lines([told_step.piece for chapter in told.chapters for told_step in chapter.steps])
    left_lines = sum(left.changed_lines for left in told.left_out)
    housekeeping_lines = changed_lines([LOCK_FILE])

    assert told_lines + left_lines + housekeeping_lines == changed_lines(CHANGE)


def test_a_step_told_of_a_file_the_change_does_not_have_is_refused() -> None:
    assert paths_of(refusal_of(story_of(step("src/elsewhere.py", 1, 5)))) == [(*FIRST_STEP, "file")]


def test_a_step_told_of_a_file_the_change_shows_no_line_of_is_refused() -> None:
    assert paths_of(refusal_of(story_of(step(LOGO, 1, 5)))) == [(*FIRST_STEP, "file")]


@pytest.mark.parametrize(("first", "last"), [(14, 14), (30, 40)])
def test_a_step_whose_lines_hold_nothing_the_change_did_is_refused(first: int, last: int) -> None:
    """A line the change only kept, or lines the change does not show at all: a step tells something it did."""
    [fault] = refusal_of(story_of(step(SERVICE, first, last)))

    assert fault.path == (*FIRST_STEP, "lines")
    assert SERVICE in fault.reason


def test_a_housekeeping_file_the_change_does_not_have_is_refused() -> None:
    assert paths_of(refusal_of(story_of(*WHOLE_SERVICE, housekeeping=("CHANGELOG.md",)))) == [FIRST_HOUSEKEEPING]


def test_a_file_named_as_housekeeping_and_told_in_a_step_is_refused_naming_the_chapter() -> None:
    """It is housekeeping because it has nothing to tell."""
    [fault] = refusal_of(story_of(*WHOLE_SERVICE, housekeeping=(SERVICE,)))

    assert fault.path == FIRST_HOUSEKEEPING
    assert ONLY_CHAPTER in fault.reason


def test_lines_already_refused_for_their_numbers_are_not_also_held_to_tell_nothing() -> None:
    assert paths_of(refusal_of(story_of(step(SERVICE, 13, 12)))) == [(*FIRST_STEP, "lines")]


def test_what_is_wrong_with_the_document_and_what_is_wrong_against_the_change_are_said_together() -> None:
    untitled = planted(story_of(step(SERVICE, 14, 14), housekeeping=("CHANGELOG.md",)), ("title",), "")

    assert paths_of(refusal_of(untitled)) == [("title",), (*FIRST_STEP, "lines"), FIRST_HOUSEKEEPING]
