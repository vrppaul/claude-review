"""What keeps a story from being told, found all at once.

The agent writes a story in one go and sends it whole. Refused for one
fault, it would put that right and send the story again, to be refused for
the next: so the whole document is read first, and everything wrong with it
is said in one answer, each fault at the field it is about.

Two readings find them. One is of what the document shows by itself,
whatever change it is told of: texts that say nothing or run past their
length, chapters and links that do not hold together, lines no file could
have or told twice. The other is against the change: a step or a
housekeeping file the change does not have, and a step that tells nothing
the change did.
"""

from collections.abc import Iterator

from pydantic import BaseModel, ConfigDict

from claude_review.domain.exceptions import FieldFault, FieldPath
from claude_review.domain.models import FIRST_LINE
from claude_review.domain.story import TEXT_LIMITS, Chapter, OverviewItem, Step, Story, StoryOverview, StoryText
from claude_review.services.place_words import line_span
from claude_review.services.story_slices import ToldFile

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
FILE = "file"
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
NO_SUCH_FILE = "is no file of this change"
NO_LINES_SHOWN = "is a file the change shows no line of: a step has nothing of it to tell"
NO_CHANGE_TOLD = "hold no line of {file} that the change added or removed: a step tells something it did"
HOUSEKEEPING_TOLD = "is told in chapter {chapter}: a file with a step to it is not housekeeping"


class StepInDocument(BaseModel):
    """A step, where it stands in its story's document, and the chapter that tells it."""

    model_config = ConfigDict(frozen=True)

    path: FieldPath
    chapter: Chapter[Step]
    step: Step


def document_faults(story: Story[Step]) -> list[FieldFault]:
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


def placement_faults(story: Story[Step], change: dict[str, ToldFile]) -> list[FieldFault]:
    """Everything wrong with a story that only the change it is told of shows, each fault at its field.

    `change` is the files of the change by their paths. A step told of
    lines no file could have is left out: it is refused for that already.
    """
    steps = [told for told in _steps_of(story.chapters) if not _numbering_faults(told)]
    return [
        *(fault for told in steps for fault in _step_faults(told, change)),
        *_housekeeping_faults(story, change),
    ]


def _step_faults(told: StepInDocument, change: dict[str, ToldFile]) -> Iterator[FieldFault]:
    """What is wrong with a step against the change.

    Its file is not in the change, or shows no line; or its lines hold nothing
    the change added or removed.
    """
    file = change.get(told.step.file)
    if file is None:
        yield FieldFault(path=(*told.path, FILE), reason=NO_SUCH_FILE)
    elif not file.shows_lines:
        yield FieldFault(path=(*told.path, FILE), reason=NO_LINES_SHOWN)
    elif file.changed_lines(file.rows_at(told.step.lines)) == 0:
        yield FieldFault(path=(*told.path, LINES), reason=NO_CHANGE_TOLD.format(file=told.step.file))


def _housekeeping_faults(story: Story[Step], change: dict[str, ToldFile]) -> Iterator[FieldFault]:
    """Every housekeeping file the change does not have, and every one a step is told of.

    A file is housekeeping because it has nothing to tell: named as that
    and told in a step, it would be both.
    """
    steps = list(_steps_of(story.chapters))
    for index, file in enumerate(story.housekeeping):
        told = next((told for told in steps if told.step.file == file), None)
        if file not in change:
            yield FieldFault(path=(HOUSEKEEPING, index), reason=NO_SUCH_FILE)
        elif told is not None:
            yield FieldFault(path=(HOUSEKEEPING, index), reason=HOUSEKEEPING_TOLD.format(chapter=told.chapter.id))


def _texts_out_of_bounds(story: Story[Step]) -> Iterator[FieldFault]:
    """Every text of the story that says nothing, or more than its kind may."""
    yield from _text_faults((TITLE,), story.title, StoryText.TITLE)
    yield from _overview_texts_out_of_bounds(story.overview)
    for index, chapter in enumerate(story.chapters):
        yield from _text_faults((CHAPTERS, index, TITLE), chapter.title, StoryText.CHAPTER_TITLE)
        yield from _text_faults((CHAPTERS, index, WHY), chapter.why, StoryText.CHAPTER_WHY)
        yield from _text_faults((CHAPTERS, index, DOUBT), chapter.doubt, StoryText.CHAPTER_DOUBT)
    for told in _steps_of(story.chapters):
        yield from _text_faults((*told.path, REASON), told.step.reason, StoryText.STEP_REASON)


