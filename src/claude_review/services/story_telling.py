"""Telling a story of a change: the story as written, placed on the change, or refused with everything wrong.

A story may be told once nothing is wrong with it, by itself or against the
change. Told, each step carries the piece of its file it shows, cut out of
the change by the one rule that says what a step is, and whatever of the
change no step tells is set beside the story — so every line the change
added or removed is in a step, in a file named as housekeeping, or among
what was left out, and a story cannot hide one.

A round's work then moves the code under the story, and the story follows
it onto each take of the change as a thread follows its lines: by what the
lines say, looked for nearest where they were (`find_run`), and where the
round rewrote some of them, by what is left of them. Each step is cut
again by the same rule, and marked where what it shows is not what it was
told with; what no step tells is worked out again. A story is followed from
the story as it was told, every time, so code put back as it was reads as
told again.
"""

from typing import Self

from pydantic import BaseModel, ConfigDict

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


class _SideNow(BaseModel):
    """One side of a file as a later take shows it: its lines in order, and every text any of them says.

    Lines a side says nowhere are not looked for in it: a round that rewrote
    a long step whole would otherwise have each of its lines looked for
    alone through the whole file, which took seconds.
    """

    model_config = ConfigDict(frozen=True)

    lines: list[SideLine]
    said: frozenset[str]

    @classmethod
    def of(cls, lines: list[SideLine]) -> Self:
        """The side these lines make up, in order."""
        return cls(lines=lines, said=frozenset(line.content for line in lines))

    def says_all_of(self, lines: list[SideLine]) -> bool:
        """Whether each of these lines says what some line of this side says."""
        return all(line.content in self.said for line in lines)


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
    return story.told(chapters, _left_out(_steps_of(story.chapters), story.housekeeping, files, change))


def follow(told: ToldStory, files: list[DiffFile]) -> ToldStory:
    """A story as it was told, on a later take of the change: each step on its lines as they now stand.

    The steps of one file are followed together, since two of them must not
    come to tell one line, and each is found again by its file and the line
    it was told to start at: no two steps of a file start at one line.
    """
    change = {file.path: PlacedFile(file) for file in files}
    followed = {
        path: _followed_steps(steps, change.get(path))
        for path, steps in _steps_of_each_file(_steps_of(told.chapters)).items()
    }
    chapters = [
        chapter.told([followed[step.file][step.lines.first] for step in chapter.steps]) for chapter in told.chapters
    ]
    # A step that shows no code tells none of the lines it was told of: what stands there now is left out
    showing_code = [told_step for told_step in _steps_of(chapters) if told_step.piece is not None]
    return told.told(chapters, _left_out(showing_code, told.housekeeping, files, change))


def _told_chapter(chapter: Chapter[Step], change: dict[str, PlacedFile]) -> Chapter[ToldStep]:
    """A chapter as it is told: everything it says, and each of its steps with what it shows."""
    return chapter.told([_told_step(step, change[step.file]) for step in chapter.steps])


def _told_step(step: Step, file: PlacedFile) -> ToldStep:
    """A step as it is told: everything it says, and the piece of its file it shows."""
    return step.told(file.piece([file.rows_at(step.lines)]), changed_since_told=False)


def _followed_steps(steps: list[ToldStep], file: PlacedFile | None) -> dict[int, ToldStep]:
    """Steps of one file on a later take of it, by the line each was told to start at.

    None of them is placed where the file left the change.
    """
    if file is None:
        return {step.lines.first: _not_placed(step) for step in steps}
    standing = _where_steps_stand(steps, file.file)
    return {
        step.lines.first: _not_placed(step) if lines is None else _cut_again(step, lines, file)
        for step, lines in zip(steps, standing, strict=True)
    }


def _not_placed(step: ToldStep) -> ToldStep:
    """A step whose code the review cannot place in the change now: on its lines as told, with no piece, marked."""
    return step.told(None, changed_since_told=True)


