"""Telling a story of a change: the story as written, placed on the change, or refused with everything wrong.

A story may be told once nothing is wrong with it, by itself or against the
change. Told, each step carries the piece of its file it shows, cut out of
the change by the one rule that says what a step is, and whatever of the
change no step tells is set beside the story — so every line the change
added or removed is in a step, in a file named as housekeeping, or among
what was left out, and a story cannot hide one.

A round's work then moves the code under the story, and the story follows
it onto each take of the change by what the diff from the take it was told
of to that take says of each of its lines (`_LinesMoved`): a line kept
moves as the lines above it were put in or taken out, and a step's end
among lines the round replaced lands on what stands in their place. So a
step follows its own code whatever its lines say, and a line said another
way stays in the step that told it. Each step is cut again by the same
rule, and marked where what it shows is not what it was told with; what no
step tells is worked out again. A story is followed from the story as it
was told, every time, so code put back as it was reads as told again.
"""

from bisect import bisect_left
from itertools import accumulate, groupby

from pydantic import BaseModel, ConfigDict

from claude_review.domain.exceptions import StoryRefusedError
from claude_review.domain.models import DiffFile, DiffHunk, DiffLine, LineSpan, LineType
from claude_review.domain.story import Chapter, FollowedStep, LeftOut, Step, StepNow, Story, ToldStep, ToldStory
from claude_review.services.story_checks import document_faults, placement_faults, steps_by_file
from claude_review.services.story_slices import PlacedFile, side_told_by

# What a story refused is refused with, before its faults are said one by one
STORY_REFUSED = "the story may not be told as it is written"
# How far down a file the line after another stands
NEXT_LINE = 1
# The line a file's lines come after: none of them is reached yet
NO_LINE_REACHED = 0
# How far a line moves when nothing above it was put in or taken out
NOT_MOVED = 0


class _Landing(BaseModel):
    """Where a line of the take a story was told of stands in a later take: as a step's first line, and as its last.

    The two differ only for a line the rounds replaced, which is no line of
    the later take.
    """

    model_config = ConfigDict(frozen=True)

    as_first: int
    as_last: int


class _LinesMoved:
    """Where the lines of one file in the take a story was told of stand in a later take, as the diff between says.

    A line the rounds kept moves as the lines above it were put in or taken
    out. A line inside a block they replaced is no line of the later take: a
    step's first line inside one lands on the first line put in its place,
    and its last on the last; where the block put none in, on the line after
    it and the line before, so a step all of whose lines went runs
    backwards, and stands nowhere.
    """

    def __init__(self, changed: DiffFile | None) -> None:
        # A file the diff between the takes does not name was not changed between them
        hunks = [] if changed is None else changed.hunks
        # Every line of the told take a hunk shows, with where it lands
        self._landings = {line: landing for hunk in hunks for line, landing in _landings(hunk).items()}
        # Where each hunk ends among the told take's lines, and how far the
        # lines below each moved: by none above the first hunk
        self._hunk_ends = [_told_end(hunk) for hunk in hunks]
        self._moved_below = list(accumulate((_lines_put_in(hunk) for hunk in hunks), initial=NOT_MOVED))

    def carried(self, lines: LineSpan) -> LineSpan:
        """These lines of the told take on the later one: running backwards where nothing of them is left."""
        return LineSpan(first=self._landing(lines.first).as_first, last=self._landing(lines.last).as_last)

    def _landing(self, line: int) -> _Landing:
        """Where one line of the told take lands: by its hunk where one shows it, else moved as the lines above it."""
        shown = self._landings.get(line)
        if shown is not None:
            return shown
        moved_to = line + self._moved_below[bisect_left(self._hunk_ends, line)]
        return _Landing(as_first=moved_to, as_last=moved_to)


def tell(story: Story[Step], files: list[DiffFile]) -> ToldStory[ToldStep]:
    """The story on the change it is told of.

    A told story says everything the story said: each part of it makes its
    own told form from what telling adds, so nothing here names a field of
    a part, and a field a part gains later is told without a word here.

    Raises:
        StoryRefusedError: if anything is wrong with it, carrying all of it.
    """
    change = {file.path: PlacedFile(file) for file in files}
    faults = [*document_faults(story), *placement_faults(story, change)]
    if faults:
        raise StoryRefusedError(STORY_REFUSED, faults)
    chapters = [_told_chapter(chapter, change) for chapter in story.chapters]
    lines_told = {path: [step.lines for step in steps] for path, steps in _steps_of_each_file(story.chapters).items()}
    return story.told(chapters, _left_out(lines_told, story.housekeeping, files, change))


