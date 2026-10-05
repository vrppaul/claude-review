"""How a thread is written out for the agent, in both review formats."""

from pathlib import Path

from claude_review.domain.models import Turn, TurnAuthor

# The agent reading this wrote the change, so its own turns are addressed to
# it as "You"
TURN_LABELS = {TurnAuthor.AUTHOR: "You", TurnAuthor.READER: "Reviewer"}


def format_opening(body: str, images: list[Path]) -> str:
    """What the comment that opened a thread said, as written, with its screenshots."""
    return "\n".join(part for part in (body, *image_lines(images)) if part)


def format_turn(turn: Turn) -> str:
    """Quote a turn under the comment it belongs to, named by its author.

    A blockquote keeps the conversation apart from the comment that opened
    it, so the instruction and the discussion of it do not read as one
    paragraph.
    """
    label = f"> **{TURN_LABELS[turn.author]}:**"
    lines = [*turn.body.splitlines(), *image_lines(turn.images)]
    if len(lines) == 1:
        return f"{label} {lines[0]}"
    # A quoted block needs the marker on every line, blank ones included
    quoted = "\n".join(f"> {line}" if line else ">" for line in lines)
    return f"{label}\n{quoted}"


def image_lines(images: list[Path]) -> list[str]:
    """Name each screenshot as a file the agent can open."""
    return [f"Image: {path}" for path in images]