def _where_steps_stand(steps: list[ToldStep], file: DiffFile) -> list[LineSpan | None]:
    """Where the steps of one file stand in a later take of it, in the order given; None for one not placed.

    Each moves as what is left of its lines moved, and one nothing of which
    is found is not placed. Should two then meet — one not placed counted on
    the lines it was told of, where it stays — none is: which lines are
    whose nobody can say, and the lines told never meet, so the steps of a
    file are still told apart by where they start.
    """
    sides_now = {side: _SideNow.of(side_lines(file, side)) for side in LineSide}
    moved = [_moved_lines(step, sides_now) for step in steps]
    standing = [step.lines if lines is None else lines for step, lines in zip(steps, moved, strict=True)]
    if any(met is not None for met in first_met(standing)):
        return [None] * len(steps)
    return moved


def _moved_lines(step: ToldStep, sides_now: dict[LineSide, _SideNow]) -> LineSpan | None:
    """A step's lines moved as what is left of the lines its piece shows moved; None where nothing of them is found.

    The lines it shows, on the side its file is told by, are runs that follow
    one another, broken where a hunk ends. Its first line moves as the first
    run found moved, and its last as the last. A step whose piece shows no
    line of that side — a file the change shows no line of — has nothing to
    look for, and stays; one that shows no piece has nothing either, and is
    found nowhere.
    """
    piece = step.piece
    if piece is None:
        return None
    side = side_told_by(piece)
    runs = _runs(side_lines(piece, side))
    if not runs:
        return step.lines
    moves = [move for run in runs if (move := _how_far_moved(run, sides_now[side])) is not None]
    if not moves:
        return None
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


def _how_far_moved(run: list[SideLine], side_now: _SideNow) -> int | None:
    """How many lines further down a run now stands; None where no line of it is said as it was.

    Where it stands whole, nearest where it was, it moved as that place
    says. Where a round rewrote some of it, it moved as the first of its
    lines still said as it was moved, each looked for alone nearest where it
    stood: what is left of the run is where it now is.
    """
    whole = _how_far_found(run, side_now)
    if whole is not None:
        return whole
    return next((moved for line in run if (moved := _how_far_found([line], side_now)) is not None), None)


def _how_far_found(lines: list[SideLine], side_now: _SideNow) -> int | None:
    """How many lines further down these lines stand together, where what they say stands nearest; None if nowhere."""
    if not side_now.says_all_of(lines):
        return None
    [first, *_] = lines
    found = find_run(side_now.lines, [line.content for line in lines], near=first.number)
    return None if found is None else side_now.lines[found].number - first.number


def _cut_again(step: ToldStep, lines: LineSpan, file: PlacedFile) -> ToldStep:
    """A step on the lines it now stands at, cut again, and marked if it shows other rows than it was told with."""
    piece = file.piece([file.rows_at(lines)])
    return step.at(lines).told(piece, changed_since_told=_shows_other_rows(step.piece, piece))


def _shows_other_rows(told: DiffFile | None, now: DiffFile) -> bool:
    """Whether a piece shows other rows than the piece told: what each row is and says, wherever it stands."""
    rows_told, rows_now = _rows_of(told), _rows_of(now)
    return len(rows_told) != len(rows_now) or any(
        was.kind != is_now.kind or was.content != is_now.content
        for was, is_now in zip(rows_told, rows_now, strict=True)
    )


def _rows_of(piece: DiffFile | None) -> list[DiffLine]:
    """Every row a piece shows, hunk after hunk: none where there is no piece."""
    return [] if piece is None else [line for hunk in piece.hunks for line in hunk.lines]


def _left_out[StepKind: Step](
    steps: list[StepKind], housekeeping: list[str], files: list[DiffFile], change: dict[str, PlacedFile]
) -> list[LeftOut]:
    """What these steps leave out, file by file in the order of the change: nothing of a housekeeping file."""
    steps_of_each_file = _steps_of_each_file(steps)
    named = frozenset(housekeeping)
    return [
        left
        for file in files
        if file.path not in named
        for left in _left_out_of(
            file, change[file.path], [step.lines for step in steps_of_each_file.get(file.path, [])]
        )
    ]


def _steps_of[StepKind: Step](chapters: list[Chapter[StepKind]]) -> list[StepKind]:
    """Every step of these chapters, in the order the story tells them."""
    return [step for chapter in chapters for step in chapter.steps]


def _steps_of_each_file[StepKind: Step](steps: list[StepKind]) -> dict[str, list[StepKind]]:
    """These steps by the file they tell, each file's in the order given."""
    steps_of_each_file: dict[str, list[StepKind]] = {}
    for step in steps:
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
