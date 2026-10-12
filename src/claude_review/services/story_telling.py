"""Telling a story of a change: the story as written, placed on the change, or refused with everything wrong.

A story may be told once nothing is wrong with it, by itself or against the
change. Told, each step carries the piece of its file it shows, cut out of
the change by the one rule that says what a step is, and whatever of the
change no step tells is set beside the story — so every line the change
added or removed is in a step, in a file named as housekeeping, or among
what was left out, and a story cannot hide one.
"""

from claude_review.domain.models import DiffFile
from claude_review.domain.story import Chapter, LeftOut, Step, Story, StoryRefusedError, ToldStep, ToldStory
from claude_review.services.story_checks import document_faults, placement_faults
from claude_review.services.story_slices import ToldFile


def tell(story: Story[Step], files: list[DiffFile]) -> ToldStory:
    """The story on the change it is told of.

    Raises:
        StoryRefusedError: if anything is wrong with it, carrying all of it.
    """
    change = {file.path: ToldFile(file) for file in files}
    faults = [*document_faults(story), *placement_faults(story, change)]
    if faults:
        raise StoryRefusedError(faults)
    return ToldStory(
        title=story.title,
        overview=story.overview,
        chapters=[_told_chapter(chapter, change) for chapter in story.chapters],
        housekeeping=story.housekeeping,
        left_out=_left_out(story, files, change),
    )


def _told_chapter(chapter: Chapter[Step], change: dict[str, ToldFile]) -> Chapter[ToldStep]:
    """A chapter with each of its steps as it is told."""
    return Chapter[ToldStep](
        id=chapter.id,
        title=chapter.title,
        why=chapter.why,
        doubt=chapter.doubt,
        steps=[_told_step(step, change[step.file]) for step in chapter.steps],
    )


def _told_step(step: Step, file: ToldFile) -> ToldStep:
    """A step with the piece of its file it shows."""
    return ToldStep(file=step.file, lines=step.lines, reason=step.reason, piece=file.piece(file.rows_at(step.lines)))


def _left_out(story: Story[Step], files: list[DiffFile], change: dict[str, ToldFile]) -> list[LeftOut]:
    """What the story leaves out, file by file in the order of the change: nothing of a housekeeping file."""
    steps = [step for chapter in story.chapters for step in chapter.steps]
    return [
        left
        for file in files
        if file.path not in story.housekeeping
        for left in _left_out_of(file, change[file.path], [step for step in steps if step.file == file.path])
    ]


def _left_out_of(file: DiffFile, told: ToldFile, steps: list[Step]) -> list[LeftOut]:
    """What the steps of one file leave out of it, if anything.

    A file the change shows no line of — binary, too large, only moved —
    has no line for a step to tell, and is left out whole, as it is.
    """
    if not told.shows_lines:
        return [LeftOut(piece=file, changed_lines=0)]
    left = told.left_out([run for step in steps for run in told.rows_at(step.lines)])
    return [LeftOut(piece=told.piece(left), changed_lines=told.changed_lines(left))] if left else []
