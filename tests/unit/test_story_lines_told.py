"""Functional requirement tests for which earlier step of a file a step meets: the first to have told a line of it.

A line is told once, and a step that tells one again is told which step
told it first — first in the story, wherever in the file the others lie.
Each step is named here by its place among the steps of its file.
"""

from hypothesis import given, strategies as strategy

from claude_review.domain.models import LineSpan
from claude_review.services.story_lines_told import first_met

# A line every step of a generated story tells, and how far a step may reach either side of it
SHARED = 500
FURTHEST_REACH = 400
# How far apart generated steps that share no line may stand, and how long each may be
WIDEST_GAP = 5
LONGEST_STEP = 5
# Steps by their places in a story: the first told, and the second
FIRST, SECOND = 0, 1
MEETS_NONE = None


def lines(first: int, last: int) -> LineSpan:
    return LineSpan(first=first, last=last)


def test_a_file_no_step_tells_has_no_step_to_meet_another() -> None:
    assert first_met([]) == []


def test_steps_that_share_no_line_meet_none() -> None:
    assert first_met([lines(10, 20), lines(30, 40), lines(21, 29)]) == [MEETS_NONE, MEETS_NONE, MEETS_NONE]


def test_a_step_that_tells_one_line_of_an_earlier_step_meets_it() -> None:
    assert first_met([lines(10, 20), lines(20, 30)]) == [MEETS_NONE, FIRST]


def test_a_step_meets_an_earlier_one_that_lies_inside_it() -> None:
    assert first_met([lines(40, 60), lines(1, 100)]) == [MEETS_NONE, FIRST]


def test_a_step_meets_an_earlier_one_it_lies_inside() -> None:
    assert first_met([lines(1, 100), lines(40, 60)]) == [MEETS_NONE, FIRST]


def test_of_two_earlier_steps_a_step_meets_the_one_the_story_told_first() -> None:
    """First in the story, though the other lies above it in the file."""
    assert first_met([lines(50, 60), lines(1, 10), lines(5, 55)]) == [MEETS_NONE, MEETS_NONE, FIRST]


def test_a_step_that_meets_only_a_step_that_itself_met_another_meets_that_one() -> None:
    assert first_met([lines(1, 10), lines(5, 20), lines(15, 18)]) == [MEETS_NONE, FIRST, SECOND]


def test_a_step_lying_across_several_meets_the_first_of_them_and_is_met_between_them() -> None:
    """The lines between two narrow steps were told by nobody but the wide one."""
    across = lines(1, 100)

    assert first_met([lines(10, 12), lines(30, 32), across, lines(20, 22)]) == [MEETS_NONE, MEETS_NONE, FIRST, 2]


def test_the_same_lines_told_again_meet_the_first_telling_every_time() -> None:
    assert first_met([lines(7, 9), lines(7, 9), lines(7, 9)]) == [MEETS_NONE, FIRST, FIRST]


@given(
    reaches=strategy.lists(
        strategy.tuples(
            strategy.integers(min_value=0, max_value=FURTHEST_REACH),
            strategy.integers(min_value=0, max_value=FURTHEST_REACH),
        ),
        min_size=1,
    )
)
def test_however_many_steps_tell_one_line_each_after_the_first_meets_the_first(reaches: list[tuple[int, int]]) -> None:
    steps = [lines(SHARED - above, SHARED + below) for above, below in reaches]

    assert first_met(steps) == [MEETS_NONE, *[FIRST] * (len(steps) - 1)]


@strategy.composite
def steps_that_stand_apart(draw: strategy.DrawFn) -> list[LineSpan]:
    """Steps of one file, each starting past the end of the one above it, in whatever order a story tells them."""
    gaps = draw(strategy.lists(strategy.integers(min_value=1, max_value=WIDEST_GAP), min_size=1))
    lengths = draw(
        strategy.lists(
            strategy.integers(min_value=0, max_value=LONGEST_STEP - 1), min_size=len(gaps), max_size=len(gaps)
        )
    )
    down_the_file: list[LineSpan] = []
    reached = 0
    for gap, length in zip(gaps, lengths, strict=True):
        down_the_file.append(lines(reached + gap, reached + gap + length))
        reached += gap + length
    return draw(strategy.permutations(down_the_file))


@given(steps=steps_that_stand_apart())
def test_however_a_story_orders_steps_that_stand_apart_none_meets_another(steps: list[LineSpan]) -> None:
    assert first_met(steps) == [MEETS_NONE] * len(steps)
