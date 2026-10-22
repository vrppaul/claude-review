"""The ids the agent's threads take beside the ones the page holds, what the review says of those it cannot, and
what the agent has of each thread, which stays as the agent has it."""

import pytest
from structlog.typing import EventDict

from claude_review.domain.exceptions import HandedWordsChangedError
from claude_review.domain.models import (
    FIRST_ROUND,
    CommentSeverity,
    LineAnchor,
    ThreadDraft,
    TurnAuthor,
    TurnDraft,
)
from claude_review.services.review.reader_threads import ReaderThreads
from tests.helpers import FIRST_THREAD_ID, REVIEWED_FILE, REVIEWED_LINE, line_anchor

# What a thread hangs on, quoted, and the same lines once the diff lost them
ANCHOR = line_anchor(REVIEWED_FILE, 1, quote=[REVIEWED_LINE])
LOST = line_anchor(REVIEWED_FILE, 1, quote=[REVIEWED_LINE], outdated=True)
OPENING = "Why one?"
# The reader's reply the agent is handed with the thread, as it was and as it may come back
REPLY_ID = "turn-1"
REPLY = TurnDraft(turn_id=REPLY_ID, author=TurnAuthor.READER, body="Which caller?", images=[], round=FIRST_ROUND)
REPLY_REWORDED = TurnDraft(
    turn_id=REPLY_ID, author=TurnAuthor.READER, body="Which callers?", images=[], round=FIRST_ROUND
)
REPLY_BY_THE_AGENT = TurnDraft(
    turn_id=REPLY_ID, author=TurnAuthor.AUTHOR, body="Which caller?", images=[], round=FIRST_ROUND
)
# What the reader says in the thread after the agent was handed it
LATER = TurnDraft(turn_id="turn-2", author=TurnAuthor.READER, body="And the other?", images=[], round=FIRST_ROUND)


def _thread(
    *,
    body: str = OPENING,
    images: tuple[str, ...] = (),
    severity: CommentSeverity = CommentSeverity.NOTE,
    raised_by: TurnAuthor = TurnAuthor.READER,
    turns: tuple[TurnDraft, ...] = (REPLY,),
    resolved: bool = False,
    anchor: LineAnchor = ANCHOR,
) -> ThreadDraft:
    """The thread the agent is handed, with its reply, or that thread come back from the page changed."""
    return ThreadDraft(
        thread_id=FIRST_THREAD_ID,
        anchor=anchor,
        severity=severity,
        body=body,
        images=list(images),
        turns=list(turns),
        raised_by=raised_by,
        resolved=resolved,
    )


def test_threads_the_review_cannot_take_are_said_once_while_every_hello_carries_them(logged: list[EventDict]) -> None:
    """A hello comes as often as once a second while the reader types: what was left out is said as it changes."""
    threads = ReaderThreads()

    threads.hold([], [], unnamed_count=1)
    threads.hold([], [], unnamed_count=1)

    assert [entry["event"] for entry in logged] == ["threads_left_out"]


@pytest.mark.parametrize(
    "held_id", ["raised-²", "raised-٣", "raised-"], ids=["superscript", "arabic-indic", "no-number"]
)
def test_an_id_this_review_never_hands_out_does_not_move_its_numbering(held_id: str) -> None:
    """The review numbers its own in plain digits; anything else is a page's id, however it reads."""
    threads = ReaderThreads()
    threads.hold([], [held_id], unnamed_count=0)

    assert threads.raise_id() == "raised-1"


def test_what_the_agent_has_of_a_thread_only_grows_each_turn_as_first_handed() -> None:
    """A copy read later — older than the page's, or rewritten by a page at fault — takes nothing from it."""
    threads = ReaderThreads()
    threads.handed(_thread(), round_number=FIRST_ROUND)
    threads.handed(_thread(turns=(REPLY_REWORDED, LATER)), round_number=FIRST_ROUND)

    had = threads.handed(_thread(turns=()), round_number=FIRST_ROUND)

    assert [(turn.turn_id, turn.body) for turn in had.turns] == [(REPLY_ID, REPLY.body), (LATER.turn_id, LATER.body)]


def test_what_the_agent_has_of_a_thread_keeps_the_round_it_first_had_it_in() -> None:
    """Handed again in a later round, with what was said since, it still went to the agent in the first."""
    threads = ReaderThreads()
    threads.handed(_thread(), round_number=FIRST_ROUND)

    had = threads.handed(_thread(turns=(REPLY, LATER)), round_number=FIRST_ROUND + 1)

    assert had.round == FIRST_ROUND


def test_what_the_agent_has_of_a_thread_says_whether_it_was_last_handed_settled() -> None:
    """Settled, then opened again: the agent knows only what it was handed last, so a change since goes to it again."""
    threads = ReaderThreads()

    settled = threads.handed(_thread(resolved=True), round_number=FIRST_ROUND)
    opened_again = threads.handed(_thread(), round_number=FIRST_ROUND)

    assert (settled.resolved, opened_again.resolved) == (True, False)


@pytest.mark.parametrize(
    "changed",
    [
        _thread(body="Why two?"),
        _thread(images=("shot.png",)),
        _thread(severity=CommentSeverity.BLOCKER),
        _thread(raised_by=TurnAuthor.AUTHOR),
        _thread(turns=(REPLY_REWORDED,)),
        _thread(turns=()),
        _thread(turns=(REPLY_BY_THE_AGENT,)),
    ],
    ids=[
        "its opening reworded",
        "a screenshot added to its opening",
        "reweighed",
        "claimed by the agent",
        "a reply reworded",
        "a reply taken out",
        "a reply said by the agent",
    ],
)
def test_a_thread_coming_back_changed_in_what_the_agent_has_of_it_is_refused(changed: ThreadDraft) -> None:
    """The agent reads once: words it has would change under its answer, and it would never read them again."""
    threads = ReaderThreads()
    threads.handed(_thread(), round_number=FIRST_ROUND)

    with pytest.raises(HandedWordsChangedError):
        threads.check_handed([changed])


@pytest.mark.parametrize(
    "changed",
    [_thread(turns=(REPLY, LATER)), _thread(resolved=True), _thread(anchor=LOST)],
    ids=["a reply said since", "settled", "its lines lost"],
)
def test_a_thread_coming_back_with_what_the_agent_never_had_is_taken(changed: ThreadDraft) -> None:
    threads = ReaderThreads()
    threads.handed(_thread(), round_number=FIRST_ROUND)

    threads.check_handed([changed])


def test_the_agents_own_thread_coming_back_with_another_opening_is_refused() -> None:
    """The agent has what it raised a thread with from the moment it raised it."""
    threads = ReaderThreads()
    threads.raised(_thread(raised_by=TurnAuthor.AUTHOR, turns=()), round_number=FIRST_ROUND)

    with pytest.raises(HandedWordsChangedError):
        threads.check_handed([_thread(body="Rename it after all.", raised_by=TurnAuthor.AUTHOR, turns=())])
