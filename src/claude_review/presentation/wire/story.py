"""A story on the wire: the document the agent writes, and the story as a page is told it.

Two families of models, because a story crosses the wire twice and is not
the same thing each way. The agent sends a document it wrote by hand: it is
held to a request's bounds, a field it does not have is refused rather than
passed over, and a step's lines come as a person writes them, "104-129".
A page is sent the story once it is told: every step with the piece of the
change it shows, and what no step tells beside it.

What a story is held to as a story — the length of each text, links that
lead somewhere, steps that tell something — is not asked here: the review
asks all of that at once (`services/story_checks.py`), so the agent hears
everything wrong with its story in one answer.
"""

from typing import Annotated, Self

from pydantic import ConfigDict, Field

from claude_review.domain import story
from claude_review.domain.models import MAX_ID_LENGTH, MAX_PATH_LENGTH
from claude_review.domain.story import ToldFrom
from claude_review.presentation.wire.base import MAX_TEXT_LENGTH, LinesWritten, WireBool, WireModel
from claude_review.presentation.wire.content import DiffFile
from claude_review.services.review import review_story

# The most of each thing one document may hold. A story with more is not a
# story any more, and the request that carries one stays bounded; how much a
# story SHOULD hold is no business of these.
MAX_CHAPTERS = 100
MAX_STEPS_IN_CHAPTER = 200
MAX_OVERVIEW_ITEMS = 100
MAX_DIAGRAM_LINKS = 100
MAX_HOUSEKEEPING_FILES = 2000

# A text of the story as the agent sends it: bounded as anything said in a
# review is. The length its kind is held to is the story's own rule, said
# with a hint by the story's checks.
StoryWords = Annotated[str, Field(max_length=MAX_TEXT_LENGTH)]
# What a chapter is led to by, and what a part of the diagram is called
StoryName = Annotated[str, Field(max_length=MAX_ID_LENGTH)]
# A file of the change, by any name the change gives one: a name no thread
# could carry is still told
ChangedFile = Annotated[str, Field(max_length=MAX_PATH_LENGTH)]


class StoryInput(WireModel):
    """A part of a story's document as the agent wrote it: a field it does not have is refused, never passed over."""

    model_config = ConfigDict(extra="forbid")


class StepInput(StoryInput):
    """A piece of the change, and why it is the way it is."""

    file: ChangedFile
    lines: LinesWritten
    reason: StoryWords | None = None


class ChapterInput(StoryInput):
    """Changes that belong together, told one step after another."""

    id: StoryName
    title: StoryWords
    why: StoryWords
    doubt: StoryWords | None = None
    steps: list[StepInput] = Field(max_length=MAX_STEPS_IN_CHAPTER)


class OverviewItemInput(StoryInput):
    """One thing the overview lists, and the chapter that shows it, when one does."""

    text: StoryWords
    chapter: StoryName | None = None


class DiagramInput(StoryInput):
    """The change drawn, and the chapter each part of the drawing leads to."""

    mermaid: StoryWords
    caption: StoryWords | None = None
    links: dict[StoryName, StoryName] = Field(default_factory=dict, max_length=MAX_DIAGRAM_LINKS)


class StoryOverviewInput(StoryInput):
    """The change in short. What it lists may be left out: a story need not have turned anything down."""

    task: StoryWords
    done: StoryWords
    doubt: StoryWords | None = None
    diagram: DiagramInput | None = None
    decisions: list[OverviewItemInput] = Field(default_factory=list, max_length=MAX_OVERVIEW_ITEMS)
    turned_down: list[OverviewItemInput] = Field(default_factory=list, max_length=MAX_OVERVIEW_ITEMS)
    later: list[OverviewItemInput] = Field(default_factory=list, max_length=MAX_OVERVIEW_ITEMS)


class StoryRequest(StoryInput):
    """Request body for PUT /api/story — the story the agent tells of the change, whole.

    It says what it is told from, and has no way not to: a reconstruction
    that forgot to say so would pass for the memory of whoever made the
    change.
    """

    title: StoryWords
    told_from: ToldFrom
    overview: StoryOverviewInput
    chapters: list[ChapterInput] = Field(max_length=MAX_CHAPTERS)
    housekeeping: list[ChangedFile] = Field(default_factory=list, max_length=MAX_HOUSEKEEPING_FILES)

    def in_the_review(self) -> story.Story[story.Step]:
        """The story the document writes, as the review's own models hold one."""
        return story.Story[story.Step].model_validate(self, from_attributes=True)