def _overview_texts_out_of_bounds(overview: StoryOverview) -> Iterator[FieldFault]:
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


def _text_faults(path: FieldPath, text: str | None, kind: StoryText) -> Iterator[FieldFault]:
    """What is wrong with a text of one kind: it says nothing, or runs past the length its kind may be.

    A text left out is no text, and has nothing wrong with it.
    """
    if text is None:
        return
    held_to = TEXT_LIMITS[kind]
    if _says_nothing(text):
        yield FieldFault(path=path, reason=SAYS_NOTHING)
    elif len(text) > held_to.characters:
        too_long = TOO_LONG.format(length=len(text), limit=held_to.characters, hint=held_to.hint)
        yield FieldFault(path=path, reason=too_long)


def _blank_faults(path: FieldPath, text: str) -> Iterator[FieldFault]:
    """What is wrong with a text that has no length to keep to: it says nothing."""
    if _says_nothing(text):
        yield FieldFault(path=path, reason=SAYS_NOTHING)


def _says_nothing(text: str) -> bool:
    """Whether a text is blanks alone."""
    return not text.strip()


def _parts_missing(chapters: list[Chapter[Step]]) -> Iterator[FieldFault]:
    """A story with no chapter, and every chapter with no step: neither tells anything."""
    if not chapters:
        yield FieldFault(path=(CHAPTERS,), reason=NO_CHAPTERS)
    for index, chapter in enumerate(chapters):
        if not chapter.steps:
            yield FieldFault(path=(CHAPTERS, index, STEPS), reason=NO_STEPS)


def _ids_repeated(chapters: list[Chapter[Step]]) -> Iterator[FieldFault]:
    """Every chapter under an id an earlier chapter has: a link to that id could mean either."""
    ids = [chapter.id for chapter in chapters]
    for index in _repeated_at(ids):
        yield FieldFault(path=(CHAPTERS, index, ID), reason=ID_REPEATED.format(chapter=ids[index]))


def _links_to_no_chapter(story: Story[Step]) -> Iterator[FieldFault]:
    """Every link the overview makes to a chapter the story does not have."""
    known = frozenset(chapter.id for chapter in story.chapters)
    overview = story.overview
    for name, items in _item_lists(overview).items():
        for index, item in enumerate(items):
            yield from _link_faults((OVERVIEW, name, index, CHAPTER), item.chapter, known)
    if overview.diagram is not None:
        for part, chapter in overview.diagram.links.items():
            yield from _link_faults((OVERVIEW, DIAGRAM, LINKS, part), chapter, known)


def _link_faults(path: FieldPath, chapter: str | None, known: frozenset[str]) -> Iterator[FieldFault]:
    """What is wrong with a link: it leads to a chapter the story does not have. One left out leads nowhere."""
    if chapter is not None and chapter not in known:
        yield FieldFault(path=path, reason=NO_SUCH_CHAPTER.format(chapter=chapter))


def _lines_numbered_wrongly(chapters: list[Chapter[Step]]) -> Iterator[FieldFault]:
    """Every step told of lines no file could have."""
    for told in _steps_of(chapters):
        yield from _numbering_faults(told)


def _numbering_faults(told: StepInDocument) -> list[FieldFault]:
    """What is wrong with how a step's lines are numbered: from before a file's first line, or backwards."""
    lines = told.step.lines
    path = (*told.path, LINES)
    faults: list[FieldFault] = []
    if lines.first < FIRST_LINE:
        faults.append(FieldFault(path=path, reason=BEFORE_FIRST_LINE.format(first=lines.first, first_line=FIRST_LINE)))
    if lines.last < lines.first:
        faults.append(FieldFault(path=path, reason=RUNS_BACKWARDS.format(first=lines.first, last=lines.last)))
    return faults


def _lines_told_twice(chapters: list[Chapter[Step]]) -> Iterator[FieldFault]:
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
            yield FieldFault(path=(*later.path, LINES), reason=TOLD_TWICE.format(lines=met, chapter=earlier.chapter.id))


def _share_a_line(one: Step, other: Step) -> bool:
    """Whether two steps tell a line of the same file."""
    return one.file == other.file and one.lines.meets(other.lines)


def _files_named_twice(housekeeping: list[str]) -> Iterator[FieldFault]:
    """Every file the housekeeping names again, having named it once."""
    for index in _repeated_at(housekeeping):
        yield FieldFault(path=(HOUSEKEEPING, index), reason=NAMED_TWICE.format(file=housekeeping[index]))


def _steps_of(chapters: list[Chapter[Step]]) -> Iterator[StepInDocument]:
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
