"""Telling a story of a change: the story as written, placed on the change, or refused with everything wrong.

A story may be told once nothing is wrong with it, by itself or against the
change. Told, each step carries the piece of its file it shows, cut out of
the change by the one rule that says what a step is, and whatever of the
change no step tells is set beside the story — so every line the change
added or removed is in a step, in a file named as housekeeping, or among
what was left out, and a story cannot hide one.
"""

from claude_review.domain.exceptions import StoryRefusedError
from claude_review.domain.models import DiffFile, LineSpan
from claude_review.domain.story import Chapter, LeftOut, Step, Story, ToldStep, ToldStory
from claude_review.services.story_checks import document_faults, placement_faults
from claude_review.services.story_slices import PlacedFile

# What a story refused is refused with, before its faults are said one by one
STORY_REFUSED = "the story may not be told as it is written"


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
    return story.told(chapters, _left_out(story, files, change))


def _told_chapter(chapter: Chapter[Step], change: dict[str, PlacedFile]) -> Chapter[ToldStep]:
    """A chapter as it is told: everything it says, and each of its steps with what it shows."""
    return chapter.told([_told_step(step, change[step.file]) for step in chapter.steps])


def _told_step(step: Step, file: PlacedFile) -> ToldStep:
    """A step as it is told: everything it says, and the piece of its file it shows."""
    return step.told(file.piece([file.rows_at(step.lines)]))


def _left_out(story: Story[Step], files: list[DiffFile], change: dict[str, PlacedFile]) -> list[LeftOut]:
    """What the story leaves out, file by file in the order of the change: nothing of a housekeeping file."""
    lines_told = _lines_told_of_each_file(story)
    housekeeping = frozenset(story.housekeeping)
    return [
        left
        for file in files
        if file.path not in housekeeping
        for left in _left_out_of(file, change[file.path], lines_told.get(file.path, []))
    ]


def _lines_told_of_each_file(story: Story[Step]) -> dict[str, list[LineSpan]]:
    """The lines the story's steps tell, by the file they are lines of."""
    lines_told: dict[str, list[LineSpan]] = {}
    for chapter in story.chapters:
        for step in chapter.steps:
            lines_told.setdefault(step.file, []).append(step.lines)
    return lines_told


def _left_out_of(file: DiffFile, placed: PlacedFile, lines_told: list[LineSpan]) -> list[LeftOut]:
    """What steps of these lines leave out of one file, if anything.

    A file the change shows no line of — binary, too large, only moved —
    has no line for a step to tell, and is left out whole, as it is.
    """
    if not placed.shows_lines:
        return [LeftOut(piece=file, changed_lines=0)]
    left = placed.left_out([placed.rows_at(lines) for lines in lines_told])
    return [LeftOut(piece=placed.piece(left), changed_lines=placed.changed_lines(left))] if left else []
