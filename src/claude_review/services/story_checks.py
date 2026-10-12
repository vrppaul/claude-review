"""What keeps a story from being told, found all at once.

The agent writes a story in one go and sends it whole. Refused for one
fault, it would put that right and send the story again, to be refused for
the next: so the whole document is read first, and everything wrong with it
is said in one answer, each fault at the field it is about.

What is read here is what a document shows by itself, whatever change it is
told of: texts that say nothing or run past their length, chapters and
links that do not hold together, lines no file could have or told twice.
"""

from collections.abc import Iterator

from pydantic import BaseModel, ConfigDict

from claude_review.domain.models import FIRST_LINE
from claude_review.domain.story import (
    TEXT_LIMITS,
    Chapter,
    FieldPath,
    OverviewItem,
    Step,
    Story,
    StoryFault,
    StoryOverview,
    StoryText,
)
from claude_review.services.place_words import line_span

# The fields of a story's document, as a fault names them: what the
# document's own models call them, since that is what the agent wrote
TITLE = "title"
OVERVIEW = "overview"
TASK = "task"
DONE = "done"
DOUBT = "doubt"
DIAGRAM = "diagram"
MERMAID = "mermaid"
CAPTION = "caption"
LINKS = "links"
DECISIONS = "decisions"
TURNED_DOWN = "turned_down"
LATER = "later"
TEXT = "text"
CHAPTER = "chapter"
CHAPTERS = "chapters"
ID = "id"
WHY = "why"
STEPS = "steps"
LINES = "lines"
REASON = "reason"
HOUSEKEEPING = "housekeeping"

# What is wrong at a field, in words the agent can act on
SAYS_NOTHING = "says nothing"
TOO_LONG = "is {length} characters long, and may be {limit} at most. {hint}"
NO_CHAPTERS = "holds no chapter: a story tells at least one"
NO_STEPS = "holds no step: a chapter shows at least one piece of the change"
ID_REPEATED = "{chapter} is an earlier chapter's id as well: a link to it could mean either"
NO_SUCH_CHAPTER = "leads to chapter {chapter}, and the story has none by that id"
BEFORE_FIRST_LINE = "starts at line {first}: a file's lines are numbered from {first_line}"
RUNS_BACKWARDS = "runs backwards, from line {first} to line {last}"
TOLD_TWICE = "meets lines {lines} of the same file, which chapter {chapter} tells already: a line is told once"
NAMED_TWICE = "names {file} a second time"


class StepInDocument(BaseModel):
    """A step, where it stands in its story's document, and the chapter that tells it."""

    model_config = ConfigDict(frozen=True)

    path: FieldPath
    chapter: Chapter
    step: Step


def document_faults(story: Story) -> list[StoryFault]:
    """Everything wrong with a story that its document shows by itself, each fault at its field."""
    return [
        *_texts_out_of_bounds(story),
        *_parts_missing(story.chapters),
        *_ids_repeated(story.chapters),
        *_links_to_no_chapter(story),
        *_lines_numbered_wrongly(story.chapters),
        *_lines_told_twice(story.chapters),
        *_files_named_twice(story.housekeeping),
    ]


def _texts_out_of_bounds(story: Story) -> Iterator[StoryFault]:
    """Every text of the story that says nothing, or more than its kind may."""
    yield from _text_faults((TITLE,), story.title, StoryText.TITLE)
    yield from _overview_texts_out_of_bounds(story.overview)
    for index, chapter in enumerate(story.chapters):
        yield from _text_faults((CHAPTERS, index, TITLE), chapter.title, StoryText.CHAPTER_TITLE)
        yield from _text_faults((CHAPTERS, index, WHY), chapter.why, StoryText.CHAPTER_WHY)
        yield from _text_faults((CHAPTERS, index, DOUBT), chapter.doubt, StoryText.CHAPTER_DOUBT)
    for told in _steps_of(story.chapters):
        yield from _text_faults((*told.path, REASON), told.step.reason, StoryText.STEP_REASON)


def _overview_texts_out_of_bounds(overview: StoryOverview) -> Iterator[StoryFault]:
    """Every text of the overview that says nothing or too much: its three lines, its drawing, what it lists."""
    yield from _text_faults((OVERVIEW, TASK), overview.task, StoryText.TASK)
    yield from _text_faults((OVERVIEW, DONE), overview.done, StoryText.DONE)
    yield from _text_faults((OVERVIEW, DOUBT), overview.doubt, StoryText.DOUBT)
    if overview.diagram is not None:
        yield from _blank_faults((OVERVIEW, DIAGRAM, MERMAID), overview.diagram.mermaid)
        yield from _text_faults((OVERVIEW, DIAGRAM, CAPTION), overview.diagram.caption, StoryText.CAPTION)
    for name, items in _item_lists(overview).items():
        for index, item in enumerate(items):
            yield from _text_faults((OVERVIEW, name, index, TEXT), item.text, StoryText.ITEM)


def _text_faults(path: FieldPath, text: str | None, kind: StoryText) -> Iterator[StoryFault]:
    """What is wrong with a text of one kind: it says nothing, or runs past the length its kind may be.

    A text left out is no text, and has nothing wrong with it.
    """
    if text is None:
        return
    held_to = TEXT_LIMITS[kind]
    if _says_nothing(text):
        yield StoryFault(path=path, reason=SAYS_NOTHING)
    elif len(text) > held_to.characters:
        too_long = TOO_LONG.format(length=len(text), limit=held_to.characters, hint=held_to.hint)
        yield StoryFault(path=path, reason=too_long)


