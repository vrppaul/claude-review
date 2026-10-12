"""What crosses the wire carries everything the review's own model has, field for field.

The wire's models are built from the review's by their fields, so a field
added to one and not the other would be dropped, or filled with a default,
without a word. The same holds wherever one thing is written twice: an event
and the push a page reads for it, a thread as the page sends it and as the
review holds it, a hello as the page says it and as the server hears it.
Each pair is held to the same fields here.
"""

from typing import get_args

import pytest
from pydantic import BaseModel

from claude_review.domain import models, page_events
from claude_review.presentation.wire import agent, content, pushes, records, threads

# What a push carries of its own: the kind the page tells it apart by
PUSH_KIND = frozenset({"type"})

# Each thing the review tells its pages, and the push a page reads for it
EVENTS_AND_PUSHES: list[tuple[type[BaseModel], type[BaseModel], frozenset[str]]] = [
    (page_events.ThreadAnswered, pushes.ReplyPush, PUSH_KIND),
    (page_events.AnswererChanged, pushes.AnswererPush, PUSH_KIND),
    (page_events.AgentSaid, pushes.ChatPush, PUSH_KIND),
    (page_events.WorkReported, pushes.ProgressPush, PUSH_KIND),
    (page_events.FileShown, pushes.ShowPush, PUSH_KIND),
    (page_events.StatusReported, pushes.StatusPush, PUSH_KIND),
    (page_events.ThreadRaised, pushes.PointPush, PUSH_KIND),
    (page_events.TreeMoved, pushes.ChangedPush, PUSH_KIND),
    (page_events.RoundBegan, pushes.RoundPush, PUSH_KIND),
    (page_events.DiffRetaken, pushes.DiffPush, PUSH_KIND),
    (page_events.ReviewEnded, pushes.EndedPush, PUSH_KIND),
]

# Pairs of the review's model and the wire's, with what the wire adds of its own
TWINS: list[tuple[type[BaseModel], type[BaseModel], frozenset[str]]] = [
    (models.DiffLine, content.DiffLine, frozenset()),
    (models.DiffHunk, content.DiffHunk, frozenset()),
    # Whether a thread may name it, which the review's model answers from its path rather than keeps
    (models.DiffFile, content.DiffFile, frozenset({"commentable"})),
    (models.LineAnchor, threads.LineAnchor, frozenset()),
    (models.Turn, threads.Turn, frozenset()),
    # The place a thread hangs on, in plain words
    (models.Thread, threads.Thread, frozenset({"where"})),
    (models.AgentStatus, agent.AgentStatus, frozenset()),
    (models.ProgressStep, agent.ProgressStep, frozenset()),
    (models.AgentWork, agent.AgentWork, frozenset()),
    (models.ThreadQuestion, agent.ThreadQuestion, frozenset()),
    (models.PanelMessage, agent.PanelMessage, frozenset()),
    (models.PanelCancel, agent.PanelCancel, frozenset()),
    (models.PanelEntry, agent.PanelEntry, frozenset()),
    (models.SaidInPanel, agent.SaidInPanel, frozenset()),
    (models.RoundSubmission, agent.RoundSubmission, frozenset()),
    (models.ReaderSettings, records.ReaderSettings, frozenset()),
    (models.GuideState, records.GuideState, frozenset()),
    # A thread as the page holds it, sent back with whatever is about it
    (models.ThreadDraft, threads.ThreadInput, frozenset()),
    (models.TurnDraft, threads.TurnInput, frozenset()),
    *EVENTS_AND_PUSHES,
    # A hello as the server hears it, and as the page says it
    (threads.ReceivedHello, threads.SessionHello, frozenset()),
]


@pytest.mark.parametrize(("review_model", "wire_model", "wire_only"), TWINS, ids=[pair[1].__name__ for pair in TWINS])
def test_the_wire_carries_every_field_of_the_reviews_own_model(
    review_model: type[BaseModel], wire_model: type[BaseModel], wire_only: frozenset[str]
) -> None:
    assert set(wire_model.model_fields) == set(review_model.model_fields) | wire_only


def test_every_event_the_review_tells_its_pages_is_held_to_its_push() -> None:
    """An event added without its pair here would be held to nothing."""
    assert {event for event, _, _ in EVENTS_AND_PUSHES} == set(get_args(page_events.PageEvent.__value__))
