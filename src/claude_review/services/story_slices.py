"""A step as rows of the change: the one rule for which rows a step's lines are.

A story speaks of lines; the change is rows — lines kept, added and
removed. Every row has a place on the side its file is told by: the number
it has there, or, for a row with none — a line removed from a file told as
it now stands — the number of the next row that has one, since that is
where it was removed from; past the last such row, the number of the one
before. A step is every row whose place is among its lines, so removed
lines come with the place they were removed from.

Checking a step, showing it, and saying what no step tells all read the
rows through this one rule, so they cannot disagree about what a step is.
"""

from itertools import batched, islice

from pydantic import BaseModel, ConfigDict

from claude_review.domain.models import NO_HUNK_HEADER, DiffFile, DiffHunk, DiffLine, LineType
from claude_review.domain.story import StepLines


class PlacedRow(BaseModel):
    """A row of a file, with its place on the side the file is told by."""

    model_config = ConfigDict(frozen=True)

    line: DiffLine
    place: int


class HunkRows(BaseModel):
    """A run of rows of one hunk: which of its file's hunks, and from which of its rows up to which."""

    model_config = ConfigDict(frozen=True)

    hunk: int
    start: int
    # One past the last row of the run
    stop: int


class ToldFile:
    """One file of the change as a story reads it: every row with its place, worked out once for all its steps."""

    def __init__(self, file: DiffFile) -> None:
        self._file = file
        self._hunks = _placed_rows(file)

    @property
    def shows_lines(self) -> bool:
        """Whether the change shows any line of the file.

        Of one that is binary, too large or only moved, it shows none.
        """
        return bool(self._hunks)

    def rows_at(self, lines: StepLines) -> list[HunkRows]:
        """The rows a step of these lines is: in each hunk that has any, the run of rows whose places are among them.

        Places never go down from one row to the next, so the rows of a hunk
        that are among the lines stand together.
        """
        runs: list[HunkRows] = []
        for index, rows in enumerate(self._hunks):
            among = [position for position, row in enumerate(rows) if lines.holds(row.place)]
            if among:
                runs.append(HunkRows(hunk=index, start=among[0], stop=among[-1] + 1))
        return runs

    def left_out(self, told: list[HunkRows]) -> list[HunkRows]:
        """The rows no step tells, as the runs of them that hold a change.

        What lies between and around the runs that are told, hunk by hunk. A
        run of lines the change only kept is nobody's: it is context, shown
        beside a change or not at all.
        """
        left: list[HunkRows] = []
        for index, rows in enumerate(self._hunks):
            taken = sorted((run for run in told if run.hunk == index), key=lambda run: run.start)
            edges = [0, *(edge for run in taken for edge in (run.start, run.stop)), len(rows)]
            between = [HunkRows(hunk=index, start=start, stop=stop) for start, stop in batched(edges, 2, strict=True)]
            left.extend(run for run in between if self.changed_lines([run]) > 0)
        return left

    def changed_lines(self, runs: list[HunkRows]) -> int:
        """How many rows of these runs the change added or removed."""
        return sum(1 for run in runs for row in self._rows_of(run) if row.line.kind != LineType.CONTEXT)

    def piece(self, runs: list[HunkRows]) -> DiffFile:
        """These runs cut out of the file, each a hunk of its own: a piece of the file, to be shown as a file is."""
        return DiffFile(
            path=self._file.path,
            old_path=self._file.old_path,
            status=self._file.status,
            hunks=[self._cut(run) for run in runs],
        )

    def _rows_of(self, run: HunkRows) -> list[PlacedRow]:
        return self._hunks[run.hunk][run.start : run.stop]

    def _cut(self, run: HunkRows) -> DiffHunk:
        """A run of a hunk's rows as a hunk: it starts, on each side, as many lines on as that side has rows above it.

        Git's header says where the whole hunk is and what it holds, which is
        true of no part of it: a piece has none.
        """
        hunk = self._file.hunks[run.hunk]
        above = hunk.lines[: run.start]
        return DiffHunk(
            header=NO_HUNK_HEADER,
            old_start=hunk.old_start + sum(1 for line in above if line.kind != LineType.ADD),
            new_start=hunk.new_start + sum(1 for line in above if line.kind != LineType.DELETE),
            lines=hunk.lines[run.start : run.stop],
        )


def _placed_rows(file: DiffFile) -> list[list[PlacedRow]]:
    """Every row of the file with its place, hunk by hunk."""
    lines = [line for hunk in file.hunks for line in hunk.lines]
    placed = (PlacedRow(line=line, place=place) for line, place in zip(lines, _places(lines), strict=True))
    return [list(islice(placed, len(hunk.lines))) for hunk in file.hunks]


def _places(lines: list[DiffLine]) -> list[int]:
    """Each row's place on the side the file is told by.

    Its own number there; for a row with none, the number of the next row
    that has one; past the last such row, that row's number.
    """
    numbers = _numbers_told_by(lines)
    numbered = [number for number in numbers if number is not None]
    if not numbered:
        return []
    places: list[int] = []
    following = numbered[-1]
    for number in reversed(numbers):
        following = number if number is not None else following
        places.append(following)
    places.reverse()
    return places


def _numbers_told_by(lines: list[DiffLine]) -> list[int | None]:
    """Each row's number on the side the file is told by, where it has one.

    A file is told as it now stands, by the numbers of its new side. One the
    change left no line of — deleted, or emptied — has only the lines it had,
    and is told by those: every row of it is a removed line, with a number
    on the old side.
    """
    as_it_stands = [line.new_number for line in lines]
    if any(number is not None for number in as_it_stands):
        return as_it_stands
    return [line.old_number for line in lines]
