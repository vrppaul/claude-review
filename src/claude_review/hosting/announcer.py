"""What a review hosted on this machine tells whoever started it.

Hosting decides when there is something to tell; whoever started the review
decides how it is told — a line on a terminal, a window opened, a note a
test reads.
"""

from pathlib import Path
from typing import Protocol


class ReviewAnnouncer(Protocol):
    """Whoever started a review, told what they need to know of it."""

    async def listening_at(self, url: str) -> None:
        """The review is up, and this is where it is."""
        ...

    def images_left_in(self, directory: Path) -> None:
        """The review has ended, and the images pasted into it stay here for the agent to open."""
        ...
