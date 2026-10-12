"""A story: a change told by the agent that made it, in the order it is best read.

A second way to read the same diff. First an overview — what was asked,
what was done, what to doubt — then chapters, each a run of steps, and each
step a piece of the change with the agent's reason above it.

A story comes as a document the agent wrote, and these models are first of
all that: what the document is made of, and nothing about whether it may be
told. That is asked of the whole document at once
(`services/story_checks.py`), so the agent hears everything wrong with it in
one answer, each fault at the field it is about. A story that may be told
is then the same story with what each step shows cut out of the change
(`ToldStory`): only `services/story_telling.py` makes one.
"""

from enum import StrEnum, auto

from pydantic import BaseModel, ConfigDict

from claude_review.domain.models import DiffFile


class StoryPart(BaseModel):
    """What every part of a story is: written once, and never changed."""

    model_config = ConfigDict(frozen=True)


class StepLines(StoryPart):
    """The lines of a file a step is told of, the first and the last both among them."""

    first: int
    last: int

    def holds(self, line: int) -> bool:
        """Whether a line is among them."""
        return self.first <= line <= self.last

    def meets(self, other: StepLines) -> bool:
        """Whether the two hold a line in common, each running from its first line to its last."""
        return self.first <= other.last and other.first <= self.last


class Step(StoryPart):
    """A piece of the change, and why it is the way it is.

    Its lines are numbered as the file now stands — as it stood, for a file
    the change left no line of. A step with no reason shows code that needs
    none.
    """

    # Any file the change touched: one whose name no thread could carry is
    # still told
    file: str
    lines: StepLines
    reason: str | None = None


class Chapter[StepKind: Step](StoryPart):
    """Changes that belong together, told one step after another.

    Its steps are as the agent wrote them, or as they are told, each with
    what it shows: a chapter is the same either way.
    """

    # What the overview and the diagram lead to it by
    id: str
    title: str
    # Why these changes belong together
    why: str
    # Where the reader should look hardest, when there is such a place
    doubt: str | None = None
    steps: list[StepKind]


class OverviewItem(StoryPart):
    """One thing the overview lists: a decision taken, a way turned down, something left for later."""

    text: str
    # The chapter that shows it, by its id, when one does
    chapter: str | None = None


class Diagram(StoryPart):
    """The change drawn: its parts, and the chapter that tells each."""

    # The drawing, as Mermaid writes one. Whether it draws only a browser can
    # say; that an empty one does not, the review can
    mermaid: str
    caption: str | None = None
    # The chapter each part leads to, by the name the drawing gives the part
    links: dict[str, str]


class StoryOverview(StoryPart):
    """The change in short: what was asked, what was done, and what to doubt."""

    task: str
    done: str
    doubt: str | None = None
    diagram: Diagram | None = None
    decisions: list[OverviewItem]
    turned_down: list[OverviewItem]
    later: list[OverviewItem]


class Story[StepKind: Step](StoryPart):
    """A change as the agent tells it, whole: a story is sent in one piece, and replaced in one piece."""

    title: str
    overview: StoryOverview
    chapters: list[Chapter[StepKind]]
    # Files that changed and have nothing to tell — a lock file, a changelog —
    # named so that what changed in them is not held against the story
    housekeeping: list[str]


class StoryText(StrEnum):
    """The kinds of text a story is told in, each held to a length of its own.

    TITLE — what the change is called.
    TASK, DONE, DOUBT — the three lines of the overview.
    CAPTION — what the diagram is called.
    ITEM — one thing the overview lists.
    CHAPTER_TITLE, CHAPTER_WHY, CHAPTER_DOUBT — what a chapter is called, why
    its changes belong together, and where to look hardest in it.
    STEP_REASON — why a piece of the change is the way it is.
    """

    TITLE = auto()
    TASK = auto()
    DONE = auto()
    DOUBT = auto()
    CAPTION = auto()
    ITEM = auto()
    CHAPTER_TITLE = auto()
    CHAPTER_WHY = auto()
    CHAPTER_DOUBT = auto()
    STEP_REASON = auto()


class TextLimit(BaseModel):
    """How long one kind of text may be, and where what does not fit belongs."""

    model_config = ConfigDict(frozen=True)

    characters: int
    # Where the rest belongs, said to whoever wrote more
    hint: str


# A story is short before it is anything else: the overview reads in three
# lines because it cannot be written in more. Each limit says where the rest
# belongs, so a text refused for its length is cut down to what it is for
# rather than trimmed to fit.
TEXT_LIMITS: dict[StoryText, TextLimit] = {
    StoryText.TITLE: TextLimit(characters=80, hint="Name the change. What it does is for the overview to say."),
    StoryText.TASK: TextLimit(characters=160, hint="One sentence. The rest belongs in the decisions."),
    StoryText.DONE: TextLimit(characters=240, hint="Two sentences at most. The rest belongs in the decisions."),
    StoryText.DOUBT: TextLimit(
        characters=200,
        hint="The one thing most worth checking. The rest belongs in the doubt of the chapter it is about.",
    ),
    StoryText.CAPTION: TextLimit(characters=60, hint="A name for the diagram, and no more."),
    StoryText.ITEM: TextLimit(characters=240, hint="One thing to an item. Give the rest an item of its own."),
    StoryText.CHAPTER_TITLE: TextLimit(
        characters=60, hint="Name the chapter. Why its changes belong together is for its why to say."
    ),
    StoryText.CHAPTER_WHY: TextLimit(
        characters=400,
        hint="Why these changes belong together. What each piece does belongs in the reason of its step.",
    ),
    StoryText.CHAPTER_DOUBT: TextLimit(
        characters=300,
        hint="Where to look hardest in this chapter. The rest belongs in the reason of the step it is about.",
    ),
    StoryText.STEP_REASON: TextLimit(
        characters=400, hint="Why this piece is the way it is. If that takes more, tell it as two steps."
    ),
}


class ToldStep(Step):
    """A step as it is told: with the piece of its file it shows, cut out of the change."""

    piece: DiffFile


class LeftOut(BaseModel):
    """What a story leaves out of one file: changes no step tells, in a file nobody named as housekeeping.

    Shown all the same, beside the story: a story that could hide a change
    would be an advertisement for it.
    """

    model_config = ConfigDict(frozen=True)

    # The rows left out, each run of them that holds a change a hunk of its
    # own; the file as it is, when the change shows no line of it
    piece: DiffFile
    # How many lines of it the change added or removed
    changed_lines: int


class ToldStory(Story[ToldStep]):
    """A story on the change it is told of: every step with what it shows, and what no step tells."""

    left_out: list[LeftOut]
