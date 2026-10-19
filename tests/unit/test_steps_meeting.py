"""Functional requirement tests for which steps of a file meet: each that shares a line with another is named one it does.

A line is told once, so a story whose steps share a line is refused at each
of them, and steps that come to share one once followed stand nowhere. Each
step is named here by its place among the steps of its file.
"""

from itertools import chain

from hypothesis import given, strategies as strategy

from claude_review.domain.models import LineSpan
from claude_review.services.story_checks import one_met_by_each

# How far down a file a generated step may start, and how far past its first line it may reach
FURTHEST_START = 400
FURTHEST_REACH = 400
# How far apart generated steps that share no line may stand, and how long each may be
WIDEST_GAP = 5
LONGEST_STEP = 5
MEETS_NONE = None


def lines(first: int, last: int) -> LineSpan:
    return LineSpan(first=first, last=last)


def share_a_line(steps: list[LineSpan], one: int, other: int) -> bool:
    """The rule as it reads: two steps share a line when each starts no later than the other ends."""
    return steps[one].first <= steps[other].last and steps[other].first <= steps[one].last


def meets_another_plainly(steps: list[LineSpan], place: int) -> bool:
    """The step held against every other in turn: whether any of them shares a line with it."""
    others = chain(range(place), range(place + 1, len(steps)))
    return any(share_a_line(steps, place, other) for other in others)


@strategy.composite
def steps_of_one_file(draw: strategy.DrawFn) -> list[LineSpan]:
    """Steps of one file told in any order, lying across one another or apart, of a line or of many."""
    firsts = draw(strategy.lists(strategy.integers(min_value=1, max_value=FURTHEST_START)))
    return [lines(first, first + draw(strategy.integers(min_value=0, max_value=FURTHEST_REACH))) for first in firsts]


@strategy.composite
def steps_each_sharing_a_line(draw: strategy.DrawFn) -> list[LineSpan]:
    """Steps of one file in any order, each told beside a step of its first line alone: none shares no line."""
    steps = draw(steps_of_one_file())
    return draw(strategy.permutations([*steps, *[lines(step.first, step.first) for step in steps]]))


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


@given(steps=steps_of_one_file())
def test_however_the_steps_of_a_file_lie_each_is_named_one_exactly_when_it_shares_a_line_with_another(
    steps: list[LineSpan],
) -> None:
    named = [met is not MEETS_NONE for met in one_met_by_each(steps)]

    assert named == [meets_another_plainly(steps, place) for place in range(len(steps))]


@given(steps=steps_each_sharing_a_line())
def test_the_step_each_is_named_is_another_that_shares_a_line_with_it(steps: list[LineSpan]) -> None:
    met = one_met_by_each(steps)

    assert all(other != place for place, other in enumerate(met))
    assert all(share_a_line(steps, place, other) for place, other in enumerate(met))


@given(steps=steps_that_stand_apart())
def test_however_a_story_orders_steps_that_stand_apart_none_meets_another(steps: list[LineSpan]) -> None:
    assert one_met_by_each(steps) == [MEETS_NONE] * len(steps)


def test_two_steps_that_share_one_line_each_meet_the_other() -> None:
    assert one_met_by_each([lines(10, 20), lines(20, 30)]) == [1, 0]
