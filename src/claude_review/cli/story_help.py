"""What `claude-review story --help` says under its options: a story's document, whole, and how long its texts may be.

An agent asked for a story has to learn how one is written, and learns it
in one place: this help. The skill names the command and no number, and the
event that asks for a story carries nothing. So the help shows a document
with every part a story may have, and lists the length each kind of text is
held to with where the rest belongs, as the review says them when it
refuses one.

All of it is read off what the review itself holds. The example is a
`StoryRequest` written here in code, so the type checker holds its fields
to the model the review reads a document with, and a test holds it to
being a story the review finds no fault in. What a story may be told from
is every value of `ToldFrom`. What a chapter's id may hold is said in the
words the review refuses one in. The lengths are the rows of
`TEXT_LIMITS`, the one table of them.

Not said here, for want of anything to read it off: which field of the
document each kind of text stands in, and what else the review refuses a
story for. Both live in the code of `services/story_checks.py`, a path
built at each check, and a list of them here would be a second copy.

What makes a story good is read off nothing: it is advice, in prose, kept
in `good_story.md` beside this module and shown line by line as written.
It ships with the command that checks a story, so whichever way the skill
was installed, the agent reads the advice of the version it writes for.
"""

from pathlib import Path

from claude_review.domain.models import CHAPTER_ID_RULE, LineSpan
from claude_review.domain.story import TEXT_LIMITS, StoryText, TextLimit, ToldFrom
from claude_review.presentation.schemas.story import (
    ChapterInput,
    DiagramInput,
    OverviewItemInput,
    StepInput,
    StoryOverviewInput,
    StoryRequest,
)

# The chapters of the example, by the ids its overview and its diagram lead to them by
ARRIVING = "paste-arrives"
KEPT = "images-kept"
HANDED_OVER = "agent-gets-path"
# The one file the example tells in several steps
IMAGE_SERVICE = "src/claude_review/services/image_service.py"

# A story with every part one may have, told as good_story.md asks: the change that let a reader paste a
# screenshot, its tests in the chapter of what they hold
EXAMPLE = StoryRequest(
    title="Paste a screenshot into the panel or any comment",
    told_from=ToldFrom.MEMORY,
    overview=StoryOverviewInput(
        task="Let the reader paste a screenshot wherever they write, and get it to the agent as a file it can open.",
        done=(
            "Ctrl+V works in the panel and in every comment field. Each image is sent as it is pasted; the review"
            " keeps it by its bytes and hands the agent a path."
        ),
        doubt=(
            "An image pasted into a comment that is then closed unsent is dropped at once: reopen the draft and the"
            " image is gone."
        ),
        diagram=DiagramInput(
            # The node at the heart of the change marked with mermaid's own class, which the page edges in the
            # agent's colour
            mermaid=(
                "flowchart LR\n"
                "  paste[Reader pastes] --> service[Image service]:::heart\n"
                "  service --> store[Image store]\n"
                "  store --> agent[Agent opens the file]"
            ),
            caption="The way an image takes",
            links={"paste": ARRIVING, "service": KEPT, "store": KEPT, "agent": HANDED_OVER},
        ),
        decisions=[
            OverviewItemInput(
                text="An image is known by its bytes, not by the type the upload claims, so it is served back as what"
                " it is.",
                chapter=KEPT,
            ),
            OverviewItemInput(
                text="The room an image takes is reserved before it is written, so two uploads at once cannot both"
                " slip under the cap.",
                chapter=KEPT,
            ),
        ],
        turned_down=[
            OverviewItemInput(
                text="The image inside the comment's text: it would ride every round and fill the agent's context with"
                " pixels it cannot read.",
                chapter=HANDED_OVER,
            )
        ],
        later=[OverviewItemInput(text="Dragging a file in: only a paste works.", chapter=ARRIVING)],
    ),
    chapters=[
        ChapterInput(
            id=ARRIVING,
            title="A paste reaches the review",
            why=(
                "An image goes to the review the moment it is pasted, not when the comment is sent: the reader sees"
                " what the agent will get while still writing, and the comment carries an id, not the bytes."
            ),
            doubt="Several images pasted at once: only the first is read.",
            steps=[
                StepInput(
                    file="frontend/src/lib/utils/images.ts",
                    lines=LineSpan(first=30, last=47),
                    reason="The body is the image itself, not a form: there is one thing to send, and a form would"
                    " only wrap it.",
                ),
                StepInput(
                    file="src/claude_review/presentation/routes.py",
                    lines=LineSpan(first=353, last=374),
                    reason="The route stops reading once the body passes 10 MB: past the limit the answer is known,"
                    " and the rest is never held.",
                ),
            ],
        ),
        ChapterInput(
            id=KEPT,
            title="The review keeps an image by what it is",
            why=(
                "One service decides what is kept and one store touches the disk: the service checks and counts, the"
                " store only writes and removes, under names it makes itself."
            ),
            doubt="The room is reserved before the write, so a write that fails must give it back: step 2.3 does.",
            steps=[
                StepInput(
                    file=IMAGE_SERVICE,
                    lines=LineSpan(first=68, last=92),
                    reason="A format is known by its first bytes, not by the type the upload claims: a renamed PDF"
                    " never passes for a PNG.",
                ),
                StepInput(
                    file=IMAGE_SERVICE,
                    lines=LineSpan(first=102, last=130),
                    reason="Cheap checks first, the disk last. The room is reserved before the write is awaited, so"
                    " an upload arriving meanwhile is measured against it.",
                ),
                StepInput(
                    file=IMAGE_SERVICE,
                    lines=LineSpan(first=131, last=141),
                    reason="Whatever stops the write gives the room back: BaseException on purpose, so a cancelled"
                    " upload does not keep its 10 MB.",
                ),
                StepInput(
                    file="tests/unit/test_image_service.py",
                    lines=LineSpan(first=1, last=58),
                    reason="New tests: a renamed PDF is refused, an image over the cap is refused unread, a failed"
                    " write gives its room back. No assertion that was there changed.",
                ),
            ],
        ),
        ChapterInput(
            id=HANDED_OVER,
            title="The agent gets a path it can open",
            why="The agent reads files, not pixels in a message: a round names each image by the path it is kept at.",
            doubt=(
                "An image stays on disk after its comment is sent, since the agent may still open it: nothing"
                " removes it before the review ends."
            ),
            steps=[
                StepInput(
                    file="src/claude_review/services/thread_markdown.py",
                    lines=LineSpan(first=12, last=35),
                    reason="An image is said as an Image: line under its comment, the form the skill tells the agent"
                    " to open.",
                )
            ],
        ),
    ],
    housekeeping=["uv.lock"],
)

