"""A story for the tests to check and to break: the one the design's canvas tells.

It is told of commit 9268258, "paste a screenshot into the panel or any
thread": the overview, and the two chapters the canvas tells in full, in the
canvas's own words. The limits a story is held to are measured against a
story somebody meant, not against filler.
"""

from collections.abc import Callable
from difflib import SequenceMatcher
from typing import override

from pydantic import BaseModel, ConfigDict, JsonValue

from claude_review.domain.exceptions import FieldPath
from claude_review.domain.models import (
    FIRST_LINE,
    FIRST_ROUND,
    FIRST_TAKE,
    NO_HUNK_HEADER,
    DiffFile,
    DiffHunk,
    DiffLine,
    FileStatus,
    LineSide,
    LineSpan,
    LineType,
)
from claude_review.domain.story import (
    Chapter,
    Diagram,
    FollowedStep,
    OverviewItem,
    Step,
    Story,
    StoryOverview,
    ToldFrom,
    ToldStory,
)
from claude_review.presentation.schemas.story import StoryRequest
from claude_review.services.anchor_service import side_lines
from claude_review.services.review.review_content import ReviewContent, TakesCompared
from claude_review.services.review.review_story import ReviewStory
from claude_review.services.story_telling import as_told
from tests.helpers import FixedClock, added_line, context_line, removed_line

# The chapters the canvas tells, by the ids the overview links to them by
PASTE_CHAPTER = "ch-1"
KEEPING_CHAPTER = "ch-2"

IMAGES_MODULE = "frontend/src/lib/utils/images.ts"
ROUTES = "src/claude_review/presentation/routes.py"
IMAGE_SERVICE = "src/claude_review/services/image_service.py"
IMAGE_STORE = "src/claude_review/repositories/image_store.py"

# How the image travels, drawn. The overview links the parts told here to their
# chapters; the last one's chapter is among those the canvas only names
DIAGRAM = """flowchart LR
  paste[Reader pastes] --> service[ImageService]
  service --> store[Image store]
  store --> agent[Agent opens it]"""


def canvas_story() -> Story[Step]:
    """The story the canvas tells: nothing in it keeps it from being told."""
    return Story[Step](
        title="Paste a screenshot into the panel or any thread",
        told_from=ToldFrom.MEMORY,
        overview=_overview(),
        chapters=[_paste_chapter(), _keeping_chapter()],
        housekeeping=["CHANGELOG.md", "uv.lock"],
    )


def told_as_written(story: Story[Step]) -> ToldStory[FollowedStep]:
    """A story as the review holds one once told, each step showing a piece with no rows: for a test of its words alone."""
    return as_told(
        story.told(
            [
                chapter.told([shown.told(changed_file(shown.file)) for shown in chapter.steps])
                for chapter in story.chapters
            ],
            [],
        )
    )


def planted(story: Story[Step], path: FieldPath, value: JsonValue) -> Story[Step]:
    """The story with one field of its document written anew: the field its path leads to, as the agent's JSON nests it."""
    document = story.model_dump()
    *way, field = path
    holder = document
    for part in way:
        holder = holder[part]
    holder[field] = value
    return Story[Step].model_validate(document)


def field_at(story: Story[Step], path: FieldPath) -> JsonValue:
    """What a path leads to in a story's document; a path that leads nowhere raises."""
    found = story.model_dump()
    for part in path:
        found = found[part]
    return found


def as_the_agent_writes(story: Story[Step]) -> dict[str, JsonValue]:
    """A story as its document says it: JSON, each step's lines written "104-129"."""
    return StoryRequest.from_domain(story).model_dump(mode="json")


def without_field(document: dict[str, JsonValue], field: str) -> dict[str, JsonValue]:
    """A document with one of its fields left out, as an agent that forgot it would write it."""
    left = dict(document)
    del left[field]
    return left


