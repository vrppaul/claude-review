"""Which earlier step of a file a step meets: the first to have told a line of it.

A line is told once. A step that tells a line an earlier step of its file
told already is refused, and told which step that was: the first to tell
it, in the order the story tells its steps. Held against every earlier step
in turn, a story as long as a request may carry took about a minute to
check when one of its steps lay across the rest.

So the lines are kept, not the steps. Two steps that share a line share
the first line of whichever starts further down the file, so only the
lines some step starts at need keeping — every step's, which is why the
steps of a file are asked and told together, in one place (`first_met`).
In the order of the file, the lines a step tells are then a run of those
kept. What was told of them is kept as a tree of runs, each halved into
two until it is a single line — a segment tree, to whoever knows it by
that name — and a run is told, or asked who told any of it first, through
the few whole runs that make it up rather than line by line: a file of n
steps is checked in about n times the logarithm of n.
"""

import sys
from bisect import bisect_left, bisect_right

from pydantic import BaseModel, ConfigDict

from claude_review.domain.models import LineSpan

# Where the lines kept are counted from
FIRST_KEPT = 0
# A run that is a single line, which is halved no further
ONE_LINE = 1
# What a run's length is divided by to find where it is halved
IN_HALF = 2
# The place in a story of the step that told a line no step has told: later than any step a story has
NOBODY = sys.maxsize


class RunKept(BaseModel):
    """A run of the lines kept, by their places among them: from which, up to which."""

    model_config = ConfigDict(frozen=True)

    start: int
    # One past the last line of the run
    stop: int

    def holds_none_of(self, other: RunKept) -> bool:
        """Whether no line kept is in both runs."""
        return other.stop <= self.start or self.stop <= other.start

    def lies_within(self, other: RunKept) -> bool:
        """Whether every line of this run is a line of the other."""
        return other.start <= self.start and self.stop <= other.stop


class ToldOfRun:
    """What has been told of one run of the lines kept, and of the two runs it is halved into under it.

    A step is known by its place in the story, so the earlier of two steps
    is the lesser of two places.
    """

    def __init__(self, run: RunKept) -> None:
        self._run = run
        # Of the steps noted at this run or under it: the first to tell all
        # of the run, and the first to tell any of it. A step that told the
        # whole of a run above this one is noted there, and not here
        self._all_told_by = NOBODY
        self._any_told_by = NOBODY
        self._halves = _halves_of(run)

    def tell(self, told: RunKept, place: int) -> None:
        """Note that the step at this place in the story tells these lines: those of them this run holds."""
        if self._run.holds_none_of(told):
            return
        self._any_told_by = min(self._any_told_by, place)
        if self._run.lies_within(told):
            self._all_told_by = min(self._all_told_by, place)
            return
        for half in self._halves:
            half.tell(told, place)

    def first_to_tell(self, asked: RunKept) -> int:
        """The place of the first step to tell any of these lines that this run holds: `NOBODY` if none has.

        Whoever told all of this run told those lines too, and is noted
        nowhere under it: so it is asked here, on the way down.
        """
        if self._run.holds_none_of(asked):
            return NOBODY
        if self._run.lies_within(asked):
            return self._any_told_by
        return min(self._all_told_by, *(half.first_to_tell(asked) for half in self._halves))


def first_met(steps: list[LineSpan]) -> list[int | None]:
    """For each step of one file, in the order a story tells them, the first earlier step that tells a line of it.

    A step is named by its place among those given; None stands for a step
    that meets none before it. Each step is asked of the lines kept, then
    tells its own: what it is asked of is what the steps before it told.
    The steps are of lines a file could have: none runs backwards.
    """
    starts = sorted({lines.first for lines in steps})
    told = ToldOfRun(RunKept(start=FIRST_KEPT, stop=len(starts)))
    met: list[int | None] = []
    for place, lines in enumerate(steps):
        # Among the lines kept: where the step's first line stands, up to one past where its last would
        run = RunKept(start=bisect_left(starts, lines.first), stop=bisect_right(starts, lines.last))
        earliest = told.first_to_tell(run)
        met.append(None if earliest == NOBODY else earliest)
        told.tell(run, place)
    return met


def _halves_of(run: RunKept) -> list[ToldOfRun]:
    """What is told of the two runs a run is halved into; of a single line, nothing more."""
    if run.stop - run.start <= ONE_LINE:
        return []
    middle = run.start + (run.stop - run.start) // IN_HALF
    return [ToldOfRun(RunKept(start=run.start, stop=middle)), ToldOfRun(RunKept(start=middle, stop=run.stop))]
