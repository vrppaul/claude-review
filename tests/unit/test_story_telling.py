"""Functional requirement tests for telling a story of a change: placed on it, or refused with everything wrong.

A story that may be told carries, step by step, the piece of the change each
step shows. Whatever the change did that no step tells is set beside it, so
a story cannot hide a line; and one told of something the change does not
hold is refused, with all of it said at once.

A round's work then moves the code under the story. The story follows it,
each step its own lines as a thread does, and shows the code as it now
stands: a step whose code changed after it was told is marked, and what the
round added that no step tells is left out.
"""

import pytest

from claude_review.domain.exceptions import FieldFault, FieldPath, StoryRefusedError
from claude_review.domain.models import NO_HUNK_HEADER, DiffFile, DiffHunk, DiffLine, FileStatus, LineSpan, Unshown
from claude_review.domain.story import Step, Story, ToldStep, ToldStory
from claude_review.services.story_telling import follow, tell
from tests.helpers import added_line, removed_line
from tests.stories import (
    ONLY_CHAPTER,
    changed_file,
    changed_in,
    chapter_of,
    hunk,
    lines_of,
    planted,
    rows_of,
    step,
    story_of,
    story_of_chapters,
)

SERVICE = "src/service.py"
STORE = "src/store.py"
LOCK = "uv.lock"
LOGO = "docs/logo.png"

# The change every test here tells: one line replaced by two and two removed in a service, a store added
# whole, a lock file rewritten, and a picture the change shows no line of
SERVICE_FILE = changed_file(SERVICE, hunk(10, 10, "  -++ -- "))
STORE_FILE = changed_file(STORE, hunk(1, 1, "+++"), status=FileStatus.ADDED)
LOCK_FILE = changed_file(LOCK, hunk(3, 3, " -+ "))
LOGO_FILE = DiffFile(path=LOGO, status=FileStatus.ADDED, hunks=[], unshown=Unshown.BINARY)
CHANGE = [SERVICE_FILE, STORE_FILE, LOCK_FILE, LOGO_FILE]
# Steps that between them tell everything the service and the store changed
WHOLE_SERVICE = [step(SERVICE, 12, 13), step(SERVICE, 15, 15)]
WHOLE_STORE = step(STORE, 1, 3)
# What a told story holds that the story as written does not: the piece each step shows and whether it changed
# since, and what is left out
WHAT_TELLING_ADDS = {"left_out": True, "chapters": {"__all__": {"steps": {"__all__": {"piece", "changed_since_told"}}}}}
# Where the first step of a story of one chapter stands, and the first file it names as housekeeping
FIRST_STEP: FieldPath = ("chapters", 0, "steps", 0)
FIRST_HOUSEKEEPING: FieldPath = ("housekeeping", 0)
# Two chapters of one story, for a file told in both
EARLIER_CHAPTER = "ch-earlier"
LATER_CHAPTER = "ch-later"

# A file of seven lines, "a" to "g", whose second and sixth lines the change rewrote, and a file it added whole
LETTERS = "src/letters.py"
ADDED = "src/added.py"


def hunk_of_lines(old_start: int, new_start: int, *lines: DiffLine) -> DiffHunk:
    """A hunk of these rows, starting on each side where its first row stands there."""
    return DiffHunk(header=NO_HUNK_HEADER, old_start=old_start, new_start=new_start, lines=list(lines))


