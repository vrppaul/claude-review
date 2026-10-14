"""A change long enough to look at, and a story told of it: what `look.py` serves.

Most of what a look is for shows only on a long review: a reading area that
scrolls for screens, a glide from one chapter to another, the bar that says
which chapter is read, contents longer than their column. So the change is
thirty files changed in four places each, far apart, ten files added whole,
and a note: forty-one files. The story tells it in six chapters and
twenty-nine steps: chapters of one step and of ten, steps with a reason and
without one, a chapter with a doubt, and most of the changed files told by
no step at all, so the story has its part for what is left out. Its
overview draws the change, wider than a narrow column, nodes leading to
chapters.

Data alone: the files as they are committed and as the change leaves them,
and the story as the document the review's `story` command takes. Nothing
here is written to a disk or handed to the review; `look.py` does both.
"""

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict

# How many files the change touches, and how long each is
MODIFIED_FILES = 30
ADDED_FILES = 10
LINES_OF_A_MODIFIED_FILE = 200
LINES_OF_AN_ADDED_FILE = 150
# A file no step of the story tells, which the story names as housekeeping
NOTES = "notes.txt"

FROZEN = ConfigDict(frozen=True)


class LineRun(BaseModel):
    """Lines of a file that follow one another, from the first to the last of them."""

    model_config = FROZEN

    first: int
    last: int

    def numbers(self) -> range:
        return range(self.first, self.last + 1)

    def written(self) -> str:
        """The run as a step of a story writes its lines."""
        return f"{self.first}-{self.last}"


class StoryStep(BaseModel):
    """A piece of the change as a story's document tells it, and why it is the way it is."""

    model_config = FROZEN

    file: str
    lines: str
    reason: str | None


class Chapter(BaseModel):
    """Changes that belong together, as a story's document tells them."""

    model_config = FROZEN

    id: str
    title: str
    why: str
    doubt: str | None
    steps: list[StoryStep]


class Decision(BaseModel):
    """A decision the overview lists, and the chapter that shows it."""

    model_config = FROZEN

    text: str
    chapter: str


class Diagram(BaseModel):
    """The change drawn, in Mermaid, and the chapter each node leads to, by the node's name."""

    model_config = FROZEN

    mermaid: str
    caption: str
    links: dict[str, str]


class Overview(BaseModel):
    """The change in short."""

    model_config = FROZEN

    task: str
    done: str
    doubt: str
    diagram: Diagram
    decisions: list[Decision]


class Story(BaseModel):
    """The document the review's `story` command takes."""

    model_config = FROZEN

    title: str
    told_from: str
    overview: Overview
    chapters: list[Chapter]
    housekeeping: list[str]


# Where a modified file changes: its head, a second place, and two more further down
THE_HEAD = LineRun(first=10, last=12)
THE_SECOND_PLACE = LineRun(first=60, last=62)
CHANGED_PLACES = (THE_HEAD, THE_SECOND_PLACE, LineRun(first=120, last=122), LineRun(first=180, last=182))
# An added file whole, and its two halves
ADDED_WHOLE = LineRun(first=1, last=LINES_OF_AN_ADDED_FILE)
ITS_FIRST_HALF = LineRun(first=1, last=75)
ITS_SECOND_HALF = LineRun(first=76, last=LINES_OF_AN_ADDED_FILE)


def _modified(number: int) -> str:
    return f"src/mod_{number:02}.py"


def _added(number: int) -> str:
    return f"src/new_{number:02}.py"


def _numbered(path: str, count: int, changed: Sequence[LineRun]) -> str:
    """A file of numbered lines, those of the runs given said to be changed."""
    words = {number: f"{path} line {number}" for number in range(1, count + 1)}
    words.update({number: f"{path} line {number}, changed" for run in changed for number in run.numbers()})
    return "".join(f"{line}\n" for line in words.values())


def _told(file: str, lines: LineRun, reason: str | None) -> StoryStep:
    return StoryStep(file=file, lines=lines.written(), reason=reason)


# The repository as it is committed, by each file's path
COMMITTED = {
    **{
        _modified(number): _numbered(_modified(number), LINES_OF_A_MODIFIED_FILE, ())
        for number in range(MODIFIED_FILES)
    },
    NOTES: "a note\n",
}
# What the change leaves in the working tree: every committed file changed, and the added ones not yet known to git
CHANGED = {
    **{
        _modified(number): _numbered(_modified(number), LINES_OF_A_MODIFIED_FILE, CHANGED_PLACES)
        for number in range(MODIFIED_FILES)
    },
    **{_added(number): _numbered(_added(number), LINES_OF_AN_ADDED_FILE, ()) for number in range(ADDED_FILES)},
    NOTES: "another note\n",
}

# The story of the change. A chapter's title is sixty characters at most: the review refuses a longer one
THE_STORY = Story(
    title="A long change, told in six chapters",
    told_from="memory",
    overview=Overview(
        task="Change many files in a few places each, and add ten.",
        done="Thirty files changed in four places each; ten files added.",
        doubt="The last chapter tells one line of a file changed in four places.",
        # Wider than a narrow column, with its heart marked, a node that leads nowhere, and one whose name
        # begins another's
        diagram=Diagram(
            mermaid=(
                "flowchart LR\n"
                "  added[Ten files added] --> heads[Heads changed]:::heart\n"
                "  heads --> heads-2[Ten more heads] --> last[One line more] --> notes[A note]"
            ),
            caption="How the change runs",
            links={"added": "ch-1", "heads": "ch-2", "heads-2": "ch-4", "last": "ch-6"},
        ),
        decisions=[Decision(text="The added files come before the changed ones.", chapter="ch-2")],
    ),
    chapters=[
        Chapter(
            id="ch-1",
            title="The first file added, and the first changed",
            why="The beginning of the change: one file added whole, and two places of one changed.",
            doubt=None,
            steps=[
                _told(_added(0), ADDED_WHOLE, "The whole of the first added file."),
                _told(_modified(0), THE_HEAD, "The first place the first file changed."),
                _told(_modified(0), THE_SECOND_PLACE, "The second place."),
            ],
        ),
        Chapter(
            id="ch-2",
            title="Five files changed at their heads, half of an added one",
            why="Each of these changes its first place the same way.",
            doubt="Whether the five are the same change.",
            steps=[
                *(_told(_modified(number), THE_HEAD, f"The head of file {number}.") for number in range(1, 6)),
                _told(_added(1), ITS_FIRST_HALF, "The first half of the second added file."),
            ],
        ),
        Chapter(
            id="ch-3",
            title="The rest of the added file, and three more",
            why="What chapter two began.",
            doubt=None,
            steps=[
                _told(_added(1), ITS_SECOND_HALF, "The second half."),
                *(_told(_added(number), ADDED_WHOLE, f"Added file {number}.") for number in range(2, 5)),
            ],
        ),
        Chapter(
            id="ch-4",
            title="Ten heads",
            why="Ten files, one place each.",
            doubt=None,
            steps=[_told(_modified(number), THE_HEAD, None) for number in range(6, 16)],
        ),
        Chapter(
            id="ch-5",
            title="Five files added whole",
            why="The long chapter.",
            doubt=None,
            steps=[_told(_added(number), ADDED_WHOLE, f"Added file {number}, whole.") for number in range(5, 10)],
        ),
        Chapter(
            id="ch-6",
            title="One line more",
            why="The end.",
            doubt=None,
            steps=[_told(_modified(16), THE_HEAD, "The last step of the story.")],
        ),
    ],
    housekeeping=[NOTES],
)
