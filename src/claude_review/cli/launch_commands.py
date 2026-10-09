"""The commands that open a review: of a diff, of files, of a conversation.

Each reads what it reviews its own way and hands it to the same launch,
which serves it until it ends and prints what it handed back.
"""

import asyncio
from collections.abc import Awaitable
from pathlib import Path

import click
import structlog

from claude_review.cli.openings import ReviewOpening, open_diff, open_files, open_transcript
from claude_review.cli.ports import ANY_FREE_PORT, HIGHEST_PORT
from claude_review.cli.serving import LaunchOptions, serve_review
from claude_review.domain.models import ReviewMode

log = structlog.get_logger()

# What each kind of review says when there is nothing in it to read
NOTHING_TO_REVIEW = {
    ReviewMode.DIFF: "No changes found.",
    ReviewMode.FILES: "No content to review.",
    ReviewMode.TRANSCRIPT: "No messages to review.",
}

# Every launch takes these two: where to serve, and whether to open a window
launch_port = click.option(
    "--port",
    type=click.IntRange(min=ANY_FREE_PORT, max=HIGHEST_PORT),
    default=None,
    help="Port to serve the review on; 0 for any free one. Omitted, it is worked out from what is reviewed, "
    "so reopening the same review comes back to the same address.",
)
no_open = click.option("--no-open", is_flag=True, help="Don't open the browser automatically.")


@click.command("diff")
@click.argument(
    "location", required=False, default=Path(), type=click.Path(exists=True, file_okay=False, path_type=Path)
)
@click.option(
    "--base", type=str, default=None, help="Compare against a specific commit (e.g., HEAD~3, abc123, v0.5.0)."
)
@launch_port
@no_open
def diff_command(location: Path, base: str | None, port: int | None, no_open: bool) -> None:
    """Review git changes.

    LOCATION is any directory in the repository, the current one by default:
    the review is of the whole repository whichever it is.
    """
    _launch(open_diff(location.resolve(), base), LaunchOptions(port=port, open_browser=not no_open))


@click.command("files")
@click.argument("paths", nargs=-1, required=True, type=click.Path(exists=True, path_type=Path))
@launch_port
@no_open
def files_command(paths: tuple[Path, ...], port: int | None, no_open: bool) -> None:
    """Review text files — plans, docs, configs, source code."""
    _launch(open_files([path.resolve() for path in paths]), LaunchOptions(port=port, open_browser=not no_open))


@click.command("transcript")
@click.argument("path", required=True, type=click.Path(exists=True, path_type=Path))
@launch_port
@no_open
def transcript_command(path: Path, port: int | None, no_open: bool) -> None:
    """Review a conversation transcript JSONL file."""
    _launch(open_transcript(path.resolve()), LaunchOptions(port=port, open_browser=not no_open))


def _launch(opening: Awaitable[ReviewOpening], options: LaunchOptions) -> None:
    """Open a review, hold it open until it ends, and print what it handed back."""
    handed_back = asyncio.run(_open_and_serve(opening, options))
    if handed_back:
        click.echo(handed_back)


async def _open_and_serve(opening: Awaitable[ReviewOpening], options: LaunchOptions) -> str:
    """Read what is to be reviewed, and serve it unless there is nothing in it."""
    opened = await opening
    if not opened.diff_files:
        click.echo(NOTHING_TO_REVIEW[opened.mode], err=True)
        return ""
    log.info("content_loaded", file_count=len(opened.diff_files), mode=opened.mode)
    return await serve_review(opened, options)


LAUNCH_COMMANDS = (diff_command, files_command, transcript_command)