# The change a story is told of, and how the round's work leaves it. Rewritten: "b" as "B", and "f" as "F"
LINE_B = hunk_of_lines(2, 2, removed_line(2, "b"), added_line(2, "B"))
LINE_F = hunk_of_lines(6, 6, removed_line(6, "f"), added_line(6, "F"))
LETTERS_TOLD = changed_file(LETTERS, LINE_B, LINE_F)
# Two lines put above everything: what the change rewrote stands two lines further down, said as it was
PUSHED_DOWN = changed_file(
    LETTERS,
    hunk_of_lines(1, 1, added_line(1, "first"), added_line(2, "second")),
    hunk_of_lines(2, 4, removed_line(2, "b"), added_line(4, "B")),
    hunk_of_lines(6, 8, removed_line(6, "f"), added_line(8, "F")),
)
# "B" said another way
B_REWORDED = changed_file(LETTERS, hunk_of_lines(2, 2, removed_line(2, "b"), added_line(2, "Bee")), LINE_F)
# A line put between the two rewritten, under "d"
LINE_BETWEEN = changed_file(
    LETTERS,
    LINE_B,
    hunk_of_lines(5, 5, added_line(5, "between")),
    hunk_of_lines(6, 7, removed_line(6, "f"), added_line(7, "F")),
)
# Four lines added whole, and how the round's work leaves them: a line put above them, and the third said
# another way; or a line added below them
FOUR_ADDED = changed_file(
    ADDED,
    hunk_of_lines(0, 1, added_line(1, "one"), added_line(2, "two"), added_line(3, "three"), added_line(4, "four")),
    status=FileStatus.ADDED,
)
ONE_ABOVE_AND_THE_THIRD_REWORDED = changed_file(
    ADDED,
    hunk_of_lines(
        0,
        1,
        added_line(1, "zero"),
        added_line(2, "one"),
        added_line(3, "two"),
        added_line(4, "Three"),
        added_line(5, "four"),
    ),
    status=FileStatus.ADDED,
)
ONE_BELOW = changed_file(
    ADDED,
    hunk_of_lines(
        0,
        1,
        added_line(1, "one"),
        added_line(2, "two"),
        added_line(3, "three"),
        added_line(4, "four"),
        added_line(5, "five"),
    ),
    status=FileStatus.ADDED,
)


def followed(story: Story[Step], told_of: list[DiffFile], now: list[DiffFile]) -> ToldStory:
    """A story told of one take of the change, followed onto the next."""
    return follow(tell(story, told_of), now)


def steps_of(told: ToldStory) -> list[ToldStep]:
    """Every step of a story, in the order it tells them."""
    return [told_step for chapter in told.chapters for told_step in chapter.steps]


def changed_lines(files: list[DiffFile]) -> int:
    """How many lines the change added or removed in these files."""
    return sum(changed_in(lines_of(file)) for file in files)


def refusal_of(story: Story[Step]) -> list[FieldFault]:
    """What a story is refused with against the change: every fault, as it was found."""
    with pytest.raises(StoryRefusedError) as refused:
        tell(story, CHANGE)
    return refused.value.faults


def paths_of(faults: list[FieldFault]) -> list[FieldPath]:
    return [fault.path for fault in faults]


def test_a_story_is_told_with_the_piece_of_the_change_each_step_shows() -> None:
    told = tell(story_of(*WHOLE_SERVICE, WHOLE_STORE, housekeeping=(LOCK, LOGO)), CHANGE)

    assert [rows_of(told_step.piece) for told_step in told.chapters[0].steps] == [
        ["-12/", "+/12", "+/13"],
        ["-14/", "-15/", " 16/15"],
        ["+/1", "+/2", "+/3"],
    ]


def test_a_told_story_says_everything_the_story_said() -> None:
    reasoned = planted(story_of(*WHOLE_SERVICE, WHOLE_STORE, housekeeping=(LOCK, LOGO)), (*FIRST_STEP, "reason"), "So.")
    story = planted(reasoned, ("overview", "doubt"), "Whether it holds.")

    told = tell(story, CHANGE)

    assert told.model_dump(exclude=WHAT_TELLING_ADDS) == story.model_dump()


def test_a_change_of_a_files_mode_is_said_with_every_step_of_it_and_with_what_is_left_out() -> None:
    """Whether a file may be run is a change too: told nowhere, a story would hide it."""
    made_runnable = DiffFile(
        path=SERVICE, status=FileStatus.MODIFIED, hunks=SERVICE_FILE.hunks, old_mode="100644", new_mode="100755"
    )

    told = tell(story_of(step(SERVICE, 12, 13)), [made_runnable])

    pieces = [*(told_step.piece for told_step in told.chapters[0].steps), *(left.piece for left in told.left_out)]
    assert [(piece.old_mode, piece.new_mode) for piece in pieces] == [("100644", "100755"), ("100644", "100755")]


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


