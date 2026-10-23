"""What a review keeps of itself while it runs, to go on as it was if it is opened again before it is finished.

A review stopped under its reader — Ctrl+C, `kill`, a terminal closed, a
fault — and opened again on the same change is the same review, until the
reader finishes it: its page kept its draft, and the review keeps what only
it knows. Its round, which the page would tell it only once a page is open,
and its story, which cost the agent's tokens to tell. A review the reader
finished keeps nothing: the same change opened after it is a new review.
"""

from pydantic import BaseModel, ConfigDict, Field

from claude_review.domain.models import FIRST_ROUND
from claude_review.domain.story import KeptStory


class KeptReview(BaseModel):
    """A review as it stood when it was last kept: the round being written, and its story."""

    model_config = ConfigDict(frozen=True)

    round: int = Field(ge=FIRST_ROUND)
    # The story last told of the change, as it was told: None while none has been
    story: KeptStory | None
    # Whether the review wants its story kept told: asked for, by the reader or as it opened, and not stopped
    story_wanted: bool
