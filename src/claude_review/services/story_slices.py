"""A step as rows of the change: the one rule for which rows a step's lines are.

A story speaks of lines; the change is rows — lines kept, added and
removed. Every row has a place on the side its file is told by: the number
it has there, or, for a row with none — a line removed from a file told as
it now stands — the number of the next row of its hunk that has one, since
that is where it was removed from; past the last such row of the hunk, the
number of the one before. A step is every row whose place is among its
lines, so removed lines come with the place they were removed from.

A file's rows stand in the order of its lines, hunk after hunk, so places
never go down from one row to the next: the rows of a step stand together,
and are found without reading the rest; what no step tells is the runs of
rows between.

Checking a step, showing it, and saying what no step tells all read the
rows through this one rule, so they cannot disagree about what a step is.
"""

from bisect import bisect_left, bisect_right
from itertools import accumulate, pairwise

from pydantic import BaseModel, ConfigDict

from claude_review.domain.models import NO_HUNK_HEADER, DiffFile, DiffHunk, DiffLine, LineSide, LineSpan, LineType

# Where a file's rows are counted from
FIRST_ROW = 0


class PlacedRow(BaseModel):
    """A row of a file as a story reads it: where it is told, and where a hunk that began with it would start."""

    model_config = ConfigDict(frozen=True)

    line: DiffLine
    # Its place on the side the file is told by
    place: int
    # The number it has on each side, or the one the next line there would
    # have: what a hunk cut from this row on starts at
    old_start: int
    new_start: int


class RowRun(BaseModel):
    """A run of a file's rows, its hunks read one after another: from which row up to which."""

    model_config = ConfigDict(frozen=True)

    start: int
    # One past the last row of the run
    stop: int


class SideOfHunk(BaseModel):
    """One side of a hunk: the number each row has there, where it has one, and the line the side starts at."""

    model_config = ConfigDict(frozen=True)

    numbers: list[int | None]
    start: int

    def places(self) -> list[int]:
        """Each row's place on this side.

        Its own number; for a row with none, the number of the next row that
        has one; past the last such row, that row's number. A hunk that
        shows no line of the side is told where the side starts: at the line
        that follows whatever the hunk removed.
        """
        last_numbered = next((number for number in reversed(self.numbers) if number is not None), self.start)
        return _numbers_ahead(self.numbers, past_the_last=last_numbered)

    def starts(self) -> list[int]:
        """Where a hunk that began with each row would start on this side.

        At the row's own number, or at the number of the next row that has
        one; past the last such row, at the line after it, where the side's
        next line would be.
        """
        lines_shown = sum(1 for number in self.numbers if number is not None)
        return _numbers_ahead(self.numbers, past_the_last=self.start + lines_shown)