def _overview() -> StoryOverview:
    return StoryOverview(
        task="Let the reader paste a screenshot wherever they write, and get it to the agent as a file it can open.",
        done=(
            "Ctrl+V works in the panel and in every comment field. Each image is uploaded as it is pasted;"
            " the server keeps it by its bytes and hands the agent a path."
        ),
        doubt=(
            "An image pasted into a comment that is then closed unsent is dropped at once."
            " Reopen the draft and the image is gone."
        ),
        diagram=Diagram(
            mermaid=DIAGRAM,
            caption="How an image travels",
            links={"paste": PASTE_CHAPTER, "service": KEEPING_CHAPTER, "store": KEEPING_CHAPTER},
        ),
        decisions=[
            OverviewItem(
                text=(
                    "An image is known by its bytes, not by the type the upload claims,"
                    " so a file is served back as what it is."
                ),
                chapter=KEEPING_CHAPTER,
            ),
            OverviewItem(
                text=(
                    "The quota is reserved before the write is awaited:"
                    " two uploads at once cannot both slip under 200 MB."
                ),
                chapter=KEEPING_CHAPTER,
            ),
            OverviewItem(
                text=(
                    "No path is built from an id the reader sent."
                    " The store names the files; the service finds them in the ledger."
                ),
                chapter=KEEPING_CHAPTER,
            ),
        ],
        turned_down=[
            OverviewItem(
                text=(
                    "Base64 in the message. It would ride every round"
                    " and fill the agent's context with pixels it cannot read."
                )
            ),
            OverviewItem(
                text="An upload widget per field. The panel and the comments share one class and two components instead."
            ),
        ],
        later=[OverviewItem(text="Drag and drop. Only paste works."), OverviewItem(text="Images in transcript mode.")],
    )


def _paste_chapter() -> Chapter[Step]:
    return Chapter[Step](
        id=PASTE_CHAPTER,
        title="A paste reaches the server",
        why=(
            "An image goes to the server the moment it is pasted, not when the message is sent."
            " The reader sees what the agent will get while still writing,"
            " and the message carries ids instead of bytes."
        ),
        steps=[
            Step(
                file=IMAGES_MODULE,
                lines=LineSpan(first=30, last=47),
                reason=(
                    "The body is the image itself, not a form: there is one thing to send,"
                    " and a form would only wrap it. A refusal comes back in the server's own words."
                ),
            ),
            Step(
                file=ROUTES,
                lines=LineSpan(first=353, last=374),
                reason=(
                    "The route stops reading once the body passes 10 MB. Past the limit the answer is already"
                    " known, and the rest is never held. 413 means too big, 422 means not an image this review keeps."
                ),
            ),
        ],
    )


def _keeping_chapter() -> Chapter[Step]:
    return Chapter[Step](
        id=KEEPING_CHAPTER,
        title="The server keeps images by what they are",
        why=(
            "Policy sits in one service and the disk behind one protocol. The service decides what to keep;"
            " the store only writes and removes, under names it makes itself."
        ),
        doubt=(
            "The quota is reserved before the write is awaited. If the write then fails,"
            " the reservation must be given back. Step 2.3 does that; check it."
        ),
        steps=[
            Step(
                file=IMAGE_SERVICE,
                lines=LineSpan(first=68, last=92),
                reason=(
                    "A format is known by its first bytes, not by the type the upload claims."
                    " A file is served back as what it is, and a renamed PDF never passes for a PNG."
                ),
            ),
            Step(
                file=IMAGE_SERVICE,
                lines=LineSpan(first=102, last=130),
                reason=(
                    "Cheap checks first, the disk last. The quota is reserved before the write is awaited,"
                    " so an upload that arrives meanwhile is measured against it."
                ),
            ),
            Step(
                file=IMAGE_SERVICE,
                lines=LineSpan(first=131, last=141),
                reason=(
                    "Whatever stops the write gives the room back."
                    " BaseException on purpose: a cancelled upload must not keep its 10 MB."
                ),
            ),
            Step(
                file=IMAGE_STORE,
                lines=LineSpan(first=7, last=23),
                reason=(
                    "The store is the only code that touches the disk for images. Names come from the review,"
                    " never from the reader, so none can reach outside the directory."
                ),
            ),
        ],
    )


class RowKind(BaseModel):
    """A kind of row, as a test writes one: how its line is made, and what it counts for."""

    model_config = ConfigDict(frozen=True)

    # The line, given the number the row would have on each side
    line: Callable[[int, int], DiffLine]
    # How many lines it is on the old side and on the new, and how many the change added or removed in it
    old_lines: int
    new_lines: int
    changes: int


def _kept(old_number: int, new_number: int) -> DiffLine:
    return context_line(old_number, new_number, f" {old_number}/{new_number}")


def _added(_old_number: int, new_number: int) -> DiffLine:
    return added_line(new_number, f"+/{new_number}")


def _removed(old_number: int, _new_number: int) -> DiffLine:
    return removed_line(old_number, f"-{old_number}/")


