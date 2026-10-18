"""Functional requirement tests for telling a story of a change: placed on it, or refused with everything wrong.

A story that may be told carries, step by step, the piece of the change each
step shows. Whatever the change did that no step tells is set beside it, so
a story cannot hide a line; and one told of something the change does not
hold is refused, with all of it said at once.

A round's work then moves the code under the story. The story follows it,
each step its own lines through what changed between the take it was told
of and the later one, and shows the code as it now stands: a step whose
code changed after it was told is marked, and what the round added that no
step tells is left out.
"""

from itertools import pairwise

import pytest
from hypothesis import given, strategies as strategy

from claude_review.domain.exceptions import FieldFault, FieldPath, StoryRefusedError
from claude_review.domain.models import NO_HUNK_HEADER, DiffFile, DiffHunk, DiffLine, FileStatus, LineSpan, Unshown
from claude_review.domain.story import FollowedStep, Step, StepNow, Story, ToldStory
from claude_review.services.story_telling import as_told, follow, tell
from tests.helpers import added_line, context_line, removed_line
from tests.stories import (
    ONLY_CHAPTER,
    changed_file,
    changed_in,
    diff_of,
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
# What a told story holds that the story as written does not: the piece each step shows, and what is left out
WHAT_TELLING_ADDS = {"left_out": True, "chapters": {"__all__": {"steps": {"__all__": {"piece"}}}}}
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


def added_whole(path: str, contents: list[str]) -> DiffFile:
    """A file the change added whole, saying these lines in order."""
    numbered = [added_line(number, content) for number, content in enumerate(contents, start=1)]
    return changed_file(path, hunk_of_lines(0, 1, *numbered), status=FileStatus.ADDED)


# The change a story is told of, and how the round's work leaves it. Rewritten: "b" as "B", and "f" as "F"
LINE_B = hunk_of_lines(2, 2, removed_line(2, "b"), added_line(2, "B"))
LINE_F = hunk_of_lines(6, 6, removed_line(6, "f"), added_line(6, "F"))
LETTERS_TOLD = changed_file(LETTERS, LINE_B, LINE_F)
# What the file says before the change, and as the change was told of
LETTERS_BEFORE = ["a", "b", "c", "d", "e", "f", "g"]
LETTERS_AS_TOLD = ["a", "B", "c", "d", "e", "F", "g"]
# Two lines put above everything: what the change rewrote stands two lines further down, said as it was
PUSHED_DOWN = changed_file(
    LETTERS,
    hunk_of_lines(1, 1, added_line(1, "first"), added_line(2, "second")),
    hunk_of_lines(2, 4, removed_line(2, "b"), added_line(4, "B")),
    hunk_of_lines(6, 8, removed_line(6, "f"), added_line(8, "F")),
)
PUSHED_DOWN_LINES = ["first", "second", *LETTERS_AS_TOLD]
# "B" taken out again: "b" stays removed, and what stood below it moves up a line
B_TAKEN_OUT = changed_file(
    LETTERS,
    hunk_of_lines(2, 2, removed_line(2, "b")),
    hunk_of_lines(6, 5, removed_line(6, "f"), added_line(5, "F")),
)
B_TAKEN_OUT_LINES = ["a", "c", "d", "e", "F", "g"]
# A line put between the two rewritten, under "d"
LINE_BETWEEN = changed_file(
    LETTERS,
    LINE_B,
    hunk_of_lines(5, 5, added_line(5, "between")),
    hunk_of_lines(6, 7, removed_line(6, "f"), added_line(7, "F")),
)
LINE_BETWEEN_LINES = ["a", "B", "c", "d", "between", "e", "F", "g"]
# Four lines added whole, and how the round's work leaves them: a line added below them
FOUR_LINES = ["one", "two", "three", "four"]
FOUR_ADDED = added_whole(ADDED, FOUR_LINES)
ONE_BELOW_LINES = [*FOUR_LINES, "five"]
# Two lines a change added below four it kept, and how a round's work leaves them: two lines put above
# everything, and the first of the two said another way
NUMBERS = "src/numbers.py"
FIVE_AND_SIX = changed_file(NUMBERS, hunk_of_lines(5, 5, added_line(5, "five"), added_line(6, "six")))
NUMBERS_KEPT = [f"kept {number}" for number in range(1, 5)]
FIVE_AND_SIX_LINES = [*NUMBERS_KEPT, "five", "six"]
TWO_ABOVE_AND_FIVE_REWORDED = changed_file(
    NUMBERS,
    hunk_of_lines(1, 1, added_line(1, "first"), added_line(2, "second")),
    hunk_of_lines(5, 7, added_line(7, "FIVE"), added_line(8, "six")),
)
TWO_ABOVE_AND_FIVE_REWORDED_LINES = ["first", "second", *NUMBERS_KEPT, "FIVE", "six"]
# Five lines added whole, and how a round's work leaves them: a line put above, and the fourth taken out
FIVE_LINES = ["a", "x", "y", "x", "z"]
ONE_ABOVE_AND_THE_FOURTH_GONE = ["new", "a", "x", "y", "z"]
# Four lines added whole that all say the same, and a fifth like them put in
FOUR_THE_SAME = ["x"] * 4
FIVE_THE_SAME = ["x"] * 5
# A file whose first line the change kept and whose second it added, and how a round's work leaves it: the same
# two lines, both added
KEPT_THEN_ADDED = changed_file(LETTERS, hunk_of_lines(1, 1, context_line(1, 1, "a"), added_line(2, "x")))
BOTH_ADDED = changed_file(LETTERS, hunk_of_lines(1, 1, added_line(1, "a"), added_line(2, "x")))
# A file added whole, for the cases where a step that looked for its lines by what they said lost its code
CODE = "src/code.py"
# Twenty lines added whole, and how a round's work leaves them: one of them taken out, or a line put in after
# the fifth
TWENTY = "src/twenty.py"
TWENTY_LINES = [f"line {number}" for number in range(1, 21)]
PUT_IN = "put in"
FIRST_TAKEN_OUT = TWENTY_LINES[1:]
THIRD_TAKEN_OUT = [*TWENTY_LINES[:2], *TWENTY_LINES[3:]]
FIFTH_TAKEN_OUT = [*TWENTY_LINES[:4], *TWENTY_LINES[5:]]
PUT_IN_AFTER_THE_FIFTH = [*TWENTY_LINES[:5], PUT_IN, *TWENTY_LINES[5:]]
# The first ten taken out whole: the last ten move up to where they stood
ELEVENTH_ON = TWENTY_LINES[10:]
# How many lines a take of the twenty may have, as a round's work leaves them, and how many steps a story of
# them tells at most, counted by the lines that start and end them
MOST_LINES_NOW = 30
MOST_STEP_EDGES = 12
# A line past the last of the twenty, where a step that ends at the last stops
PAST_THE_TWENTY = len(TWENTY_LINES) + 1


@strategy.composite
def steps_of_the_twenty(draw: strategy.DrawFn) -> list[Step]:
    """Steps of the twenty lines that share no line, as a story's must."""
    edges = sorted(
        draw(
            strategy.lists(
                strategy.integers(min_value=1, max_value=PAST_THE_TWENTY),
                unique=True,
                min_size=2,
                max_size=MOST_STEP_EDGES,
            )
        )
    )
    return [step(TWENTY, first, following - 1) for first, following in zip(edges[::2], edges[1::2], strict=False)]


def takes_of_the_twenty() -> strategy.SearchStrategy[list[str]]:
    """The twenty lines as any round's work could leave them: taken out, put in again elsewhere, said twice, or new."""
    return strategy.lists(strategy.sampled_from([*TWENTY_LINES, PUT_IN]), min_size=1, max_size=MOST_LINES_NOW)


def followed(
    story: Story[Step], told_of: list[DiffFile], now: list[DiffFile], since_told: list[DiffFile]
) -> ToldStory[FollowedStep]:
    """A story told of one take of the change, followed onto the next, `since_told` being what changed between them."""
    return follow(tell(story, told_of), now, since_told)


def followed_whole(story: Story[Step], path: str, told: list[str], now: list[str]) -> ToldStory[FollowedStep]:
    """A story of a file the change added whole, saying these lines, followed onto a take where it says those."""
    return follow(tell(story, [added_whole(path, told)]), [added_whole(path, now)], [diff_of(path, told, now)])


def where_it_stands(followed_step: FollowedStep) -> tuple[LineSpan, list[str], bool]:
    """A step placed on a later take: the lines it stands at, what its rows say, and whether they changed since told."""
    return followed_step.now.lines, rows_of(followed_step.now.piece), followed_step.now.changed_since_told


# The lines of a take a step's code stands on, by whether it stands anywhere: none where it does not
LINES_NOW = {StepNow: lambda now: [now.lines], type(None): lambda _: []}


def lines_now(followed_step: FollowedStep) -> list[LineSpan]:
    """The lines of a later take a step's code stands on: one run of them, or none where it stands nowhere."""
    return LINES_NOW[type(followed_step.now)](followed_step.now)


def first_of(lines: LineSpan) -> int:
    """The first of some lines, which lines are put in the order of."""
    return lines.first


def steps_of[StepKind: Step](told: ToldStory[StepKind]) -> list[StepKind]:
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
    """Named the same chapter however many tell it, the agent is sent to the same place every time."""
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
    told = as_told(tell(story_of(step(LETTERS, 2, 2), step(LETTERS, 6, 6)), [LETTERS_TOLD]))

    assert [told_step.now.changed_since_told for told_step in steps_of(told)] == [False, False]


def test_steps_whose_code_moved_down_unchanged_follow_it_unmarked() -> None:
    story = followed(
        story_of(step(LETTERS, 2, 2), step(LETTERS, 6, 6)),
        [LETTERS_TOLD],
        [PUSHED_DOWN],
        [diff_of(LETTERS, LETTERS_AS_TOLD, PUSHED_DOWN_LINES)],
    )

    assert [where_it_stands(told_step) for told_step in steps_of(story)] == [
        (LineSpan(first=4, last=4), ["b", "B"], False),
        (LineSpan(first=8, last=8), ["f", "F"], False),
    ]


def test_steps_of_one_file_in_two_chapters_each_follow_their_own_code() -> None:
    """The later chapter tells the earlier lines: each step is its own wherever the story tells it."""
    story = story_of_chapters(
        chapter_of(EARLIER_CHAPTER, step(LETTERS, 6, 6)), chapter_of(LATER_CHAPTER, step(LETTERS, 2, 2))
    )

    pushed_down = followed(story, [LETTERS_TOLD], [PUSHED_DOWN], [diff_of(LETTERS, LETTERS_AS_TOLD, PUSHED_DOWN_LINES)])

    assert [told_step.now.lines for told_step in steps_of(pushed_down)] == [
        LineSpan(first=8, last=8),
        LineSpan(first=4, last=4),
    ]


def test_a_step_whose_lines_a_round_took_out_shows_no_code_and_is_marked_on_the_lines_it_was_told_of() -> None:
    """Its only line is gone: the review draws no code as its own, and none at its old numbers."""
    [told_step, _] = steps_of(
        followed(
            story_of(step(LETTERS, 2, 2), step(LETTERS, 6, 6)),
            [LETTERS_TOLD],
            [B_TAKEN_OUT],
            [diff_of(LETTERS, LETTERS_AS_TOLD, B_TAKEN_OUT_LINES)],
        )
    )

    assert (told_step.now, told_step.lines) == (None, LineSpan(first=2, last=2))


def test_what_a_step_that_stands_nowhere_told_is_left_out() -> None:
    """No step shows it now: it is not hidden behind a step that shows nothing."""
    story = followed(
        story_of(step(LETTERS, 2, 2), step(LETTERS, 6, 6)),
        [LETTERS_TOLD],
        [B_TAKEN_OUT],
        [diff_of(LETTERS, LETTERS_AS_TOLD, B_TAKEN_OUT_LINES)],
    )

    assert [rows_of(left.piece) for left in story.left_out] == [["b"]]


def test_a_step_with_a_line_put_between_its_pieces_takes_it_in_and_is_marked() -> None:
    [told_step] = steps_of(
        followed(
            story_of(step(LETTERS, 2, 6)),
            [LETTERS_TOLD],
            [LINE_BETWEEN],
            [diff_of(LETTERS, LETTERS_AS_TOLD, LINE_BETWEEN_LINES)],
        )
    )

    assert where_it_stands(told_step) == (LineSpan(first=2, last=7), ["b", "B", "between", "f", "F"], True)


def test_a_step_a_line_of_which_the_change_now_adds_where_it_kept_it_is_marked() -> None:
    """Every row still says what it said, and nothing moved between the takes: what the change does to a row changed."""
    [told_step] = steps_of(followed(story_of(step(LETTERS, 1, 2)), [KEPT_THEN_ADDED], [BOTH_ADDED], []))

    assert told_step.now.changed_since_told is True


def test_a_step_whose_file_left_the_change_shows_no_code_and_is_marked_on_the_lines_it_was_told_of() -> None:
    """Its file no longer differs: no status it was told with is true of it now."""
    [told_step, _] = steps_of(
        followed(
            story_of(step(LETTERS, 2, 2), step(ADDED, 1, 4)),
            [LETTERS_TOLD, FOUR_ADDED],
            [FOUR_ADDED],
            [diff_of(LETTERS, LETTERS_AS_TOLD, LETTERS_BEFORE)],
        )
    )

    assert (told_step.now, told_step.lines) == (None, LineSpan(first=2, last=2))


def test_a_step_is_placed_nowhere_where_what_changed_since_it_was_told_cannot_be_said() -> None:
    """The tree it was told of was never written down, say: nothing is drawn as its code on a guess."""
    story = tell(story_of(step(LETTERS, 2, 2), step(LETTERS, 6, 6)), [LETTERS_TOLD])

    assert [told_step.now for told_step in steps_of(follow(story, [LETTERS_TOLD], None))] == [None, None]


def test_a_line_the_round_added_outside_every_step_is_left_out_and_counted() -> None:
    story = followed_whole(story_of(step(ADDED, 1, 4)), ADDED, FOUR_LINES, ONE_BELOW_LINES)

    [left] = story.left_out
    assert (rows_of(left.piece), left.changed_lines) == (["five"], 1)
    assert steps_of(story)[0].now.changed_since_told is False


def test_a_step_a_line_of_which_was_said_another_way_keeps_it_moved_with_the_rest_and_marked() -> None:
    """Pushed down and its first line rewritten: the line said another way is still the step's."""
    [told_step] = steps_of(
        followed(
            story_of(step(NUMBERS, 5, 6)),
            [FIVE_AND_SIX],
            [TWO_ABOVE_AND_FIVE_REWORDED],
            [diff_of(NUMBERS, FIVE_AND_SIX_LINES, TWO_ABOVE_AND_FIVE_REWORDED_LINES)],
        )
    )

    assert where_it_stands(told_step) == (LineSpan(first=7, last=8), ["FIVE", "six"], True)


def test_a_step_of_lines_that_all_say_the_same_moves_as_the_diff_between_the_takes_says() -> None:
    """Nothing in what they say tells such lines apart: the diff says the new one was put in below them."""
    [told_step] = steps_of(followed_whole(story_of(step(CODE, 2, 3)), CODE, FOUR_THE_SAME, FIVE_THE_SAME))

    assert (told_step.now.lines, told_step.now.changed_since_told) == (LineSpan(first=2, last=3), False)


def test_a_step_a_round_took_out_stands_nowhere_and_the_steps_beside_it_keep_their_code() -> None:
    """The step taken out says what a line of the step above says: what moved is said by the diff, not by words."""
    story = followed_whole(
        story_of(step(CODE, 1, 2), step(CODE, 4, 4), step(CODE, 5, 5)), CODE, FIVE_LINES, ONE_ABOVE_AND_THE_FOURTH_GONE
    )

    [above, taken_out, below] = steps_of(story)
    assert where_it_stands(above) == (LineSpan(first=2, last=3), ["a", "x"], False)
    assert (taken_out.now, taken_out.lines) == (None, LineSpan(first=4, last=4))
    assert where_it_stands(below) == (LineSpan(first=5, last=5), ["z"], False)


def test_a_line_taken_out_inside_a_step_brings_its_end_up_and_leaves_the_next_step_its_code() -> None:
    story = followed_whole(story_of(step(TWENTY, 1, 10), step(TWENTY, 11, 20)), TWENTY, TWENTY_LINES, FIFTH_TAKEN_OUT)

    assert [where_it_stands(told_step) for told_step in steps_of(story)] == [
        (LineSpan(first=1, last=9), [*TWENTY_LINES[:4], *TWENTY_LINES[5:10]], True),
        (LineSpan(first=10, last=19), TWENTY_LINES[10:], False),
    ]


def test_a_line_put_inside_a_step_takes_its_end_down_and_leaves_the_next_step_its_code() -> None:
    story = followed_whole(
        story_of(step(TWENTY, 1, 10), step(TWENTY, 11, 20)), TWENTY, TWENTY_LINES, PUT_IN_AFTER_THE_FIFTH
    )

    assert [where_it_stands(told_step) for told_step in steps_of(story)] == [
        (LineSpan(first=1, last=11), [*TWENTY_LINES[:5], PUT_IN, *TWENTY_LINES[5:10]], True),
        (LineSpan(first=12, last=21), TWENTY_LINES[10:], False),
    ]


def test_a_line_taken_out_of_the_first_of_three_steps_leaves_every_step_its_code() -> None:
    story = followed_whole(
        story_of(step(TWENTY, 1, 5), step(TWENTY, 6, 10), step(TWENTY, 15, 20)), TWENTY, TWENTY_LINES, THIRD_TAKEN_OUT
    )

    assert [where_it_stands(told_step) for told_step in steps_of(story)] == [
        (LineSpan(first=1, last=4), [*TWENTY_LINES[:2], *TWENTY_LINES[3:5]], True),
        (LineSpan(first=5, last=9), TWENTY_LINES[5:10], False),
        (LineSpan(first=14, last=19), TWENTY_LINES[14:], False),
    ]


def test_a_step_whose_first_line_was_taken_out_starts_where_what_is_left_of_it_starts() -> None:
    [told_step] = steps_of(followed_whole(story_of(step(TWENTY, 1, 10)), TWENTY, TWENTY_LINES, FIRST_TAKEN_OUT))

    assert where_it_stands(told_step) == (LineSpan(first=1, last=9), TWENTY_LINES[1:10], True)


def test_a_step_whose_first_line_was_reworded_keeps_it_marked() -> None:
    told = ["def handle(request):", "    return answer(request)", ""]
    now = ["def handle(request, *, strict):", "    return answer(request)", ""]

    [told_step] = steps_of(followed_whole(story_of(step(CODE, 1, 2)), CODE, told, now))

    assert where_it_stands(told_step) == (LineSpan(first=1, last=2), now[:2], True)


def test_a_step_of_one_line_said_another_way_stays_on_it_marked() -> None:
    told = ["a = 1", "LIMIT = 10", "b = 2"]
    now = ["a = 1", "LIMIT = 20", "b = 2"]

    [told_step] = steps_of(followed_whole(story_of(step(CODE, 2, 2)), CODE, told, now))

    assert where_it_stands(told_step) == (LineSpan(first=2, last=2), ["LIMIT = 20"], True)


def test_a_step_whose_lines_were_all_rewritten_in_place_stays_on_them_marked() -> None:
    told = ["x = 1", "def f():", "    return 1", "y = 2"]
    now = ["x = 1", "def g():", "    return 2", "y = 2"]

    [told_step] = steps_of(followed_whole(story_of(step(CODE, 2, 3)), CODE, told, now))

    assert where_it_stands(told_step) == (LineSpan(first=2, last=3), now[1:3], True)


def test_a_step_whose_one_line_left_as_it_was_is_a_brace_moves_with_its_code_and_onto_no_other() -> None:
    """Two lines put above, and the two above its brace rewritten: the brace of the code above it says the same."""
    told = ["x = 1", "}", "def f() {", "    work()", "}", "y = 2"]
    now = ["import a", "import b", "x = 1", "}", "def f(arg) {", "    work(arg)", "}", "y = 2"]

    [told_step] = steps_of(followed_whole(story_of(step(CODE, 3, 5)), CODE, told, now))

    assert where_it_stands(told_step) == (LineSpan(first=5, last=7), now[4:7], True)


def test_a_step_whose_one_line_left_as_it_was_is_blank_moves_with_its_code() -> None:
    told = ["a = 1", "", "def f():", "    one()", "", "    two()", "b = 2"]
    now = ["first", "a = 1", "", "def f(x):", "    one(x)", "", "    two(x)", "b = 2"]

    [told_step] = steps_of(followed_whole(story_of(step(CODE, 3, 6)), CODE, told, now))

    assert where_it_stands(told_step) == (LineSpan(first=4, last=7), now[3:7], True)


def test_a_step_the_round_left_alone_keeps_its_code_when_the_step_below_it_is_rewritten() -> None:
    """Three lines put above both, and the second's two lines rewritten: only its blank one is left as it was."""
    told = ["def a():", "    one()", "", "def b():", "    two()", ""]
    now = ["import x", "import y", "import z", "def a():", "    one()", "", "def b(q):", "    two(q)", ""]

    story = followed_whole(story_of(step(CODE, 1, 3), step(CODE, 4, 6)), CODE, told, now)

    assert [where_it_stands(told_step) for told_step in steps_of(story)] == [
        (LineSpan(first=4, last=6), now[3:6], False),
        (LineSpan(first=7, last=9), now[6:9], True),
    ]


def test_lines_two_steps_had_that_a_round_rewrote_together_go_to_the_step_above() -> None:
    """The second step starts where the round's lines end: no line of the take is shown by both."""
    told = ["a", "b", "c", "d"]
    now = ["a", "B", "C", "d"]

    story = followed_whole(story_of(step(CODE, 1, 2), step(CODE, 3, 4)), CODE, told, now)

    assert [where_it_stands(told_step) for told_step in steps_of(story)] == [
        (LineSpan(first=1, last=3), now[:3], True),
        (LineSpan(first=4, last=4), ["d"], True),
    ]


def test_a_step_all_of_whose_lines_a_round_rewrote_together_with_the_step_above_stands_nowhere() -> None:
    """Every line the round put in their place is the step above's: none is left for it."""
    told = ["a", "b", "c", "d", "e"]
    now = ["a", "X", "e"]

    [above, inside] = steps_of(followed_whole(story_of(step(CODE, 1, 2), step(CODE, 3, 3)), CODE, told, now))

    assert where_it_stands(above) == (LineSpan(first=1, last=2), ["a", "X"], True)
    assert (inside.now, inside.lines) == (None, LineSpan(first=3, last=3))


def test_a_step_no_hunk_of_the_diff_between_the_takes_shows_moves_by_the_lines_put_in_above_it() -> None:
    """Git shows three lines around what it changed: two put in at the top, one taken out at the bottom."""
    now = ["put in", "and again", *TWENTY_LINES[:18], TWENTY_LINES[19]]
    above_and_below = changed_file(TWENTY, hunk(1, 1, "++   "), hunk(16, 18, "   - "))

    story = followed(
        story_of(step(TWENTY, 9, 11)),
        [added_whole(TWENTY, TWENTY_LINES)],
        [added_whole(TWENTY, now)],
        [above_and_below],
    )

    assert where_it_stands(steps_of(story)[0]) == (LineSpan(first=11, last=13), TWENTY_LINES[8:11], False)


def test_a_step_of_lines_a_file_lost_stays_on_them_while_the_change_still_takes_them_out() -> None:
    """They are lines of what the change is made against, which no round moves."""
    deleted = changed_file(LETTERS, hunk(1, 0, "--"), status=FileStatus.DELETED)

    [told_step] = steps_of(followed(story_of(step(LETTERS, 1, 2)), [deleted], [deleted], []))

    assert where_it_stands(told_step) == (LineSpan(first=1, last=2), ["-1/", "-2/"], False)


def test_a_step_of_lines_a_file_lost_stands_nowhere_once_the_file_is_back() -> None:
    """Its lines were numbered as the file was before the change; the file is now told as it stands."""
    deleted = changed_file(LETTERS, hunk(1, 0, "--"), status=FileStatus.DELETED)
    back = changed_file(LETTERS, hunk(1, 1, "--++"))

    [told_step] = steps_of(followed(story_of(step(LETTERS, 1, 2)), [deleted], [back], [added_whole(LETTERS, ["x"])]))

    assert told_step.now is None


def test_a_step_of_a_file_the_diff_between_the_takes_shows_no_line_of_stands_nowhere() -> None:
    """Grown too large to read, say: how its lines moved nobody can say."""
    too_large = DiffFile(path=CODE, status=FileStatus.MODIFIED, hunks=[], unshown=Unshown.TOO_LARGE)
    told = [added_whole(CODE, FOUR_LINES)]

    [told_step] = steps_of(followed(story_of(step(CODE, 1, 2)), told, told, [too_large]))

    assert told_step.now is None


@given(steps=steps_of_the_twenty(), now=takes_of_the_twenty())
def test_whatever_a_round_did_the_code_of_each_step_of_a_file_stands_on_lines_of_its_own(
    steps: list[Step], now: list[str]
) -> None:
    """Each runs forwards, and no two share a line: a line of the take is shown by one step at most."""
    story = followed_whole(story_of(*steps), TWENTY, TWENTY_LINES, now)

    standing = sorted((lines for told_step in steps_of(story) for lines in lines_now(told_step)), key=first_of)
    assert all(lines.first <= lines.last for lines in standing)
    assert all(earlier.last < later.first for earlier, later in pairwise(standing))


@given(steps=steps_of_the_twenty(), now=takes_of_the_twenty())
def test_whatever_a_round_did_a_step_is_known_by_the_lines_it_was_told_on(steps: list[Step], now: list[str]) -> None:
    """Whether its code stands elsewhere or nowhere: what the page and a thread on its reason know it by never moves."""
    story = followed_whole(story_of(*steps), TWENTY, TWENTY_LINES, now)

    assert [told_step.lines for told_step in steps_of(story)] == [told.lines for told in steps]


def test_each_chapter_followed_says_how_many_of_its_steps_show_code_a_round_changed() -> None:
    """The fifth line taken out changes the code of the first chapter's step, and leaves the second's as told."""
    story = story_of_chapters(
        chapter_of(EARLIER_CHAPTER, step(TWENTY, 1, 10)), chapter_of(LATER_CHAPTER, step(TWENTY, 11, 20))
    )

    fifth_taken_out = followed_whole(story, TWENTY, TWENTY_LINES, FIFTH_TAKEN_OUT)

    assert [chapter.changed_steps for chapter in fifth_taken_out.chapters] == [1, 0]


def test_a_step_that_stands_nowhere_is_not_counted_among_the_steps_of_its_chapter_a_round_changed() -> None:
    """It shows no code, and so none that changed since it was told."""
    story = followed_whole(story_of(step(TWENTY, 1, 10), step(TWENTY, 11, 20)), TWENTY, TWENTY_LINES, ELEVENTH_ON)

    assert [chapter.changed_steps for chapter in story.chapters] == [0]


def test_a_files_first_step_taken_out_whole_leaves_the_next_step_its_code_on_the_lines_it_moved_up_to() -> None:
    """The step that stands nowhere claims no line: the lines it was told on are the next step's code now."""
    story = followed_whole(story_of(step(TWENTY, 1, 10), step(TWENTY, 11, 20)), TWENTY, TWENTY_LINES, ELEVENTH_ON)

    [taken_out, moved_up] = steps_of(story)
    assert taken_out.now is None
    assert where_it_stands(moved_up) == (LineSpan(first=1, last=10), TWENTY_LINES[10:], False)