def _blank_faults(path: FieldPath, text: str) -> Iterator[StoryFault]:
    """What is wrong with a text that has no length to keep to: it says nothing."""
    if _says_nothing(text):
        yield StoryFault(path=path, reason=SAYS_NOTHING)


def _says_nothing(text: str) -> bool:
    """Whether a text is blanks alone."""
    return not text.strip()


def _parts_missing(chapters: list[Chapter]) -> Iterator[StoryFault]:
    """A story with no chapter, and every chapter with no step: neither tells anything."""
    if not chapters:
        yield StoryFault(path=(CHAPTERS,), reason=NO_CHAPTERS)
    for index, chapter in enumerate(chapters):
        if not chapter.steps:
            yield StoryFault(path=(CHAPTERS, index, STEPS), reason=NO_STEPS)


def _ids_repeated(chapters: list[Chapter]) -> Iterator[StoryFault]:
    """Every chapter under an id an earlier chapter has: a link to that id could mean either."""
    ids = [chapter.id for chapter in chapters]
    for index in _repeated_at(ids):
        yield StoryFault(path=(CHAPTERS, index, ID), reason=ID_REPEATED.format(chapter=ids[index]))


def _links_to_no_chapter(story: Story) -> Iterator[StoryFault]:
    """Every link the overview makes to a chapter the story does not have."""
    known = frozenset(chapter.id for chapter in story.chapters)
    overview = story.overview
    for name, items in _item_lists(overview).items():
        for index, item in enumerate(items):
            yield from _link_faults((OVERVIEW, name, index, CHAPTER), item.chapter, known)
    if overview.diagram is not None:
        for part, chapter in overview.diagram.links.items():
            yield from _link_faults((OVERVIEW, DIAGRAM, LINKS, part), chapter, known)


def _link_faults(path: FieldPath, chapter: str | None, known: frozenset[str]) -> Iterator[StoryFault]:
    """What is wrong with a link: it leads to a chapter the story does not have. One left out leads nowhere."""
    if chapter is not None and chapter not in known:
        yield StoryFault(path=path, reason=NO_SUCH_CHAPTER.format(chapter=chapter))


def _lines_numbered_wrongly(chapters: list[Chapter]) -> Iterator[StoryFault]:
    """Every step told of lines no file could have."""
    for told in _steps_of(chapters):
        yield from _numbering_faults(told)


def _numbering_faults(told: StepInDocument) -> list[StoryFault]:
    """What is wrong with how a step's lines are numbered: from before a file's first line, or backwards."""
    lines = told.step.lines
    path = (*told.path, LINES)
    faults: list[StoryFault] = []
    if lines.first < FIRST_LINE:
        faults.append(StoryFault(path=path, reason=BEFORE_FIRST_LINE.format(first=lines.first, first_line=FIRST_LINE)))
    if lines.last < lines.first:
        faults.append(StoryFault(path=path, reason=RUNS_BACKWARDS.format(first=lines.first, last=lines.last)))
    return faults


def _lines_told_twice(chapters: list[Chapter]) -> Iterator[StoryFault]:
    """Every step that tells a line an earlier step of the same file tells already.

    A line is told once: told twice, whatever hangs on it — a thread, a
    comment being written — would be drawn under both steps and belong to
    neither. Steps told of lines no file could have are left out: they are
    refused for that already.
    """
    numbered = [told for told in _steps_of(chapters) if not _numbering_faults(told)]
    for position, later in enumerate(numbered):
        earlier = next((told for told in numbered[:position] if _share_a_line(told.step, later.step)), None)
        if earlier is not None:
            met = line_span(earlier.step.lines.first, earlier.step.lines.last)
            yield StoryFault(path=(*later.path, LINES), reason=TOLD_TWICE.format(lines=met, chapter=earlier.chapter.id))


def _share_a_line(one: Step, other: Step) -> bool:
    """Whether two steps tell a line of the same file."""
    return one.file == other.file and one.lines.meets(other.lines)


def _files_named_twice(housekeeping: list[str]) -> Iterator[StoryFault]:
    """Every file the housekeeping names again, having named it once."""
    for index in _repeated_at(housekeeping):
        yield StoryFault(path=(HOUSEKEEPING, index), reason=NAMED_TWICE.format(file=housekeeping[index]))


def _steps_of(chapters: list[Chapter]) -> Iterator[StepInDocument]:
    """Every step of the story in the order it is told, with where it stands and the chapter that tells it."""
    for chapter_index, chapter in enumerate(chapters):
        for step_index, step in enumerate(chapter.steps):
            yield StepInDocument(path=(CHAPTERS, chapter_index, STEPS, step_index), chapter=chapter, step=step)


def _item_lists(overview: StoryOverview) -> dict[str, list[OverviewItem]]:
    """The lists of the overview, each by the field that holds it."""
    return {DECISIONS: overview.decisions, TURNED_DOWN: overview.turned_down, LATER: overview.later}


def _repeated_at(names: list[str]) -> list[int]:
    """Where a list names something it has named earlier already."""
    return [index for index, name in enumerate(names) if name in names[:index]]