# How a row of a hunk is written in a test, by its sign: a space for a line the change kept, and git's
# own signs for the rest. Every line says its sign and its numbers, so a test reads which row it holds.
ROWS = {
    " ": RowKind(line=_kept, old_lines=1, new_lines=1, changes=0),
    "+": RowKind(line=_added, old_lines=0, new_lines=1, changes=1),
    "-": RowKind(line=_removed, old_lines=1, new_lines=0, changes=1),
}
# The sign each kind of line is written by
SIGNS = {LineType.CONTEXT: " ", LineType.ADD: "+", LineType.DELETE: "-"}
# The one chapter of a story a test tells of a change of its own
ONLY_CHAPTER = "ch-1"


def hunk(old_start: int, new_start: int, signs: str) -> DiffHunk:
    """A hunk whose rows are written by their signs, numbered on each side from where the hunk starts there."""
    lines: list[DiffLine] = []
    old_number, new_number = old_start, new_start
    for sign in signs:
        row = ROWS[sign]
        lines.append(row.line(old_number, new_number))
        old_number += row.old_lines
        new_number += row.new_lines
    return DiffHunk(header=NO_HUNK_HEADER, old_start=old_start, new_start=new_start, lines=lines)


def signs_of(lines: list[DiffLine]) -> str:
    """The signs these rows are written by, in order."""
    return "".join(SIGNS[line.kind] for line in lines)


def changed_in(lines: list[DiffLine]) -> int:
    """How many of these rows the change added or removed."""
    return sum(ROWS[sign].changes for sign in signs_of(lines))


def lines_of(file: DiffFile) -> list[DiffLine]:
    """Every row of a file, hunk after hunk."""
    return [line for shown in file.hunks for line in shown.lines]


def changed_file(path: str, *hunks: DiffHunk, status: FileStatus = FileStatus.MODIFIED) -> DiffFile:
    """A file of a change, with the hunks it shows."""
    return DiffFile(path=path, status=status, hunks=list(hunks))


def _kept_between(before: list[str], _after: list[str], told: range, now: range) -> list[DiffLine]:
    """Lines a block difflib found alike says on both sides: rows kept, numbered on each side."""
    return [context_line(old + FIRST_LINE, new + FIRST_LINE, before[old]) for old, new in zip(told, now, strict=True)]


def _changed_between(before: list[str], after: list[str], told: range, now: range) -> list[DiffLine]:
    """Lines a block difflib found changed: the ones it took out, then the ones it put in their place."""
    return [
        *(removed_line(old + FIRST_LINE, before[old]) for old in told),
        *(added_line(new + FIRST_LINE, after[new]) for new in now),
    ]


# How each kind of block difflib finds between two lists of lines is written as rows of a diff
BLOCK_ROWS: dict[str, Callable[[list[str], list[str], range, range], list[DiffLine]]] = {
    "equal": _kept_between,
    "replace": _changed_between,
    "delete": _changed_between,
    "insert": _changed_between,
}


def diff_of(path: str, before: list[str], after: list[str]) -> DiffFile:
    """What a diff says changed in a file from these lines to those, as one hunk that shows every line."""
    blocks = SequenceMatcher(a=before, b=after, autojunk=False).get_opcodes()
    rows = [
        row
        for kind, told_start, told_stop, now_start, now_stop in blocks
        for row in BLOCK_ROWS[kind](before, after, range(told_start, told_stop), range(now_start, now_stop))
    ]
    return changed_file(path, DiffHunk(header=NO_HUNK_HEADER, old_start=FIRST_LINE, new_start=FIRST_LINE, lines=rows))


def rows_of(file: DiffFile) -> list[str]:
    """What every row of a file says, hunk after hunk."""
    return [line.content for line in lines_of(file)]


def step(file: str, first: int, last: int) -> Step:
    """A step told of lines of a file, with no reason given."""
    return Step(file=file, lines=LineSpan(first=first, last=last))


def chapter_of(chapter_id: str, *steps: Step) -> Chapter[Step]:
    """A chapter that tells these steps, with nothing wrong in what it says."""
    return Chapter[Step](
        id=chapter_id, title="The change", why="It belongs together.", doubt="Look hardest here.", steps=list(steps)
    )


