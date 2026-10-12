"""A story for the tests to check and to break: the one the design's canvas tells.

It is told of commit 9268258, "paste a screenshot into the panel or any
thread": the overview, and the two chapters the canvas tells in full, in the
canvas's own words. The limits a story is held to are measured against a
story somebody meant, not against filler.
"""

from collections.abc import Callable

from pydantic import BaseModel, ConfigDict, JsonValue

from claude_review.domain.models import NO_HUNK_HEADER, DiffFile, DiffHunk, DiffLine, FileStatus, LineType
from claude_review.domain.story import (
    Chapter,
    Diagram,
    FieldPath,
    OverviewItem,
    Step,
    StepLines,
    Story,
    StoryOverview,
)
from tests.helpers import added_line, context_line, removed_line

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
        overview=_overview(),
        chapters=[_paste_chapter(), _keeping_chapter()],
        housekeeping=["CHANGELOG.md", "uv.lock"],
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
                lines=StepLines(first=30, last=47),
                reason=(
                    "The body is the image itself, not a form: there is one thing to send,"
                    " and a form would only wrap it. A refusal comes back in the server's own words."
                ),
            ),
            Step(
                file=ROUTES,
                lines=StepLines(first=353, last=374),
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
                lines=StepLines(first=68, last=92),
                reason=(
                    "A format is known by its first bytes, not by the type the upload claims."
                    " A file is served back as what it is, and a renamed PDF never passes for a PNG."
                ),
            ),
            Step(
                file=IMAGE_SERVICE,
                lines=StepLines(first=102, last=130),
                reason=(
                    "Cheap checks first, the disk last. The quota is reserved before the write is awaited,"
                    " so an upload that arrives meanwhile is measured against it."
                ),
            ),
            Step(
                file=IMAGE_SERVICE,
                lines=StepLines(first=131, last=141),
                reason=(
                    "Whatever stops the write gives the room back."
                    " BaseException on purpose: a cancelled upload must not keep its 10 MB."
                ),
            ),
            Step(
                file=IMAGE_STORE,
                lines=StepLines(first=7, last=23),
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


def rows_of(file: DiffFile) -> list[str]:
    """What every row of a file says, hunk after hunk."""
    return [line.content for line in lines_of(file)]


def step(file: str, first: int, last: int) -> Step:
    """A step told of lines of a file, with no reason given."""
    return Step(file=file, lines=StepLines(first=first, last=last))


def story_of(*steps: Step, housekeeping: tuple[str, ...] = ()) -> Story[Step]:
    """A story of one chapter that tells these steps, with nothing wrong in what it says."""
    return Story[Step](
        title="A change",
        overview=StoryOverview(task="Change it.", done="It is changed.", decisions=[], turned_down=[], later=[]),
        chapters=[
            Chapter[Step](
                id=ONLY_CHAPTER,
                title="The change",
                why="It belongs together.",
                doubt="Look hardest here.",
                steps=list(steps),
            )
        ],
        housekeeping=list(housekeeping),
    )