def test_a_housekeeping_file_told_in_several_chapters_is_refused_naming_the_first_that_tells_it() -> None:
    """As a line told twice names the chapter that told it first: the agent is sent to the same place every time."""
    told_in_two = story_of_chapters(
        chapter_of(EARLIER_CHAPTER, step(SERVICE, 12, 13)),
        chapter_of(LATER_CHAPTER, step(SERVICE, 15, 15)),
        housekeeping=(SERVICE,),
    )

    [fault] = refusal_of(told_in_two)

    assert (EARLIER_CHAPTER in fault.reason, LATER_CHAPTER in fault.reason) == (True, False)


def test_lines_already_refused_for_their_numbers_are_not_also_held_to_tell_nothing() -> None:
    assert paths_of(refusal_of(story_of(step(SERVICE, 13, 12)))) == [(*FIRST_STEP, "lines")]


def test_what_is_wrong_with_the_document_and_what_is_wrong_against_the_change_are_said_together() -> None:
    untitled = planted(story_of(step(SERVICE, 14, 14), housekeeping=("CHANGELOG.md",)), ("title",), "")

    assert paths_of(refusal_of(untitled)) == [("title",), (*FIRST_STEP, "lines"), FIRST_HOUSEKEEPING]


def test_a_story_as_told_marks_no_step_changed() -> None:
    told = tell(story_of(step(LETTERS, 2, 2), step(LETTERS, 6, 6)), [LETTERS_TOLD])

    assert [told_step.changed_since_told for told_step in steps_of(told)] == [False, False]


def test_steps_whose_code_moved_down_unchanged_follow_it_unmarked() -> None:
    story = followed(story_of(step(LETTERS, 2, 2), step(LETTERS, 6, 6)), [LETTERS_TOLD], [PUSHED_DOWN])

    assert [
        (told_step.lines, rows_of(told_step.piece), told_step.changed_since_told) for told_step in steps_of(story)
    ] == [
        (LineSpan(first=4, last=4), ["b", "B"], False),
        (LineSpan(first=8, last=8), ["f", "F"], False),
    ]


def test_a_step_whose_line_was_said_another_way_stays_on_its_lines_marked_showing_the_code_as_it_now_stands() -> None:
    [told_step, _] = steps_of(
        followed(story_of(step(LETTERS, 2, 2), step(LETTERS, 6, 6)), [LETTERS_TOLD], [B_REWORDED])
    )

    assert told_step.lines == LineSpan(first=2, last=2)
    assert rows_of(told_step.piece) == ["b", "Bee"]
    assert told_step.changed_since_told is True


def test_a_step_with_a_line_put_between_its_pieces_takes_it_in_and_is_marked() -> None:
    [told_step] = steps_of(followed(story_of(step(LETTERS, 2, 6)), [LETTERS_TOLD], [LINE_BETWEEN]))

    assert told_step.lines == LineSpan(first=2, last=7)
    assert rows_of(told_step.piece) == ["b", "B", "between", "f", "F"]
    assert told_step.changed_since_told is True


def test_a_step_whose_file_left_the_change_shows_its_file_with_no_rows_and_is_marked() -> None:
    [told_step, _] = steps_of(
        followed(story_of(step(LETTERS, 2, 2), step(ADDED, 1, 4)), [LETTERS_TOLD, FOUR_ADDED], [FOUR_ADDED])
    )

    assert (told_step.piece.path, told_step.piece.hunks) == (LETTERS, [])
    assert told_step.lines == LineSpan(first=2, last=2)
    assert told_step.changed_since_told is True


def test_a_line_the_round_added_outside_every_step_is_left_out_and_counted() -> None:
    story = followed(story_of(step(ADDED, 1, 4)), [FOUR_ADDED], [ONE_BELOW])

    [left] = story.left_out
    assert (rows_of(left.piece), left.changed_lines) == (["five"], 1)
    assert steps_of(story)[0].changed_since_told is False


def test_steps_of_a_file_that_would_meet_once_followed_all_stay_on_their_lines() -> None:
    """The first step's lines followed would take a line the second, lost, still tells: no line is told twice."""
    story = followed(story_of(step(ADDED, 1, 2), step(ADDED, 3, 4)), [FOUR_ADDED], [ONE_ABOVE_AND_THE_THIRD_REWORDED])

    assert [(told_step.lines, told_step.changed_since_told) for told_step in steps_of(story)] == [
        (LineSpan(first=1, last=2), True),
        (LineSpan(first=3, last=4), True),
    ]