def story_of_chapters(
    *chapters: Chapter[Step], housekeeping: tuple[str, ...] = (), told_from: ToldFrom = ToldFrom.MEMORY
) -> Story[Step]:
    """A story that tells these chapters, from memory unless it says otherwise, with nothing wrong in what it says."""
    return Story[Step](
        title="A change",
        told_from=told_from,
        overview=StoryOverview(task="Change it.", done="It is changed.", decisions=[], turned_down=[], later=[]),
        chapters=list(chapters),
        housekeeping=list(housekeeping),
    )


def story_of(*steps: Step, housekeeping: tuple[str, ...] = ()) -> Story[Step]:
    """A story of one chapter that tells these steps, with nothing wrong in what it says."""
    return story_of_chapters(chapter_of(ONLY_CHAPTER, *steps), housekeeping=housekeeping)


# A file the change added two lines to, a story that tells the first of them, and how a round's work may leave
# the file: a third line added, the first rewritten, or the second taken out
STORIED = "src/storied.py"
TOLD_OF = [changed_file(STORIED, hunk(1, 1, "++"))]
ONE_MORE_LEFT_OUT = [changed_file(STORIED, hunk(1, 1, "+++"))]
FIRST_REWRITTEN = [changed_file(STORIED, hunk(1, 1, "-++"))]
NOTHING_LEFT_OUT = [changed_file(STORIED, hunk(1, 1, "+"))]
THE_FIRST_LINE = story_of(step(STORIED, 1, 1))
# The round the diff is taken again in, once the first was sent
SECOND_ROUND = FIRST_ROUND + 1
# The moment the review's clock says, whenever a story's asking asks it
ASKED_AT = 1_791_000_000_000


# What a take of a change is written down as, by the take's number
TREE_OF_TAKE = "tree of take {take}"


def tree_of(take: int) -> str:
    return TREE_OF_TAKE.format(take=take)


def take_of(files: list[DiffFile], take: int) -> ReviewContent:
    """A take of a change, by its number, written down as a tree of its own."""
    return ReviewContent(files, frozenset(), take=take, written_as=tree_of(take))


def _lines_of_each_file(files: list[DiffFile]) -> dict[str, list[str]]:
    """What each file of a take says: the lines its hunks show on their new side."""
    return {file.path: [line.content for line in side_lines(file, LineSide.NEW)] for file in files}


def between_takes(earlier: list[DiffFile], later: list[DiffFile]) -> list[DiffFile]:
    """What changed in each file from one take to another, as a diff of the lines each take shows of it says.

    A file a take does not hold says nothing in it.
    """
    before, after = _lines_of_each_file(earlier), _lines_of_each_file(later)
    return [diff_of(path, before.get(path, []), after.get(path, [])) for path in dict.fromkeys([*before, *after])]


class TakesComparedByTheirLines(TakesCompared):
    """Takes of a change by the trees they were written down as, compared by the lines each shows of its files."""

    def __init__(self, takes: dict[str, list[DiffFile]]) -> None:
        self._takes = takes

    @override
    async def changed_between(self, earlier: str, later: str) -> list[DiffFile]:
        return between_takes(self._takes[earlier], self._takes[later])


# What a story that is never followed onto a take is built with: no take to compare
NO_TAKES = TakesComparedByTheirLines({})
# Whether the reader wants a story of every change: they turned stories on, or left them off
STORIES_ON = True
STORIES_OFF = False


async def told_then_followed(*takes: list[DiffFile]) -> ReviewStory:
    """The story of the first line told of the first take of a change, then followed onto each take after it.

    Each later take is taken in a round of its own: the second, then the third, and so on.
    """
    numbered = dict(enumerate(takes, start=FIRST_TAKE))
    compared = TakesComparedByTheirLines({tree_of(take): files for take, files in numbered.items()})
    story = ReviewStory(FixedClock(ASKED_AT), takes=compared, takes_a_story=True)
    [told_of, *after] = [take_of(files, take) for take, files in numbered.items()]
    await story.tell(THE_FIRST_LINE, told_of, round_number=FIRST_ROUND)
    for round_number, change in enumerate(after, start=SECOND_ROUND):
        await story.follow(change, round_number=round_number, stories_on=STORIES_OFF)
    return story


def review_story(takes: TakesCompared) -> ReviewStory:
    """The story of a review of a change, on the clock the asking for one is dated by."""
    return ReviewStory(FixedClock(ASKED_AT), takes=takes, takes_a_story=True)


def story_of_no_change() -> ReviewStory:
    """The story of a review of files read once, or of a conversation: there is no change to tell one of."""
    return ReviewStory(FixedClock(ASKED_AT), takes=NO_TAKES, takes_a_story=False)