# How deep the example's document is set in, a level at a time
DOCUMENT_INDENT = 2
# What parts the words of a kind of text in its name, and what stands between them where the help says it
BETWEEN_WORDS_OF_A_NAME = "_"
BETWEEN_WORDS_SAID = " "
# What stands between the columns of a limit's line
BETWEEN_COLUMNS = "  "
# What click reads before a paragraph as: leave its lines as they are written
AS_WRITTEN = "\b"
BETWEEN_PARAGRAPHS = "\n\n"

# What the help says before the example, after it, and before the limits
BEFORE_THE_EXAMPLE = (
    "The document, shown with every part a story may have. A step's lines are numbered as its file now stands: "
    "as it stood, for a file the change left no line of."
)
TOLD_FROM_IS_ONE_OF = '"told_from" is one of: {told_from}.'
BETWEEN_VALUES = ", "
BEFORE_THE_LIMITS = (
    "A story is told in short texts. The most characters each kind may hold, and where the rest belongs:"
)

# What makes a story good, for the agent about to tell one, and how its file is written
GOOD_STORY = Path(__file__).with_name("good_story.md")
GOOD_STORY_ENCODING = "utf-8"


def _said(kind: StoryText) -> str:
    """A kind of text as the help calls it: in words."""
    return kind.replace(BETWEEN_WORDS_OF_A_NAME, BETWEEN_WORDS_SAID)


def _limit_line(kind: StoryText, limit: TextLimit, name_width: int, count_width: int) -> str:
    """One kind of text, how many characters it may hold, and where the rest belongs, in columns."""
    return BETWEEN_COLUMNS.join([_said(kind).ljust(name_width), str(limit.characters).rjust(count_width), limit.hint])


def _limit_lines() -> list[str]:
    """A line for every kind of text a story is told in, its columns as wide as the widest name and count."""
    name_width = max(len(_said(kind)) for kind in TEXT_LIMITS)
    count_width = max(len(str(limit.characters)) for limit in TEXT_LIMITS.values())
    return [_limit_line(kind, limit, name_width, count_width) for kind, limit in TEXT_LIMITS.items()]


def _as_written(lines: list[str]) -> str:
    """Lines click prints one under another as they are, where it would fill a paragraph of them to the width."""
    return "\n".join([AS_WRITTEN, *lines])


def _paragraphs_as_written(text: str) -> list[str]:
    """A text's paragraphs, each printed as its lines are written: its headings and lists keep their shape."""
    return [_as_written(paragraph.splitlines()) for paragraph in text.strip().split(BETWEEN_PARAGRAPHS)]


def story_document_help() -> str:
    """What the help of `story` says of the document.

    An example with every part a story may have; what it may be told from, every value of
    `ToldFrom`; what a chapter's id may hold; the length each kind of text is held to; then
    what makes a story good.
    """
    example = EXAMPLE.model_dump_json(indent=DOCUMENT_INDENT)
    return BETWEEN_PARAGRAPHS.join(
        [
            BEFORE_THE_EXAMPLE,
            _as_written(example.splitlines()),
            TOLD_FROM_IS_ONE_OF.format(told_from=BETWEEN_VALUES.join(ToldFrom)),
            CHAPTER_ID_RULE,
            BEFORE_THE_LIMITS,
            _as_written(_limit_lines()),
            *_paragraphs_as_written(GOOD_STORY.read_text(encoding=GOOD_STORY_ENCODING)),
        ]
    )
