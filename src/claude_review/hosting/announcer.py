"""What a review hosted on this machine tells whoever started it.

Hosting decides when there is something to tell; whoever started the review
decides how it is told — a line on a terminal, a window opened, a note a
test reads.
"""

from abc import ABC, abstractmethod
from pathlib import Path


class ReviewAnnouncer(ABC):
    """Whoever started a review, told what they need to know of it."""

    @abstractmethod
    async def listening_at(self, url: str) -> None:
        """The review is up, and this is where it is."""

    @abstractmethod
    def images_left_in(self, directory: Path) -> None:
        """The review has ended, and the images pasted into it stay here for the agent to open."""

    @abstractmethod
    def never_opened(self) -> None:
        """The review has ended with no page ever opening it: nobody came to it."""
