"""What a review started from the command line tells the terminal it was started in."""

import asyncio
import webbrowser
from pathlib import Path
from typing import override

import click
import structlog

from claude_review.hosting.announcer import ReviewAnnouncer

log = structlog.get_logger()

# How the review says where it is, on stderr: whoever started it in the
# background reads the address from this line
READY_ANNOUNCEMENT = "Review ready at "


class TerminalAnnouncer(ReviewAnnouncer):
    """Says on stderr where the review is and what it left behind, and opens the review if asked."""

    def __init__(self, *, open_browser: bool) -> None:
        self._open_browser = open_browser

    @override
    async def listening_at(self, url: str) -> None:
        """Say where the review is, and open it if asked.

        Said either way. Opening a window and saying where the review is are
        two different jobs, and tying them together meant that anything
        starting a review for somebody else had to refuse the window to learn
        the address — so nobody's browser ever opened.
        """
        click.echo(f"{READY_ANNOUNCEMENT}{url}", err=True)
        if self._open_browser:
            await asyncio.to_thread(_open_browser, url)

    @override
    def images_left_in(self, directory: Path) -> None:
        click.echo(
            f"Images pasted in this review stay in {directory} until the system clears its temporary files.", err=True
        )


def _open_browser(url: str) -> None:
    """Open the review, and let it go if there is nothing to open it with.

    A machine with no browser — over ssh, in a container, in CI — must not
    lose its review over the attempt. The address has already been printed,
    which is the way in either way.
    """
    try:
        webbrowser.open_new(url)
    except webbrowser.Error:
        log.info("no_browser", url=url)
