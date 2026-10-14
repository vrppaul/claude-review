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
being a story the review finds no fault in. Which parts may be left out is
shown, not listed: a second document holds the least a story may be, held
the same two ways, and what it lacks of the first may be left out. What a
story may be told from is every value of `ToldFrom`. The lengths are the
rows of `TEXT_LIMITS`, the one table of them.

Not said here, for want of anything to read it off: which field of the
document each kind of text stands in, and what else the review refuses a
story for. Both live in the code of `services/story_checks.py`, a path
built at each check, and a list of them here would be a second copy.
"""

from claude_review.domain.models import LineSpan
from claude_review.domain.story import TEXT_LIMITS, StoryText, TextLimit, ToldFrom
from claude_review.presentation.wire.story import (
    ChapterInput,
    DiagramInput,
    OverviewItemInput,
    StepInput,
    StoryOverviewInput,
    StoryRequest,
)

# The chapters of the example, by the ids its overview and its diagram lead to them by
PASTING = "ch-1"
KEEPING = "ch-2"

# A story with every part one may have, told of a change small enough to read at a glance
EXAMPLE = StoryRequest(
    title="Paste a screenshot into a comment",
    told_from=ToldFrom.MEMORY,
    overview=StoryOverviewInput(
        task="Let the reader paste a screenshot into a comment.",
        done="A pasted image goes to the review, which keeps it. The comment shows it and names it to the agent.",
        doubt="Whether an image is checked before it is kept, or only its size.",
        diagram=DiagramInput(
            mermaid="flowchart LR\n  paste[Reader pastes] --> store[Image store]",
            caption="The way an image takes",
            links={"paste": PASTING, "store": KEEPING},
        ),
        decisions=[OverviewItemInput(text="Images are kept on disk, never in the draft.", chapter=KEEPING)],
        turned_down=[OverviewItemInput(text="Sending the image inside the comment's own text.", chapter=PASTING)],
        later=[OverviewItemInput(text="Dragging a file in, as well as pasting one.", chapter=PASTING)],
    ),
    chapters=[
        ChapterInput(
            id=PASTING,
            title="A paste reaches the review",
            why="The field and the request change together: one without the other pastes nothing.",
            doubt="A paste of several images at once: only the first is read.",
            steps=[
                StepInput(
                    file="frontend/src/lib/components/CommentBox.svelte",
                    lines=LineSpan(first=88, last=104),
                    reason="The field takes the paste itself, so an image never becomes text in it.",
                )
            ],
        ),
        ChapterInput(
            id=KEEPING,
            title="The review keeps the image",
            why="Whatever is kept is checked first, in one place, before the disk is touched.",
            doubt="The check of what kind of file it is reads the first bytes alone.",
            steps=[
                StepInput(
                    file="src/claude_review/services/image_service.py",
                    lines=LineSpan(first=1, last=42),
                    reason="Cheap checks come first and the disk last: an image too large is refused unread.",
                )
            ],
        ),
    ],
    housekeeping=["uv.lock"],
)

# The least a story may be: every part it holds is one no story does without. What the example has and
# this lacks may be left out, which the two documents show without a list of parts written beside the models
LEAST = StoryRequest(
    title="Paste a screenshot into a comment",
    told_from=ToldFrom.MEMORY,
    overview=StoryOverviewInput(
        task="Let the reader paste a screenshot into a comment.",
        done="A pasted image goes to the review, which keeps it.",
    ),
    chapters=[
        ChapterInput(
            id=PASTING,
            title="A paste reaches the review",
            why="The field and the request change together: one without the other pastes nothing.",
            steps=[StepInput(file="frontend/src/lib/components/CommentBox.svelte", lines=LineSpan(first=88, last=104))],
        )
    ],
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

# What the help says before the example, and before the limits
BEFORE_THE_EXAMPLE = (
    "The document, shown with every part a story may have. A step's lines are numbered as its file now stands: "
    "as it stood, for a file the change left no line of."
)
BEFORE_THE_LEAST = (
    "The least a story may be. Whatever the document above has and this one lacks may be left out. "
    '"told_from" is one of: {told_from}.'
)
BETWEEN_VALUES = ", "
BEFORE_THE_LIMITS = (
    "A story is told in short texts. The most characters each kind may hold, and where the rest belongs:"
)


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


def story_document_help() -> str:
    """What the help of `story` says of the document.

    An example with every part a story may have; the least a story may be, with what it may be
    told from, every value of `ToldFrom`; then the length each kind of text is held to.
    """
    example = EXAMPLE.model_dump_json(indent=DOCUMENT_INDENT)
    least = LEAST.model_dump_json(indent=DOCUMENT_INDENT, exclude_defaults=True)
    return BETWEEN_PARAGRAPHS.join(
        [
            BEFORE_THE_EXAMPLE,
            _as_written(example.splitlines()),
            BEFORE_THE_LEAST.format(told_from=BETWEEN_VALUES.join(ToldFrom)),
            _as_written(least.splitlines()),
            BEFORE_THE_LIMITS,
            _as_written(_limit_lines()),
        ]
    )
