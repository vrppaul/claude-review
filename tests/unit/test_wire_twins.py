"""What crosses the wire carries everything the review's own model has, field for field.

The wire's models are built from the review's by their fields, so a field
added to one and not the other would be dropped, or filled with a default,
without a word. Each pair is held to the same fields here.
"""

import pytest
from pydantic import BaseModel

from claude_review.domain import models
from claude_review.presentation.wire import agent, content, records, threads

# Pairs of the review's model and the wire's, with what the wire adds of its own
TWINS: list[tuple[type[BaseModel], type[BaseModel], frozenset[str]]] = [
    (models.DiffLine, content.DiffLine, frozenset()),
    (models.DiffHunk, content.DiffHunk, frozenset()),
    (models.DiffFile, content.DiffFile, frozenset()),
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
    (models.RoundSubmission, agent.RoundSubmission, frozenset()),
    (models.ReaderSettings, records.ReaderSettings, frozenset()),
    (models.GuideState, records.GuideState, frozenset()),
]


@pytest.mark.parametrize(("review_model", "wire_model", "wire_only"), TWINS, ids=[pair[1].__name__ for pair in TWINS])
def test_the_wire_carries_every_field_of_the_reviews_own_model(
    review_model: type[BaseModel], wire_model: type[BaseModel], wire_only: frozenset[str]
) -> None:
    assert set(wire_model.model_fields) == set(review_model.model_fields) | wire_only
