"""The commands an agent runs against a review already open: listening, answering, showing.

Each names the review by its port and makes one call, so an agent drives
them from a loop of its own and reads and writes code between them.
"""

import click

from claude_review.cli.parameters import (
    BRANCHES,
    FILE,
    ID,
    NAMED_FILES,
    SAID,
    STATUS,
    STEP,
    STORY,
    THREAD_LINES,
    WORK,
    ThreadLines,
)
from claude_review.cli.rendering import render_catch_up, render_story_taken, render_thread
from claude_review.cli.review_client import EVENTS, ReviewClient
from claude_review.cli.story_help import story_document_help
from claude_review.cli.terminal_text import terminal_text
from claude_review.domain.models import CommentSeverity, LineSide, says_nothing
from claude_review.hosting.ports import HIGHEST_PORT, LOWEST_PORT
from claude_review.presentation.wire.agent import (
    MAX_PROGRESS_STEPS,
    ProgressRequest,
    ProgressStep,
    ReplyRequest,
    SayRequest,
    ShowRequest,
    StatusRequest,
    TimeoutEvent,
)
from claude_review.presentation.wire.base import DEFAULT_WAIT_SECONDS, MAX_WAIT_SECONDS
from claude_review.presentation.wire.story import StoryRequest
from claude_review.presentation.wire.threads import LineAnchor, PointRequest
from claude_review.services.place_words import LINES_EXAMPLE

# How a refusal lists the steps both --did and --step name
STEPS_SEPARATOR = ", "


def _client_for(_context: click.Context, _parameter: click.Parameter, port: int) -> ReviewClient:
    """The review a command calls, from the port it is served on."""
    return ReviewClient(port)


# Every command here calls one review, named by its port
review_port = click.option(
    "--port",
    "client",
    required=True,
    type=click.IntRange(min=LOWEST_PORT, max=HIGHEST_PORT),
    callback=_client_for,
    help="Port the review is served on.",
)


@click.command("wait")
@review_port
@click.option(
    "--seconds",
    default=DEFAULT_WAIT_SECONDS,
    type=click.FloatRange(min=0, min_open=True, max=MAX_WAIT_SECONDS),
    help="How long to wait before reporting that nothing was asked.",
)
@click.option(
    "--until-event",
    is_flag=True,
    help="Wait on through every timeout: print only what the reader hands over, or that the review closed.",
)
def wait_command(*, client: ReviewClient, seconds: float, until_event: bool) -> None:
    """Wait for whatever the reader hands over next.

    Prints one JSON object and exits, so a caller can loop: a "question"
    about a thread, answered with `claude-review reply`; a "message" from
    the agent panel, answered with `claude-review say`; a "round" of the
    review; a "cancel" taking a message back; a "story_request" asking for a
    story of the change, answered with `claude-review story`, its "stale"
    saying what a round moved on of a story told before; a
    "story_cancel" stopping the story asked for; "timeout" if nothing was
    said, or "closed" once the review is over. With --until-event a timeout
    is never printed: the command waits on until something else happens.
    """
    event = client.next_event(seconds)
    while until_event and isinstance(event, TimeoutEvent):
        event = client.next_event(seconds)
    click.echo(terminal_text(EVENTS.dump_json(event).decode()))


@click.command("reply")
@review_port
@click.option("--thread", required=True, type=ID, help="Thread the answer belongs to.")
@click.option(
    "--question",
    type=ID,
    default=None,
    help="Question being answered, from the event. Omitted, the oldest one still waiting takes it.",
)
@click.argument("body", required=True, type=SAID)
def reply_command(*, client: ReviewClient, thread: str, question: str | None, body: str) -> None:
    """Answer a question the reader asked about a comment thread.

    A thread can have several questions waiting at once, so naming the one
    being answered is what puts the answer under it rather than under the
    oldest one still waiting. BODY given as - is read from stdin.
    """
    client.reply(ReplyRequest(thread_id=thread, question_id=question, body=body))


