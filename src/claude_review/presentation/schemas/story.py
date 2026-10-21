"""The API's story: the document the agent writes, and the story as a page is told it.

Two families of schemas, because a story passes through the API twice and is
not the same thing each way. The agent sends a document it wrote by hand: it is
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

from pydantic import ConfigDict, Field, StrictBool

from claude_review.domain import models, story
from claude_review.domain.models import MAX_ID_LENGTH, MAX_PATH_LENGTH
from claude_review.domain.story import ToldFrom
from claude_review.presentation.schemas.base import MAX_TEXT_LENGTH, LinesWritten, Schema, made_or_none
from claude_review.presentation.schemas.content import DiffFile

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


class StoryInput(Schema):
    """A part of a story's document as the agent wrote it: a field it does not have is refused, never passed over."""

    model_config = ConfigDict(extra="forbid")


class StepInput(StoryInput):
    """A piece of the change, and why it is the way it is."""

    file: ChangedFile
    lines: LinesWritten
    reason: StoryWords | None = None

    def to_domain(self) -> story.Step:
        return story.Step(file=self.file, lines=self.lines, reason=self.reason)


class ChapterInput(StoryInput):
    """Changes that belong together, told one step after another."""

    id: StoryName
    title: StoryWords
    why: StoryWords
    doubt: StoryWords | None = None
    steps: list[StepInput] = Field(max_length=MAX_STEPS_IN_CHAPTER)

    def to_domain(self) -> story.Chapter[story.Step]:
        return story.Chapter[story.Step](
            id=self.id,
            title=self.title,
            why=self.why,
            doubt=self.doubt,
            steps=[step.to_domain() for step in self.steps],
        )


class OverviewItemInput(StoryInput):
    """One thing the overview lists, and the chapter that shows it, when one does."""

    text: StoryWords
    chapter: StoryName | None = None

    def to_domain(self) -> story.OverviewItem:
        return story.OverviewItem(text=self.text, chapter=self.chapter)


class DiagramInput(StoryInput):
    """The change drawn, and the chapter each part of the drawing leads to."""

    mermaid: StoryWords
    caption: StoryWords | None = None
    links: dict[StoryName, StoryName] = Field(default_factory=dict, max_length=MAX_DIAGRAM_LINKS)

    def to_domain(self) -> story.Diagram:
        return story.Diagram(mermaid=self.mermaid, caption=self.caption, links=self.links)


class StoryOverviewInput(StoryInput):
    """The change in short. What it lists may be left out: a story need not have turned anything down."""

    task: StoryWords
    done: StoryWords
    doubt: StoryWords | None = None
    diagram: DiagramInput | None = None
    decisions: list[OverviewItemInput] = Field(default_factory=list, max_length=MAX_OVERVIEW_ITEMS)
    turned_down: list[OverviewItemInput] = Field(default_factory=list, max_length=MAX_OVERVIEW_ITEMS)
    later: list[OverviewItemInput] = Field(default_factory=list, max_length=MAX_OVERVIEW_ITEMS)

    def to_domain(self) -> story.StoryOverview:
        return story.StoryOverview(
            task=self.task,
            done=self.done,
            doubt=self.doubt,
            diagram=made_or_none(DiagramInput.to_domain, self.diagram),
            decisions=[item.to_domain() for item in self.decisions],
            turned_down=[item.to_domain() for item in self.turned_down],
            later=[item.to_domain() for item in self.later],
        )


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

    def to_domain(self) -> story.Story[story.Step]:
        """The story the document writes, as the domain's models hold one."""
        return story.Story[story.Step](
            title=self.title,
            told_from=self.told_from,
            overview=self.overview.to_domain(),
            chapters=[chapter.to_domain() for chapter in self.chapters],
            housekeeping=self.housekeeping,
        )


class LineSpan(Schema):
    """Lines of a file, the first and the last both among them."""

    first: int
    last: int

    @classmethod
    def from_domain(cls, lines: models.LineSpan) -> Self:
        return cls(first=lines.first, last=lines.last)


class OverviewItem(Schema):
    """One thing the overview lists, and the chapter that shows it, when one does."""

    text: str
    chapter: str | None

    @classmethod
    def from_domain(cls, item: story.OverviewItem) -> Self:
        return cls(text=item.text, chapter=item.chapter)


class Diagram(Schema):
    """The change drawn, as Mermaid writes one, and the chapter each part of the drawing leads to."""

    mermaid: str
    caption: str | None
    links: dict[str, str]

    @classmethod
    def from_domain(cls, diagram: story.Diagram) -> Self:
        return cls(mermaid=diagram.mermaid, caption=diagram.caption, links=diagram.links)


class StoryOverview(Schema):
    """The change in short: what was asked, what was done, what to doubt, and what the overview lists."""

    task: str
    done: str
    doubt: str | None
    diagram: Diagram | None
    decisions: list[OverviewItem]
    turned_down: list[OverviewItem]
    later: list[OverviewItem]

    @classmethod
    def from_domain(cls, overview: story.StoryOverview) -> Self:
        return cls(
            task=overview.task,
            done=overview.done,
            doubt=overview.doubt,
            diagram=made_or_none(Diagram.from_domain, overview.diagram),
            decisions=[OverviewItem.from_domain(item) for item in overview.decisions],
            turned_down=[OverviewItem.from_domain(item) for item in overview.turned_down],
            later=[OverviewItem.from_domain(item) for item in overview.later],
        )


