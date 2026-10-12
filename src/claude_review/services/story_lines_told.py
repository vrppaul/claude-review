"""Which step of a story first told each line of a file: what a step is held against, to be told once.

A line is told once. A step that tells a line an earlier step of its file
told already is refused, and told which step that was: the first to tell
it, in the order the story tells its steps. Held against every earlier step
in turn, a story as long as a request may carry took minutes to check when
one of its steps lay across the rest.

So the lines are kept, not the steps. Two steps that share a line share
the first line of whichever starts further down the file, so only the
lines some step starts at need keeping — every step's, which is why the
steps of a file are asked and told together, in one place (`first_met`).
In the order of the file, the lines a step tells are then a run of those
kept. The runs are kept as a tree, each halved into two until it is a
single line, and a run is told, or asked who told any of it first,
through the few whole runs that make it up rather than line by line.
"""

import sys
from bisect import bisect_left, bisect_right

from claude_review.domain.models import LineSpan

# Where the lines kept are counted from
FIRST_KEPT = 0
# A run that is a single line, which is halved no further, and how many runs a longer one is halved into
ONE_LINE = 1
HALVES = 2
# The place in a story of the step that told a line no step has told: later than any step a story has
NOBODY = sys.maxsize


class RunOfLines:
    """A run of the lines kept, with the two runs it is halved into under it, down to single lines.

    A step is known by its place in the story, so the earlier of two steps
    is the lesser of two places.
    """

    def __init__(self, start: int, stop: int) -> None:
        self._start = start
        # One past the last line of the run
        self._stop = stop
        # The first step to tell every line of the run, and the first to tell any line of it
        self._told_all = NOBODY
        self._told_any = NOBODY
        self._halves = _halves_of(start, stop)

    def tell(self, start: int, stop: int, step: int) -> None:
        """Note that a step tells the lines from `start` up to `stop`: those of them this run holds."""
        if self._holds_none_of(start, stop):
            return
        self._told_any = min(self._told_any, step)
        if self._lies_within(start, stop):
            self._told_all = min(self._told_all, step)
            return
        for half in self._halves:
            half.tell(start, stop, step)

    def first_to_tell(self, start: int, stop: int) -> int:
        """The first step to tell any line from `start` up to `stop` that this run holds: `NOBODY` if none has.

        Whoever told all of this run told those lines too, and is nowhere
        noted in the runs under it: so it is asked here, on the way down.
        """
        if self._holds_none_of(start, stop):
            return NOBODY
        if self._lies_within(start, stop):
            return self._told_any
        return min(self._told_all, *(half.first_to_tell(start, stop) for half in self._halves))

    def _holds_none_of(self, start: int, stop: int) -> bool:
        return stop <= self._start or self._stop <= start

    def _lies_within(self, start: int, stop: int) -> bool:
        return start <= self._start and self._stop <= stop


def first_met(steps: list[LineSpan]) -> list[int | None]:
    """For each step of one file, in the order a story tells them, the first earlier step that tells a line of it.

    A step is named by its place among those given; None stands for a step
    that meets none before it. Each step is asked of the lines kept, then
    tells its own: what it is asked of is what the steps before it told.
    """
    starts = sorted({lines.first for lines in steps})
    kept = RunOfLines(FIRST_KEPT, len(starts))
    met: list[int | None] = []
    for place, lines in enumerate(steps):
        # Where, among the lines kept, the step's first line stands, and one past where its last would
        start = bisect_left(starts, lines.first)
        stop = bisect_right(starts, lines.last)
        earliest = kept.first_to_tell(start, stop)
        met.append(None if earliest == NOBODY else earliest)
        kept.tell(start, stop, place)
    return met


def _halves_of(start: int, stop: int) -> list[RunOfLines]:
    """The two runs a run is halved into, or none for a single line."""
    if stop - start <= ONE_LINE:
        return []
    middle = (start + stop) // HALVES
    return [RunOfLines(start, middle), RunOfLines(middle, stop)]
