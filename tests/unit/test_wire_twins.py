"""What crosses the wire carries everything the review's own model has, field for field.

The wire's models are built from the review's by their fields, so a field
added to one and not the other would be dropped, or filled with a default,
without a word. Each pair is held to the same fields here.
"""

import pytest
from pydantic import BaseModel

from claude_review.domain import models
from claude_review.presentation.wire import agent, content, records, threads

# Pairs of the review's model and the wire's
TWINS: list[tuple[type[BaseModel], type[BaseModel]]] = [
    (models.DiffLine, content.DiffLine),
    (models.DiffHunk, content.DiffHunk),
    (models.DiffFile, content.DiffFile),
    (models.LineAnchor, threads.LineAnchor),
    (models.Turn, threads.Turn),
    (models.Thread, threads.Thread),
    (models.AgentStatus, agent.AgentStatus),
    (models.ProgressStep, agent.ProgressStep),
    (models.AgentWork, agent.AgentWork),
    (models.ThreadQuestion, agent.ThreadQuestion),
    (models.PanelMessage, agent.PanelMessage),
    (models.PanelCancel, agent.PanelCancel),
    (models.PanelEntry, agent.PanelEntry),
    (models.RoundSubmission, agent.RoundSubmission),
    (models.ReaderSettings, records.ReaderSettings),
    (models.GuideState, records.GuideState),
]


@pytest.mark.parametrize(("review_model", "wire_model"), TWINS, ids=[pair[1].__name__ for pair in TWINS])
def test_the_wire_carries_every_field_of_the_reviews_own_model(
    review_model: type[BaseModel], wire_model: type[BaseModel]
) -> None:
    assert set(wire_model.model_fields) == set(review_model.model_fields)
