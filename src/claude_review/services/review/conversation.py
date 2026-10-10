"""What has been said in the agent panel, both halves, kept so an agent arriving later can catch up.

The reader's page remembers the whole conversation across a reload; the
agent may be a different process by then and remembers nothing. The review
saw both halves go past, so it is the one that can say what was already
discussed.
"""

from pathlib import Path

from claude_review.domain.interfaces import Clock
from claude_review.domain.models import PanelEntry, TurnAuthor


class Conversation:
    """The panel's conversation, in the order it was said, each part dated."""

    def __init__(self, clock: Clock) -> None:
        self._clock = clock
        self._entries: list[PanelEntry] = []

    @property
    def entries(self) -> list[PanelEntry]:
        """Everything said so far, oldest first; a copy, so nothing outside changes what was said."""
        return list(self._entries)

    def reader_said(self, *, message_id: str, body: str, images: list[Path]) -> None:
        self._entries.append(
            PanelEntry(message_id=message_id, author=TurnAuthor.READER, body=body, at=self._clock.now(), images=images)
        )

    def agent_said(self, *, message_id: str | None, body: str) -> None:
        self._entries.append(
            PanelEntry(message_id=message_id, author=TurnAuthor.AUTHOR, body=body, at=self._clock.now())
        )
