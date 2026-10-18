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

from claude_review.domain import models, page_events, story as told
from claude_review.presentation.wire import agent, content, pushes, records, story, threads

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
    (page_events.StoryTold, pushes.StoryPush, PUSH_KIND),
    (page_events.StoryAskingChanged, pushes.StoryAskingPush, PUSH_KIND),
    (page_events.ReviewEnded, pushes.EndedPush, PUSH_KIND),
]

# Pairs of the review's model and the wire's, with what the wire adds of its own
TWINS: list[tuple[type[BaseModel], type[BaseModel], frozenset[str]]] = [
    (models.DiffLine, content.DiffLine, frozenset()),
    (models.DiffHunk, content.DiffHunk, frozenset()),
    # Whether a thread may name it, which the review's model answers from its path rather than keeps
    (models.DiffFile, content.DiffFile, frozenset({"commentable"})),
    (models.LineAnchor, threads.LineAnchor, frozenset()),
    (models.StoryAnchor, threads.StoryAnchor, frozenset()),
    (models.OverviewBlock, threads.OverviewBlock, frozenset()),
    (models.ItemBlock, threads.ItemBlock, frozenset()),
    (models.ChapterBlock, threads.ChapterBlock, frozenset()),
    (models.ReasonBlock, threads.ReasonBlock, frozenset()),
    (models.Turn, threads.Turn, frozenset()),
    # The place a thread hangs on, in plain words: worked out from its anchor, and written out with it
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
    # A request for a story, as the agent takes it: the kind of event it is, and what went stale
    (models.StoryRequested, agent.StoryRequestEvent, frozenset({"type"})),
    (models.StoryWentStale, agent.StoryWentStale, frozenset()),
    (models.StaleStep, agent.StaleStep, frozenset()),
    (models.ReaderSettings, records.ReaderSettings, frozenset()),
    (models.GuideState, records.GuideState, frozenset()),
    # A thread as the page holds it, sent back with whatever is about it
    (models.ThreadDraft, threads.ThreadInput, frozenset()),
    (models.TurnDraft, threads.TurnInput, frozenset()),
    # A story's document as the agent writes it
    (told.Step, story.StepInput, frozenset()),
    (told.Chapter[told.Step], story.ChapterInput, frozenset()),
    (told.OverviewItem, story.OverviewItemInput, frozenset()),
    (told.Diagram, story.DiagramInput, frozenset()),
    (told.StoryOverview, story.StoryOverviewInput, frozenset()),
    (told.Story[told.Step], story.StoryRequest, frozenset()),
    # and the story as a page is told it
    (models.LineSpan, story.LineSpan, frozenset()),
    (told.OverviewItem, story.OverviewItem, frozenset()),
    (told.Diagram, story.Diagram, frozenset()),
    (told.StoryOverview, story.StoryOverview, frozenset()),
    # Whether a thread may name its file, which the review's model answers from its path rather than keeps
    (told.StepNow, story.StepNow, frozenset()),
    (told.FollowedStep, story.FollowedStep, frozenset({"commentable"})),
    # How many of its steps show code changed since the story was told, which the review's model answers from its
    # steps rather than keeps
    (told.Chapter[told.FollowedStep], story.FollowedChapter, frozenset({"changed_steps"})),
    (told.LeftOut, story.LeftOut, frozenset()),
    (told.ToldStory[told.FollowedStep], story.ToldStory, frozenset()),
    (told.StoryHeld, story.StoryHeld, frozenset()),
    (told.CodeMovedOn, story.CodeMovedOn, frozenset()),
    (told.LeftOutChanged, story.LeftOutChanged, frozenset()),
    # and the reader's asking for one, read with the review's facts
    (told.StoryAsking, content.StoryAsking, frozenset()),
    *EVENTS_AND_PUSHES,
    # A hello as the server hears it, and as the page says it
    (threads.ReceivedHello, threads.SessionHello, frozenset()),
]


@pytest.mark.parametrize(("review_model", "wire_model", "wire_only"), TWINS, ids=[pair[1].__name__ for pair in TWINS])
def test_the_wire_carries_every_field_of_the_reviews_own_model(
    review_model: type[BaseModel], wire_model: type[BaseModel], wire_only: frozenset[str]
) -> None:
    written_out = set(wire_model.model_fields) | set(wire_model.model_computed_fields)

    assert written_out == set(review_model.model_fields) | wire_only


def test_every_event_the_review_tells_its_pages_is_held_to_its_push() -> None:
    """An event added without its pair here would be held to nothing."""
    assert {event for event, _, _ in EVENTS_AND_PUSHES} == set(get_args(page_events.PageEvent.__value__))