@click.command("catch-up")
@review_port
@click.option("--thread", type=ID, default=None, help="One thread, in full, rather than the index.")
@click.option("--json", "as_json", is_flag=True, help="The whole thing as JSON, for a program to read.")
def catch_up_command(*, client: ReviewClient, thread: str | None, as_json: bool) -> None:
    """Catch up on a review already under way.

    `wait` hands over what happens next, never what already happened, so an
    agent that restarted mid-review knows nothing: not the round, not the
    threads, not what was discussed in the panel. This says all three.

    It prints an index — a line per thread, the panel in short — because
    handing over the whole review unasked would cost more than the work.
    Name a thread to get that one in full.
    """
    if thread is not None:
        read = client.thread(thread)
        printed = read.model_dump_json() if as_json else render_thread(read)
    else:
        seen = client.catch_up()
        printed = seen.model_dump_json() if as_json else render_catch_up(seen)
    click.echo(terminal_text(printed))


@click.command("say")
@review_port
@click.option(
    "--message",
    type=ID,
    default=None,
    help="Message being answered, from the event. Omitted, this is you speaking first.",
)
@click.option(
    "--file",
    "files",
    type=FILE,
    multiple=True,
    callback=NAMED_FILES,
    help="A file worth opening at what you said. Repeatable; each becomes a chip the reader can jump by.",
)
@click.argument("body", required=True, type=SAID)
def say_command(*, client: ReviewClient, message: str | None, files: tuple[str, ...], body: str) -> None:
    """Say something in the agent panel.

    The panel is where the review is discussed rather than any one line of
    it. Naming the message is what puts an answer under it: several can be
    waiting, and the reader is still reading while you write. Name nothing
    and you are speaking first — worth doing when you have finished
    something they are waiting on. BODY given as - is read from stdin.
    """
    client.say(SayRequest(message_id=message, body=body, files=list(files)))


@click.command("progress")
@review_port
@click.option("--message", type=ID, default=None, help="Message being worked on, from the event.")
@click.option(
    "--file", "files", type=FILE, multiple=True, callback=NAMED_FILES, help="A file being worked on. Repeatable."
)
@click.option(
    "--step",
    "steps",
    type=STEP,
    multiple=True,
    callback=BRANCHES,
    help="Something under way — a check, a subagent. Repeatable.",
)
@click.option(
    "--did", "finished", type=STEP, multiple=True, callback=BRANCHES, help="A step already finished. Repeatable."
)
@click.option("--done", is_flag=True, help="Take the line away: the work is finished. Sent on its own.")
@click.argument("text", required=False, type=WORK, default="")
def progress_command(
    *,
    client: ReviewClient,
    message: str | None,
    files: tuple[str, ...],
    steps: tuple[str, ...],
    finished: tuple[str, ...],
    done: bool,
    text: str,
) -> None:
    """Say what you are doing, while you are doing it.

    Waiting says only that something is happening; this says what. The text
    is the work itself; --did and --step are what it has branched into, and
    they are drawn hanging off it, so three subagents read as three branches
    rather than as a sentence about three subagents.

    Send it again to change it — it replaces what was showing rather than
    adding to it, because it is the state of the work and not a log of it.
    Send it with --done, or answer, and the whole thing goes away. TEXT
    given as - is read from stdin.
    """
    if done:
        if message is not None or files or steps or finished or text:
            msg = "--done takes the work line away and says nothing more: send it on its own"
            raise click.UsageError(msg)
        # Empty, which is what says the work is over
        client.report_progress(ProgressRequest())
        return
    # The review shows the work by what it says and what it has branched into;
    # given neither, it would take the line away, which only --done says
    if says_nothing(text) and not steps and not finished:
        msg = "nothing to show: say what you are doing, or what it has branched into — or send --done on its own"
        raise click.UsageError(msg)
    client.report_progress(
        ProgressRequest(
            message_id=message, text=text, files=list(files), steps=_branches(finished=finished, under_way=steps)
        )
    )


def _branches(*, finished: tuple[str, ...], under_way: tuple[str, ...]) -> list[ProgressStep]:
    """The branches of the work, those finished first, as the review takes them.

    Each option is read on its own as it is parsed; what only the two
    together can break is read here.

    Raises:
        click.UsageError: if a step is said to be both finished and under
            way, or the two name more steps than the review shows.
    """
    both = [step for step in under_way if step in finished]
    if both:
        msg = f"--did and --step both name {STEPS_SEPARATOR.join(both)}: a step is either finished or under way"
        raise click.UsageError(msg)
    branches = [
        *(ProgressStep(text=step, done=True) for step in finished),
        *(ProgressStep(text=step, done=False) for step in under_way),
    ]
    if len(branches) > MAX_PROGRESS_STEPS:
        msg = f"--did and --step together name at most {MAX_PROGRESS_STEPS} steps, not {len(branches)}"
        raise click.UsageError(msg)
    return branches


