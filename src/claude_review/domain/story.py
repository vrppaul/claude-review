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
(`ToldStory` of `ToldStep`s), and, followed onto each take of the change
after, the same story with each step as it stands there (`ToldStory` of
`FollowedStep`s). Each part makes its own told and followed forms, since it
is the part that knows what it says; only `services/story_telling.py`
decides that a story may be told, cuts what its steps show, and follows it.
"""

from enum import StrEnum, auto

from pydantic import BaseModel, ConfigDict

from claude_review.domain.models import DiffFile, EpochMillis, LineSpan, OverviewList, thread_may_name


class StoryPart(BaseModel):
    """What every part of a story is, as it is written and as it is told: made once, and never changed.

    What a story is held to — a limit, a fault found in it — is no part of
    it, and is not one of these.
    """

    model_config = ConfigDict(frozen=True)


class Step(StoryPart):
    """A piece of the change, and why it is the way it is.

    Its lines are numbered as the file now stands — as it stood, for a file
    the change left no line of. A step with no reason shows code that needs
    none.
    """

    # Any file the change touched: one whose name no thread could carry is
    # still told
    file: str
    lines: LineSpan
    reason: str | None = None

    def told(self, piece: DiffFile) -> ToldStep:
        """The step as it is told: everything it says, and the piece of its file it shows."""
        return ToldStep(file=self.file, lines=self.lines, reason=self.reason, piece=piece)


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

    def told(self, steps: list[ToldStep]) -> Chapter[ToldStep]:
        """The chapter as it is told: everything it says, with its steps as they are told in place of its own."""
        return Chapter[ToldStep](id=self.id, title=self.title, why=self.why, doubt=self.doubt, steps=steps)

    def followed(self, steps: list[FollowedStep]) -> Chapter[FollowedStep]:
        """The chapter on a take of the change: everything it says, with its steps as they stand there."""
        return Chapter[FollowedStep](id=self.id, title=self.title, why=self.why, doubt=self.doubt, steps=steps)


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

    def lists(self) -> dict[OverviewList, list[OverviewItem]]:
        """What the overview lists, each list by the name its field and a thread on its items go by."""
        return {
            OverviewList.DECISIONS: self.decisions,
            OverviewList.TURNED_DOWN: self.turned_down,
            OverviewList.LATER: self.later,
        }


class ToldFrom(StrEnum):
    """What the agent tells a story from.

    MEMORY — it made the change, and remembers why each piece is as it is.
    COMMITS — it reads the change back from its commits: a reconstruction of
    what somebody decided, and said to be one.
    """

    MEMORY = auto()
    COMMITS = auto()


class Story[StepKind: Step](StoryPart):
    """A change as the agent tells it, whole: a story is sent in one piece, and replaced in one piece."""

    title: str
    told_from: ToldFrom
    overview: StoryOverview
    chapters: list[Chapter[StepKind]]
    # Files that changed and have nothing to tell — a lock file, a changelog —
    # named so that what changed in them is not held against the story
    housekeeping: list[str]

    def told(self, chapters: list[Chapter[ToldStep]], left_out: list[LeftOut]) -> ToldStory[ToldStep]:
        """The story as it is told: everything it says, its chapters as they are told, and what no step tells."""
        return ToldStory[ToldStep](
            title=self.title,
            told_from=self.told_from,
            overview=self.overview,
            chapters=chapters,
            housekeeping=self.housekeeping,
            left_out=left_out,
        )


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
    """A step as it is told: with the piece of its file it shows, cut out of the change.

    What every take after the one it was told of follows it from: its piece
    is what it was told with.
    """

    piece: DiffFile

    def followed(self, now: StepNow | None) -> FollowedStep:
        """The step on a take of the change: everything it says, and where its code stands there, if anywhere."""
        return FollowedStep(file=self.file, lines=self.lines, reason=self.reason, now=now)


class StepNow(StoryPart):
    """Where a step's code stands on a take of the change: its lines there, the piece they are, and if it changed."""

    lines: LineSpan
    piece: DiffFile
    # Whether a round's work changed it after the step was told: its rows say something else than those told
    changed_since_told: bool


class FollowedStep(Step):
    """A step as it stands on a take of the change: as told, changed since, or not placed.

    It is known by the lines it was told on, which a round's work never
    moves: the page knows its section by them, and a thread on its reason
    its block. Where its code stands now is said beside them. A round's
    work may leave the review unable to say where that is: its file left
    the change, nothing of its lines is found, or it would meet another
    step of its file once followed. It then stands nowhere and claims no
    line, and shows no piece: a piece cut at its old lines would show other
    code, and an empty one would claim a status its file no longer has.
    Whether its code changed is said only of code it shows.
    """

    # None where its code is not in the change as it now stands
    now: StepNow | None

    @property
    def stands_as_told(self) -> bool:
        """Whether it shows the code it was told with: placed in the change, and not changed since."""
        return self.now is not None and not self.now.changed_since_told

    @property
    def commentable(self) -> bool:
        """Whether a thread may hang on what the step says: whether its file's path is one a thread may name."""
        return thread_may_name(self.file)


class LeftOut(StoryPart):
    """What a story leaves out of one file: changes no step tells, in a file nobody named as housekeeping.

    Shown all the same, beside the story: a story that could hide a change
    would be an advertisement for it.
    """

    # The rows left out, each run of them that holds a change a hunk of its
    # own; the file as it is, when the change shows no line of it
    piece: DiffFile
    # How many lines of it the change added or removed
    changed_lines: int


class ToldStory[StepKind: Step](Story[StepKind]):
    """A story on the change it is told of: every step with what it shows, and what no step tells.

    As it is told, each step a `ToldStep`; followed onto a take of the
    change, each a `FollowedStep`, as it stands there.
    """

    left_out: list[LeftOut]

    def followed(self, chapters: list[Chapter[FollowedStep]], left_out: list[LeftOut]) -> ToldStory[FollowedStep]:
        """The story on a take of the change: everything it says, its chapters as they stand there, what none tells."""
        return ToldStory[FollowedStep](
            title=self.title,
            told_from=self.told_from,
            overview=self.overview,
            chapters=chapters,
            housekeeping=self.housekeeping,
            left_out=left_out,
        )


class StoryAsking(BaseModel):
    """The reader asking the agent for a story, and how far that has got.

    Every fact a reader waiting for a story is shown: when they asked, when
    an agent took the request — None while none has — and whether they
    stopped it. It lasts until a story is told, which ends it.
    """

    model_config = ConfigDict(frozen=True)

    asked_at: EpochMillis
    taken_at: EpochMillis | None
    stopped: bool

    def taken(self, at: EpochMillis) -> StoryAsking:
        """The asking once an agent has taken the request, at this moment."""
        return StoryAsking(asked_at=self.asked_at, taken_at=at, stopped=self.stopped)

    def stopped_by_the_reader(self) -> StoryAsking:
        """The asking once the reader has stopped it: when it was asked and taken is still said."""
        return StoryAsking(asked_at=self.asked_at, taken_at=self.taken_at, stopped=True)
