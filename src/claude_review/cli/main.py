"""The command line: `claude-review <command>`.

Two kinds of command hang off it. Those that open a review — `diff`,
`files`, `transcript` — serve it until it ends. The rest are what its agent
runs against a review already open, by the port it is served on, many times
a minute; so each command is loaded only when it is run or listed, and an
agent's command never loads the server.
"""

import importlib
import logging
import sys
from typing import Any

import click
import structlog

from claude_review.cli.review_client import ReviewCallError
from claude_review.domain.protocols import GitError
from claude_review.hosting.errors import PortUnavailableError, ServerStartError
from claude_review.services.unreadable_content import UnreadableContentError

LAUNCH_COMMANDS_MODULE = "claude_review.cli.launch_commands"
AGENT_COMMANDS_MODULE = "claude_review.cli.agent_commands"
# Which module each command lives in, as its `COMMANDS` table names it
COMMAND_MODULES = {
    **dict.fromkeys(("diff", "files", "transcript"), LAUNCH_COMMANDS_MODULE),
    **dict.fromkeys(
        ("wait", "reply", "catch-up", "say", "progress", "show", "point", "status", "retake"), AGENT_COMMANDS_MODULE
    ),
}

# What goes wrong in ordinary use, and is said in a line rather than a
# traceback: no review on that port or a refusal from it, a directory that
# is no repository, a file that is not text, a port taken, a server that
# never came up
EXPLAINED_FAILURES = (ReviewCallError, GitError, UnreadableContentError, PortUnavailableError, ServerStartError)


class ReviewCommands(click.Group):
    """The commands, loaded as they are needed, failing in one line when the failure is an ordinary one.

    Anything not explained here is a fault in this program, and keeps its
    traceback so it can be found. A value an agent's command was typed with
    that the review would refuse is refused as it is parsed (`parameters.py`),
    before anything is called.
    """

    def list_commands(self, ctx: click.Context) -> list[str]:
        return sorted(COMMAND_MODULES)

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        module = COMMAND_MODULES.get(cmd_name)
        return None if module is None else importlib.import_module(module).COMMANDS[cmd_name]

    def invoke(self, ctx: click.Context) -> Any:
        try:
            return super().invoke(ctx)
        except EXPLAINED_FAILURES as failure:
            raise click.ClickException(str(failure)) from failure


@click.group(cls=ReviewCommands)
@click.version_option(package_name="claude-review")
@click.option("--verbose", is_flag=True, help="Enable diagnostic logging to stderr.")
def main(verbose: bool) -> None:
    """Browser-based code review tool for Claude Code."""
    _configure_logging(verbose=verbose)


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
