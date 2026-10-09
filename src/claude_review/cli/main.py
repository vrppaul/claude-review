"""The command line: `claude-review <command>`.

Two kinds of command hang off it. Those that open a review — `diff`,
`files`, `transcript` — serve it until it ends. The rest are what its agent
runs against a review already open, by the port it is served on.
"""

import logging
import sys
from typing import Any

import click
import structlog
from pydantic import ValidationError

from claude_review.cli.agent_commands import AGENT_COMMANDS
from claude_review.cli.launch_commands import LAUNCH_COMMANDS
from claude_review.cli.review_client import FieldRefusal, ReviewCallError, fields_said_wrong
from claude_review.cli.review_server import ServerStartError
from claude_review.domain.exceptions import GitError, PortUnavailableError, UnreadableContentError

# What goes wrong in ordinary use, and is said in a line rather than a
# traceback: no review on that port or a refusal from it, a directory that
# is no repository, a file that is not text, a port taken, a server that
# never came up
EXPLAINED_FAILURES = (ReviewCallError, GitError, UnreadableContentError, PortUnavailableError, ServerStartError)


class ReviewCommands(click.Group):
    """The commands, failing the way a command line should: one line on stderr, never a traceback.

    Anything not explained here is a fault in this program, and keeps its
    traceback so it can be found.
    """

    def invoke(self, ctx: click.Context) -> Any:
        try:
            return super().invoke(ctx)
        except EXPLAINED_FAILURES as failure:
            raise click.ClickException(str(failure)) from failure
        except ValidationError as invalid:
            # A request a command could not even build, from what it was given
            refusals = [FieldRefusal.model_validate(detail) for detail in invalid.errors()]
            msg = f"the review would refuse this: {fields_said_wrong(refusals)}"
            raise click.ClickException(msg) from invalid


@click.group(cls=ReviewCommands)
@click.version_option(package_name="claude-review")
@click.option("--verbose", is_flag=True, help="Enable diagnostic logging to stderr.")
def main(verbose: bool) -> None:
    """Browser-based code review tool for Claude Code."""
    _configure_logging(verbose=verbose)


for command in (*LAUNCH_COMMANDS, *AGENT_COMMANDS):
    main.add_command(command)


def _configure_logging(*, verbose: bool) -> None:
    """Silent by default; with --verbose, everything the review logs goes to stderr."""
    level = logging.INFO if verbose else logging.CRITICAL
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(level),
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
    )