def as_told(told: ToldStory[ToldStep]) -> ToldStory[FollowedStep]:
    """A story as it was told, on the take it was told of: each step where it was told, showing what it was told."""
    chapters = [chapter.followed([_as_told_step(step) for step in chapter.steps]) for chapter in told.chapters]
    return told.followed(chapters, told.left_out)


def follow(
    told: ToldStory[ToldStep], files: list[DiffFile], since_told: list[DiffFile] | None
) -> ToldStory[FollowedStep]:
    """A story as it was told, on a later take of the change: each step where its code now stands, if anywhere.

    `since_told` is what changed from the take the story was told of to this
    one, file by file, as a diff between the two takes says it: None where
    that cannot be said, and then no step can be placed. The steps of one
    file are followed together, since two of them must not come to tell one
    line, and each is put back where the story tells it.
    """
    change = {file.path: PlacedFile(file) for file in files}
    steps = [step for chapter in told.chapters for step in chapter.steps]
    followed = _followed(steps, change, since_told)
    # A step that stands nowhere tells none of the lines it was told of: what stands there now is left out
    lines_told = {
        path: [step.now.lines for step in of_the_file if step.now is not None]
        for path, of_the_file in steps_by_file(followed, lambda step: step.file).items()
    }
    return told.followed(_in_chapters(told.chapters, followed), _left_out(lines_told, told.housekeeping, files, change))


def _told_chapter(chapter: Chapter[Step], change: dict[str, PlacedFile]) -> Chapter[ToldStep]:
    """A chapter as it is told: everything it says, and each of its steps with what it shows."""
    return chapter.told([_told_step(step, change[step.file]) for step in chapter.steps])


def _told_step(step: Step, file: PlacedFile) -> ToldStep:
    """A step as it is told: everything it says, and the piece of its file it shows."""
    return step.told(file.piece([file.rows_at(step.lines)]))


def _followed(
    steps: list[ToldStep], change: dict[str, PlacedFile], since_told: list[DiffFile] | None
) -> list[FollowedStep]:
    """Every step on the later take, in the order given; none placed where what changed since it was told is unknown."""
    if since_told is None:
        return [_not_placed(step) for step in steps]
    changed = {file.path: file for file in since_told}
    places_of_each_file = steps_by_file(list(range(len(steps))), lambda place: steps[place].file)
    followed: dict[int, FollowedStep] = {}
    for path, places in places_of_each_file.items():
        of_the_file = _followed_in_file([steps[place] for place in places], change.get(path), changed.get(path))
        followed.update(zip(places, of_the_file, strict=True))
    return [followed[place] for place in range(len(steps))]


def _followed_in_file(steps: list[ToldStep], file: PlacedFile | None, changed: DiffFile | None) -> list[FollowedStep]:
    """Steps of one file on the later take, in the order given, `changed` being what changed in it since they were told.

    None is placed where the file left the change, or where how its lines
    moved cannot be said: the diff between the takes shows none of them. Nor
    is a step the take tells by the other side than it was told by: the
    numbers of one side say nothing of the other.
    """
    if file is None or (changed is not None and changed.unshown is not None):
        return [_not_placed(step) for step in steps]
    moved = _LinesMoved(changed)
    told_by_now = side_told_by(file.file)
    carried = [moved.carried(step.lines) if side_told_by(step.piece) == told_by_now else None for step in steps]
    standing = _down_the_file(steps, carried)
    return [
        _not_placed(step) if lines is None else _cut_again(step, lines, file)
        for step, lines in zip(steps, standing, strict=True)
    ]


def _down_the_file(steps: list[ToldStep], carried: list[LineSpan | None]) -> list[LineSpan | None]:
    """Where the steps of one file stand, in the order given: their lines carried, read down the file.

    Lines carried keep the order they were told in, and share none, but
    where one block the round replaced held lines of two steps: then the
    block is the step above's, and the step below starts after it. A step
    that has no line left, or none carried, stands nowhere.
    """
    standing: list[LineSpan | None] = [None] * len(steps)
    reached = NO_LINE_REACHED
    for place in sorted(range(len(steps)), key=lambda place: steps[place].lines.first):
        lines = carried[place]
        if lines is None:
            continue
        first = max(lines.first, reached + NEXT_LINE)
        if first <= lines.last:
            standing[place] = LineSpan(first=first, last=lines.last)
            reached = lines.last
    return standing


def _in_chapters(chapters: list[Chapter[ToldStep]], followed: list[FollowedStep]) -> list[Chapter[FollowedStep]]:
    """The chapters, each with its steps followed: `followed` holds every step in the order the story tells them."""
    in_order = iter(followed)
    return [chapter.followed([next(in_order) for _ in chapter.steps]) for chapter in chapters]