class StepNow(Schema):
    """Where a step's code stands on the take of the change the story is on."""

    # The lines it stands at there, which a round's work may have moved from those it was told on
    lines: LineSpan
    # The rows of the file the step is, to be drawn as a file is
    piece: DiffFile
    # Whether a round's work changed them after the step was told
    changed_since_told: StrictBool

    @classmethod
    def from_domain(cls, now: story.StepNow) -> Self:
        return cls(
            lines=LineSpan.from_domain(now.lines),
            piece=DiffFile.from_domain(now.piece),
            changed_since_told=now.changed_since_told,
        )


class FollowedStep(Schema):
    """A step on the take the story is on: its reason, when it has one, and where its code stands there, if anywhere."""

    file: str
    # The lines it was told on, which it is known by: a round's work never moves them
    lines: LineSpan
    reason: str | None
    # Null where its code is not in the change as it now stands
    now: StepNow | None
    # Whether a thread may hang on what it says: a path holding a control character is shown, but only to be read
    commentable: StrictBool

    @classmethod
    def from_domain(cls, step: story.FollowedStep) -> Self:
        return cls(
            file=step.file,
            lines=LineSpan.from_domain(step.lines),
            reason=step.reason,
            now=made_or_none(StepNow.from_domain, step.now),
            commentable=step.commentable,
        )


class FollowedChapter(Schema):
    """A chapter on the take the story is on: why its changes belong together, where to look hardest, and its steps."""

    id: str
    title: str
    why: str
    doubt: str | None
    steps: list[FollowedStep]
    # How many of its steps show code a round changed after they were told: a page draws it under the chapter's
    # head and in the story's contents, and counts nothing
    changed_steps: int

    @classmethod
    def from_domain(cls, chapter: story.Chapter[story.FollowedStep]) -> Self:
        return cls(
            id=chapter.id,
            title=chapter.title,
            why=chapter.why,
            doubt=chapter.doubt,
            steps=[FollowedStep.from_domain(step) for step in chapter.steps],
            changed_steps=chapter.changed_steps,
        )


class LeftOut(Schema):
    """What the story leaves out of one file, shown beside it all the same."""

    piece: DiffFile
    # How many lines of it the change added or removed
    changed_lines: int

    @classmethod
    def from_domain(cls, left: story.LeftOut) -> Self:
        return cls(piece=DiffFile.from_domain(left.piece), changed_lines=left.changed_lines)


class ToldStory(Schema):
    """A story on the change it is told of: every step with what it shows, and what no step tells."""

    title: str
    told_from: ToldFrom
    overview: StoryOverview
    chapters: list[FollowedChapter]
    housekeeping: list[str]
    left_out: list[LeftOut]

    @classmethod
    def from_domain(cls, told: story.ToldStory[story.FollowedStep]) -> Self:
        return cls(
            title=told.title,
            told_from=told.told_from,
            overview=StoryOverview.from_domain(told.overview),
            chapters=[FollowedChapter.from_domain(chapter) for chapter in told.chapters],
            housekeeping=told.housekeeping,
            left_out=[LeftOut.from_domain(left) for left in told.left_out],
        )


class LeftOutChanged(Schema):
    """How many changed lines no step told when a story was told, and how many none tells now."""

    when_told: int
    now: int

    @classmethod
    def from_domain(cls, changed: story.LeftOutChanged) -> Self:
        return cls(when_told=changed.when_told, now=changed.now)


class CodeMovedOn(Schema):
    """That a round's work moved the code under a story told before it: in which round, and how much is left out."""

    # The round of the take that first found it so: a later take that finds it still so keeps it
    round: int
    # Said only where the round changed how much is left out; None where as much is left out as when it was told
    left_out: LeftOutChanged | None

    @classmethod
    def from_domain(cls, moved_on: story.CodeMovedOn) -> Self:
        return cls(round=moved_on.round, left_out=made_or_none(LeftOutChanged.from_domain, moved_on.left_out))


class StoryHeld(Schema):
    """A story as the review holds it: on a take of the change, with the round it was told in."""

    story: ToldStory
    round: int
    # The take of the change its pieces were cut out of: their lines are
    # numbered as the threads' are only while the diff a page read says the
    # same take
    take: int
    # Set while the code under it moved on after it was told; None while it is current
    moved_on: CodeMovedOn | None

    @classmethod
    def from_domain(cls, held: story.StoryHeld) -> Self:
        return cls(
            story=ToldStory.from_domain(held.story),
            round=held.round,
            take=held.take,
            moved_on=made_or_none(CodeMovedOn.from_domain, held.moved_on),
        )


class StoryResponse(Schema):
    """Response for GET /api/story — the story the review holds, or none while nobody has told one."""

    held: StoryHeld | None


class LeftOutOfFile(Schema):
    """How much of one file a story leaves out: enough to say so in a line."""

    file: str
    # How many lines of it the change added or removed and no step tells:
    # none, of a file the change shows no line of
    changed_lines: int

    @classmethod
    def from_domain(cls, left: story.LeftOut) -> Self:
        return cls(file=left.piece.path, changed_lines=left.changed_lines)


class StoryTakenResponse(Schema):
    """Response for PUT /api/story — what the review made of the story it took, in short.

    The agent wrote the story and does not need it back; what it cannot
    know is what its steps left for the reader to find alone.
    """

    round: int
    chapters: int
    steps: int
    left_out: list[LeftOutOfFile]

    @classmethod
    def summing_up(cls, told: story.ToldStory[story.FollowedStep], *, round_number: int) -> Self:
        """A story the review has just taken, in the round it was told in, summed up for whoever told it."""
        return cls(
            round=round_number,
            chapters=len(told.chapters),
            steps=sum(len(chapter.steps) for chapter in told.chapters),
            left_out=[LeftOutOfFile.from_domain(left) for left in told.left_out],
        )