class LineSpan(WireModel):
    """Lines of a file, the first and the last both among them."""

    first: int
    last: int


class OverviewItem(WireModel):
    """One thing the overview lists, and the chapter that shows it, when one does."""

    text: str
    chapter: str | None


class Diagram(WireModel):
    """The change drawn, as Mermaid writes one, and the chapter each part of the drawing leads to."""

    mermaid: str
    caption: str | None
    links: dict[str, str]


class StoryOverview(WireModel):
    """The change in short: what was asked, what was done, what to doubt, and what the overview lists."""

    task: str
    done: str
    doubt: str | None
    diagram: Diagram | None
    decisions: list[OverviewItem]
    turned_down: list[OverviewItem]
    later: list[OverviewItem]


class StepNow(WireModel):
    """Where a step's code stands on the take of the change the story is on."""

    # The rows of the file the step is, to be drawn as a file is
    piece: DiffFile
    # Whether a round's work changed them after the step was told
    changed_since_told: WireBool


class ToldStep(WireModel):
    """A step as it is told: its reason, when it has one, and where its code stands now, if anywhere."""

    file: str
    lines: LineSpan
    reason: str | None
    # Null where its code is not in the change as it now stands
    now: StepNow | None
    # Whether a thread may hang on what it says: a path holding a control character is shown, but only to be read
    commentable: WireBool


class ToldChapter(WireModel):
    """A chapter as it is told: why its changes belong together, where to look hardest, and its steps."""

    id: str
    title: str
    why: str
    doubt: str | None
    steps: list[ToldStep]


class LeftOut(WireModel):
    """What the story leaves out of one file, shown beside it all the same."""

    piece: DiffFile
    # How many lines of it the change added or removed
    changed_lines: int


class ToldStory(WireModel):
    """A story on the change it is told of: every step with what it shows, and what no step tells."""

    title: str
    told_from: ToldFrom
    overview: StoryOverview
    chapters: list[ToldChapter]
    housekeeping: list[str]
    left_out: list[LeftOut]


class LeftOutChanged(WireModel):
    """How many changed lines no step told when a story was told, and how many none tells now."""

    when_told: int
    now: int


class CodeMovedOn(WireModel):
    """That a round's work moved the code under a story told before it: in which round, and how much is left out."""

    # The round of the take that first found it so: a later take that finds it still so keeps it
    round: int
    # Said only where the round changed how much is left out; None where as much is left out as when it was told
    left_out: LeftOutChanged | None


class StoryHeld(WireModel):
    """A story as the review holds it: on a take of the change, with the round it was told in."""

    story: ToldStory
    round: int
    # The take of the change its pieces were cut out of: their lines are
    # numbered as the threads' are only while the diff a page read says the
    # same take
    take: int
    # Set while the code under it moved on after it was told; None while it is current
    moved_on: CodeMovedOn | None


class StoryResponse(WireModel):
    """Response for GET /api/story — the story the review holds, or none while nobody has told one."""

    held: StoryHeld | None


class LeftOutOfFile(WireModel):
    """How much of one file a story leaves out: enough to say so in a line."""

    file: str
    # How many lines of it the change added or removed and no step tells:
    # none, of a file the change shows no line of
    changed_lines: int


class StoryTakenResponse(WireModel):
    """Response for PUT /api/story — what the review made of the story it took, in short.

    The agent wrote the story and does not need it back; what it cannot
    know is what its steps left for the reader to find alone.
    """

    round: int
    chapters: int
    steps: int
    left_out: list[LeftOutOfFile]

    @classmethod
    def summing_up(cls, held: review_story.StoryHeld) -> Self:
        """A story the review has just taken, summed up for whoever told it."""
        told = held.story
        return cls(
            round=held.round,
            chapters=len(told.chapters),
            steps=sum(len(chapter.steps) for chapter in told.chapters),
            left_out=[LeftOutOfFile(file=left.piece.path, changed_lines=left.changed_lines) for left in told.left_out],
        )