def _landings(hunk: DiffHunk) -> dict[int, _Landing]:
    """Where each line of the told take a hunk shows lands in the later take.

    A hunk is blocks of lines kept and blocks of lines replaced, one after
    another; a block replaced lands by what is put in its place, or by the
    last line of the later take above it where nothing is.
    """
    landings: dict[int, _Landing] = {}
    reached = hunk.new_start - NEXT_LINE
    for kept, rows in groupby(hunk.lines, key=_is_kept):
        block = list(rows)
        told = [row.old_number for row in block if row.old_number is not None]
        now = [row.new_number for row in block if row.new_number is not None]
        if kept:
            landings.update({line: _Landing(as_first=to, as_last=to) for line, to in zip(told, now, strict=True)})
        else:
            landings.update(dict.fromkeys(told, _replaced_by(now, reached)))
        reached = max(now, default=reached)
    return landings


def _replaced_by(put_in: list[int], reached: int) -> _Landing:
    """Where lines a round replaced land: on the first and the last line put in, or around where they were."""
    if not put_in:
        return _Landing(as_first=reached + NEXT_LINE, as_last=reached)
    return _Landing(as_first=min(put_in), as_last=max(put_in))


def _is_kept(row: DiffLine) -> bool:
    """Whether a row of a diff is a line both its sides have."""
    return row.kind == LineType.CONTEXT


def _told_end(hunk: DiffHunk) -> int:
    """The last line of the told take a hunk shows; where it puts its lines in, if it shows none."""
    return max((row.old_number for row in hunk.lines if row.old_number is not None), default=hunk.old_start)


def _lines_put_in(hunk: DiffHunk) -> int:
    """How many more lines the later take has than the told one where a hunk is: fewer, where it took lines out."""
    lines_now = sum(row.new_number is not None for row in hunk.lines)
    lines_told = sum(row.old_number is not None for row in hunk.lines)
    return lines_now - lines_told


def _as_told_step(step: ToldStep) -> FollowedStep:
    """A step on the take it was told of: on the lines it was told on, showing what it was told with."""
    return step.followed(StepNow(lines=step.lines, piece=step.piece, changed_since_told=False))


def _not_placed(step: ToldStep) -> FollowedStep:
    """A step whose code the review cannot place in the change now: standing nowhere, and claiming no line."""
    return step.followed(None)


def _cut_again(step: ToldStep, lines: LineSpan, file: PlacedFile) -> FollowedStep:
    """A step on the lines it now stands at, cut again, and marked if it shows other rows than it was told with."""
    piece = file.piece([file.rows_at(lines)])
    return step.followed(StepNow(lines=lines, piece=piece, changed_since_told=_shows_other_rows(step.piece, piece)))


def _shows_other_rows(told: DiffFile, now: DiffFile) -> bool:
    """Whether a piece shows other rows than the piece told: what each row is and says, wherever it stands."""
    rows_told, rows_now = _rows_of(told), _rows_of(now)
    return len(rows_told) != len(rows_now) or any(
        was.kind != is_now.kind or was.content != is_now.content
        for was, is_now in zip(rows_told, rows_now, strict=True)
    )


def _rows_of(piece: DiffFile) -> list[DiffLine]:
    """Every row a piece shows, hunk after hunk."""
    return [line for hunk in piece.hunks for line in hunk.lines]


def _left_out(
    lines_told: dict[str, list[LineSpan]], housekeeping: list[str], files: list[DiffFile], change: dict[str, PlacedFile]
) -> list[LeftOut]:
    """What steps of these lines, by file, leave out, file by file in the order of the change: none of housekeeping."""
    named = frozenset(housekeeping)
    return [
        left
        for file in files
        if file.path not in named
        for left in _left_out_of(file, change[file.path], lines_told.get(file.path, []))
    ]


def _steps_of_each_file[StepKind: Step](chapters: list[Chapter[StepKind]]) -> dict[str, list[StepKind]]:
    """The steps of these chapters by the file each tells, each file's in the order the story tells them."""
    return steps_by_file([step for chapter in chapters for step in chapter.steps], lambda step: step.file)


def _left_out_of(file: DiffFile, placed: PlacedFile, lines_told: list[LineSpan]) -> list[LeftOut]:
    """What steps of these lines leave out of one file, if anything.

    A file the change shows no line of — binary, too large, only moved —
    has no line for a step to tell, and is left out whole, as it is.
    """
    if not placed.shows_lines:
        return [LeftOut(piece=file, changed_lines=0)]
    left = placed.left_out([placed.rows_at(lines) for lines in lines_told])
    return [LeftOut(piece=placed.piece(left), changed_lines=placed.changed_lines(left))] if left else []
