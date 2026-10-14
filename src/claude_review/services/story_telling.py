"""Telling a story of a change: the story as written, placed on the change, or refused with everything wrong.

A story may be told once nothing is wrong with it, by itself or against the
change. Told, each step carries the piece of its file it shows, cut out of
the change by the one rule that says what a step is, and whatever of the
change no step tells is set beside the story — so every line the change
added or removed is in a step, in a file named as housekeeping, or among
what was left out, and a story cannot hide one.

A round's work then moves the code under the story, and the story follows
it onto each take of the change as a thread follows its lines: by what the
lines say, looked for nearest where they were (`find_run`). Each step is cut
again by the same rule, and marked where what it shows is not what it was
told with; what no step tells is worked out again. A story is followed from
the story as it was told, every time, so code put back as it was reads as
told again.
"""

from claude_review.domain.exceptions import StoryRefusedError
from claude_review.domain.models import DiffFile, DiffLine, LineSide, LineSpan
from claude_review.domain.story import Chapter, LeftOut, Step, Story, ToldStep, ToldStory
from claude_review.services.anchor_service import SideLine, find_run, side_lines
from claude_review.services.story_checks import document_faults, placement_faults
from claude_review.services.story_lines_told import first_met
from claude_review.services.story_slices import PlacedFile, side_told_by

# What a story refused is refused with, before its faults are said one by one
STORY_REFUSED = "the story may not be told as it is written"
# How far down a file the line after another stands
NEXT_LINE = 1


def tell(story: Story[Step], files: list[DiffFile]) -> ToldStory:
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
    return story.told(chapters, _left_out(story.chapters, story.housekeeping, files, change))


def follow(told: ToldStory, files: list[DiffFile]) -> ToldStory:
    """A story as it was told, on a later take of the change: each step on its lines as they now stand.

    The steps of one file are followed together, since two of them must not
    come to tell one line, and each is found again by its file and the line
    it was told to start at: no two steps of a file start at one line.
    """
    change = {file.path: PlacedFile(file) for file in files}
    followed = {
        path: _followed_steps(steps, change.get(path)) for path, steps in _steps_of_each_file(told.chapters).items()
    }
    chapters = [
        chapter.told([followed[step.file][step.lines.first] for step in chapter.steps]) for chapter in told.chapters
    ]
    return told.told(chapters, _left_out(chapters, told.housekeeping, files, change))


def _told_chapter(chapter: Chapter[Step], change: dict[str, PlacedFile]) -> Chapter[ToldStep]:
    """A chapter as it is told: everything it says, and each of its steps with what it shows."""
    return chapter.told([_told_step(step, change[step.file]) for step in chapter.steps])


def _told_step(step: Step, file: PlacedFile) -> ToldStep:
    """A step as it is told: everything it says, and the piece of its file it shows."""
    return step.told(file.piece([file.rows_at(step.lines)]), changed_since_told=False)


def _followed_steps(steps: list[ToldStep], file: PlacedFile | None) -> dict[int, ToldStep]:
    """Steps of one file on a later take of it, by the line each was told to start at.

    Each is marked, and shows no rows, where the file left the change.
    """
    if file is None:
        return {step.lines.first: step.told(step.piece.showing([]), changed_since_told=True) for step in steps}
    standing = _where_steps_stand(steps, file.file)
    return {step.lines.first: _cut_again(step, lines, file) for step, lines in zip(steps, standing, strict=True)}


def _where_steps_stand(steps: list[ToldStep], file: DiffFile) -> list[LineSpan]:
    """Where the steps of one file stand in a later take of it, in the order given.

    Each moves as its lines moved. Should two then meet, every one stays on
    the lines it was told of, which never meet: a line is told once, and the
    steps of a file are told apart by where they start.
    """
    lines_now = {side: side_lines(file, side) for side in LineSide}
    moved = [_moved_lines(step, lines_now) for step in steps]
    if any(met is not None for met in first_met(moved)):
        return [step.lines for step in steps]
    return moved


def _moved_lines(step: ToldStep, lines_now: dict[LineSide, list[SideLine]]) -> LineSpan:
    """A step's lines moved as the lines its piece shows moved: on the lines it was told of, unless all are found.

    The lines it shows, on the side its file is told by, are runs that follow
    one another, broken where a hunk ends. Its first line moves as the first
    run moved, and its last as the last; a step whose piece shows no line of
    that side has nothing to look for, and stays.
    """
    side = side_told_by(step.piece)
    runs = _runs(side_lines(step.piece, side))
    moves = [move for run in runs if (move := _how_far_moved(run, lines_now[side])) is not None]
    if not runs or len(moves) != len(runs):
        return step.lines
    return LineSpan(first=step.lines.first + moves[0], last=step.lines.last + moves[-1])


def _runs(lines: list[SideLine]) -> list[list[SideLine]]:
    """Lines of one side, cut into runs of lines that follow one another in the file."""
    runs: list[list[SideLine]] = []
    for line in lines:
        if runs and line.number == runs[-1][-1].number + NEXT_LINE:
            runs[-1].append(line)
        else:
            runs.append([line])
    return runs


def _how_far_moved(run: list[SideLine], lines_now: list[SideLine]) -> int | None:
    """How many lines further down a run now stands, where what it says stands nearest; None where it is gone."""
    [first, *_] = run
    found = find_run(lines_now, [line.content for line in run], near=first.number)
    return None if found is None else lines_now[found].number - first.number


def _cut_again(step: ToldStep, lines: LineSpan, file: PlacedFile) -> ToldStep:
    """A step on the lines it now stands at, cut again, and marked if it shows other rows than it was told with."""
    piece = file.piece([file.rows_at(lines)])
    return step.at(lines).told(piece, changed_since_told=_shows_other_rows(step.piece, piece))


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


def _left_out[StepKind: Step](
    chapters: list[Chapter[StepKind]], housekeeping: list[str], files: list[DiffFile], change: dict[str, PlacedFile]
) -> list[LeftOut]:
    """What the steps leave out, file by file in the order of the change: nothing of a housekeeping file."""
    steps_of_each_file = _steps_of_each_file(chapters)
    named = frozenset(housekeeping)
    return [
        left
        for file in files
        if file.path not in named
        for left in _left_out_of(
            file, change[file.path], [step.lines for step in steps_of_each_file.get(file.path, [])]
        )
    ]


def _steps_of_each_file[StepKind: Step](chapters: list[Chapter[StepKind]]) -> dict[str, list[StepKind]]:
    """The steps of these chapters by the file they tell, each file's in the order the story tells them."""
    steps_of_each_file: dict[str, list[StepKind]] = {}
    for chapter in chapters:
        for step in chapter.steps:
            steps_of_each_file.setdefault(step.file, []).append(step)
    return steps_of_each_file


def _left_out_of(file: DiffFile, placed: PlacedFile, lines_told: list[LineSpan]) -> list[LeftOut]:
    """What steps of these lines leave out of one file, if anything.

    A file the change shows no line of — binary, too large, only moved —
    has no line for a step to tell, and is left out whole, as it is.
    """
    if not placed.shows_lines:
        return [LeftOut(piece=file, changed_lines=0)]
    left = placed.left_out([placed.rows_at(lines) for lines in lines_told])
    return [LeftOut(piece=placed.piece(left), changed_lines=placed.changed_lines(left))] if left else []