class PlacedFile:
    """One file of the change as a story reads it: every row with its place, worked out once for all its steps."""

    def __init__(self, file: DiffFile) -> None:
        self._file = file
        told_by = _side_told_by(file)
        self._rows = [row for hunk in file.hunks for row in _placed_rows(hunk, told_by)]
        # Where each hunk ends among the file's rows: one past its last row
        self._hunk_ends = list(accumulate(len(hunk.lines) for hunk in file.hunks))
        # How many of the rows above each row the change added or removed,
        # and last, how many of them all
        self._changes_above = list(accumulate((_changes_in(row) for row in self._rows), initial=0))

    @property
    def shows_lines(self) -> bool:
        """Whether the change shows any line of the file.

        Of one that is binary, too large or only moved, it shows none.
        """
        return bool(self._rows)

    def rows_at(self, lines: LineSpan) -> RowRun:
        """The rows a step of these lines is: every row whose place is among them, which stand together.

        Lines the change shows no row at — and lines that run backwards, which
        hold none — are a run of no rows.
        """
        start = bisect_left(self._rows, lines.first, key=lambda row: row.place)
        stop = bisect_right(self._rows, lines.last, lo=start, key=lambda row: row.place)
        return RowRun(start=start, stop=stop)

    def left_out(self, told: list[RowRun]) -> list[RowRun]:
        """The rows no step tells, as the runs of them that hold a change.

        What lies between and around the runs that are told, cut where one
        hunk ends and the next begins. A run of lines the change only kept
        is nobody's: it is context, shown beside a change or not at all.
        """
        # A run of no rows stands before a run that starts where it does, so
        # each gap ends where the next run starts, whatever order they came in
        down_the_file = sorted(told, key=lambda run: (run.start, run.stop))
        gap_starts = [FIRST_ROW, *(run.stop for run in down_the_file)]
        gap_stops = [*(run.start for run in down_the_file), len(self._rows)]
        gaps = (RowRun(start=start, stop=stop) for start, stop in zip(gap_starts, gap_stops, strict=True))
        return [part for gap in gaps for part in self._hunk_by_hunk(gap) if self.changed_lines([part]) > 0]

    def changed_lines(self, runs: list[RowRun]) -> int:
        """How many rows of these runs the change added or removed."""
        return sum(self._changes_above[run.stop] - self._changes_above[run.start] for run in runs)

    def piece(self, runs: list[RowRun]) -> DiffFile:
        """These runs cut out of the file, each a hunk of its own, or one for each hunk it runs through.

        A piece of the file, to be shown as a file is: it is the file in
        everything but the rows it shows, so whatever is said of the file —
        where it was, that its mode changed, that some of it is not shown —
        is said of every piece of it, and a story cannot leave it unsaid.
        """
        cut = [self._cut(part) for run in runs for part in self._hunk_by_hunk(run)]
        return self._file.showing(cut)

    def _hunk_by_hunk(self, run: RowRun) -> list[RowRun]:
        """The run cut where one hunk ends and the next begins: of each hunk it holds rows of, a run of those rows."""
        ends_inside = self._hunk_ends[bisect_right(self._hunk_ends, run.start) : bisect_left(self._hunk_ends, run.stop)]
        cuts = [run.start, *ends_inside, run.stop]
        return [RowRun(start=start, stop=stop) for start, stop in pairwise(cuts) if start < stop]

    def _cut(self, run: RowRun) -> DiffHunk:
        """A run of one hunk's rows as a hunk of its own, starting on each side where its first row says it would.

        Git's header says where the whole hunk is and what it holds, which is
        true of no part of it: a piece has none.
        """
        first = self._rows[run.start]
        return DiffHunk(
            header=NO_HUNK_HEADER,
            old_start=first.old_start,
            new_start=first.new_start,
            lines=[row.line for row in self._rows[run.start : run.stop]],
        )


def _side_told_by(file: DiffFile) -> LineSide:
    """The side whose numbers a file is told by.

    A file is told as it now stands, by the numbers of its new side. One the
    change left no line of — deleted, or emptied — has only the lines it had,
    and is told by those: every row of it is a removed line, with a number
    on the old side.
    """
    still_has_lines = any(line.new_number is not None for hunk in file.hunks for line in hunk.lines)
    return LineSide.NEW if still_has_lines else LineSide.OLD


def _placed_rows(hunk: DiffHunk, told_by: LineSide) -> list[PlacedRow]:
    """Every row of a hunk with its place on the side its file is told by, and where a hunk begun with it starts."""
    sides = {
        LineSide.OLD: SideOfHunk(numbers=[line.old_number for line in hunk.lines], start=hunk.old_start),
        LineSide.NEW: SideOfHunk(numbers=[line.new_number for line in hunk.lines], start=hunk.new_start),
    }
    return [
        PlacedRow(line=line, place=place, old_start=old_start, new_start=new_start)
        for line, place, old_start, new_start in zip(
            hunk.lines,
            sides[told_by].places(),
            sides[LineSide.OLD].starts(),
            sides[LineSide.NEW].starts(),
            strict=True,
        )
    ]


def _numbers_ahead(numbers: list[int | None], *, past_the_last: int) -> list[int]:
    """For each row its own number, or the number of the next row that has one: `past_the_last` where none has."""
    ahead: list[int] = []
    following = past_the_last
    for number in reversed(numbers):
        following = following if number is None else number
        ahead.append(following)
    ahead.reverse()
    return ahead


def _changes_in(row: PlacedRow) -> int:
    """How many lines the change added or removed in a row: one, unless it only kept the line."""
    return int(row.line.kind != LineType.CONTEXT)
