"""What has been said in the agent panel, both halves, kept so whoever arrives later can catch up.

The reader's page remembers the conversation it saw across a reload; a page
opened in another browser, or before anything was said, saw none of it, and
the agent may be a different process by then and remembers nothing. The
review saw both halves go past, so it is the one that can say what was
already discussed.
"""

import uuid

from claude_review.domain.interfaces import Clock
from claude_review.domain.models import FilePath, SaidInPanel, TurnAuthor

# What the ids the review gives the agent's words begin with. Unique rather
# than counted: a page's draft outlives the review it was kept from, and the
# next review of the same files must not name its words as the last one did.
AGENT_WORDS_PREFIX = "answer-"


class Conversation:
    """The panel's conversation, in the order it was said, each part dated and known by an id every page shares."""

    def __init__(self, clock: Clock) -> None:
        self._clock = clock
        self._said: list[SaidInPanel] = []

    @property
    def said(self) -> list[SaidInPanel]:
        """Everything said so far, oldest first; a copy, so nothing outside changes what was said."""
        return list(self._said)

    def reader_said(self, *, message_id: str, body: str, images: list[str], threads: list[str]) -> None:
        """Keep a message the reader sent, known by the id its page gave it."""
        self._said.append(
            SaidInPanel(
                said_id=message_id,
                message_id=message_id,
                author=TurnAuthor.READER,
                body=body,
                at=self._clock.now(),
                images=images,
                threads=threads,
                files=[],
                taken_back=False,
            )
        )

    def agent_said(self, *, message_id: str | None, body: str, files: list[FilePath]) -> str:
        """Keep what the agent said, and say the id every page is to know it by."""
        said_id = f"{AGENT_WORDS_PREFIX}{uuid.uuid4().hex}"
        self._said.append(
            SaidInPanel(
                said_id=said_id,
                message_id=message_id,
                author=TurnAuthor.AUTHOR,
                body=body,
                at=self._clock.now(),
                images=[],
                threads=[],
                files=files,
                taken_back=False,
            )
        )
        return said_id

    def taken_back(self, message_id: str) -> None:
        """Mark a message the reader took back. A question taken back in a thread names none here, and marks nothing."""
        self._said = [
            said.model_copy(update={"taken_back": True}) if said.said_id == message_id else said for said in self._said
        ]