@click.command("show")
@review_port
@click.option("--file", "path", required=True, type=FILE, help="File to bring into view, as the diff names it.")
def show_command(*, client: ReviewClient, path: str) -> None:
    """Take the reader to a file, and mark it for a moment when they arrive.

    This moves somebody else's screen, so send it only when they asked to be
    taken somewhere. To offer a jump rather than make one, hang the file off
    what you say instead: `say --file <path>`.
    """
    client.show(ShowRequest(file=path))


@click.command("point")
@review_port
@click.option("--file", "path", required=True, type=FILE, help="File the thread hangs on, as the diff names it.")
@click.option("--lines", required=True, type=THREAD_LINES, help=f"Line or range it is about, e.g. {LINES_EXAMPLE}.")
@click.option(
    "--side",
    type=click.Choice(LineSide, case_sensitive=False),
    default=LineSide.NEW,
    help="Which version of the file: the new one, or the lines the change removed.",
)
@click.option(
    "--severity",
    type=click.Choice(CommentSeverity, case_sensitive=False),
    default=CommentSeverity.NOTE,
    help="How it is meant to be taken.",
)
@click.argument("body", required=True, type=SAID)
def point_command(
    *, client: ReviewClient, path: str, lines: ThreadLines, side: LineSide, severity: CommentSeverity, body: str
) -> None:
    """Raise a thread on a line of the review, from this side.

    For what belongs on the code rather than in the panel: where you did
    something other than what was asked, and why. The reader reads it as an
    ordinary thread — answers it, settles it, removes it — but it is drawn
    as yours, and it is not counted as their unsent work. Prints the id the
    thread was given. BODY given as - is read from stdin.
    """
    anchor = LineAnchor(file=path, side=side, start_line=lines.first, end_line=lines.last)
    raised = client.point(PointRequest(anchor=anchor, body=body, severity=severity))
    click.echo(raised.model_dump_json())


@click.command("status")
@review_port
@click.option("--model", type=STATUS, default=None, help="Which model is answering.")
@click.option(
    "--context",
    type=STATUS,
    default=None,
    help='How much of the context window is spent, in your own words (e.g. "53% of 1M").',
)
def status_command(*, client: ReviewClient, model: str | None, context: str | None) -> None:
    """Say what only this side can know, for the panel to show.

    The review can measure what handing it over costs, because it holds the
    diff. It cannot see into another process, so the model and the context
    are quoted from here, with the time they were said beside them. Say
    nothing and the panel shows nothing rather than a number that is a guess.
    """
    if model is None and context is None:
        msg = "nothing to report — pass --model, --context, or both"
        raise click.UsageError(msg)
    client.report_status(StatusRequest(model=model, context=context))


@click.command("retake")
@review_port
def retake_command(*, client: ReviewClient) -> None:
    """Take the diff again, after making the changes a round asked for.

    The reviews on screen reload it, keeping their threads: a comment whose
    lines survived follows them, and one whose lines are gone is marked
    outdated rather than pointing at whatever moved into their place. Prints
    which files changed since the round began. A diff review only: files and
    conversations have no diff to take again.
    """
    click.echo(terminal_text(client.retake().model_dump_json()))


@click.command("story", epilog=story_document_help())
@review_port
@click.option(
    "--file", "story", required=True, type=STORY, help='The story, as a JSON document. Given as "-", read from stdin.'
)
def story_command(*, client: ReviewClient, story: StoryRequest) -> None:
    """Tell the change as a story, for the reader to read it by.

    The document is the whole story: what was asked and done and what to
    doubt, then chapters, each a run of steps — a piece of the change, and
    why it is the way it is. It takes the place of any story told before:
    there is no patching one, so send it again whole. This help shows one
    below, and how long each of its texts may be.

    Refused, it comes back with everything wrong at once, each fault at its
    field of the document. Taken, it prints what its steps left out of the
    change, which the reader is shown beside the story all the same.
    """
    click.echo(terminal_text(render_story_taken(client.tell_story(story))))


COMMANDS = {
    command.name: command
    for command in (
        wait_command,
        reply_command,
        catch_up_command,
        say_command,
        progress_command,
        show_command,
        point_command,
        status_command,
        retake_command,
        story_command,
    )
}
