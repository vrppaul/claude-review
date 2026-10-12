"""A story for the tests to check and to break: the one the design's canvas tells.

It is told of commit 9268258, "paste a screenshot into the panel or any
thread": the overview, and the two chapters the canvas tells in full, in the
canvas's own words. The limits a story is held to are measured against a
story somebody meant, not against filler.
"""

from pydantic import JsonValue

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


def canvas_story() -> Story:
    """The story the canvas tells: nothing in it keeps it from being told."""
    return Story(
        title="Paste a screenshot into the panel or any thread",
        overview=_overview(),
        chapters=[_paste_chapter(), _keeping_chapter()],
        housekeeping=["CHANGELOG.md", "uv.lock"],
    )


def planted(story: Story, path: FieldPath, value: JsonValue) -> Story:
    """The story with one field of its document written anew: the field its path leads to, as the agent's JSON nests it."""
    document = story.model_dump()
    *way, field = path
    holder = document
    for part in way:
        holder = holder[part]
    holder[field] = value
    return Story.model_validate(document)


def field_at(story: Story, path: FieldPath) -> JsonValue:
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


def _paste_chapter() -> Chapter:
    return Chapter(
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


def _keeping_chapter() -> Chapter:
    return Chapter(
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
