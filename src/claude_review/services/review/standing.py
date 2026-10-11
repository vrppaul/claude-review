"""Where a review stands, read in one piece by whoever has to say it: its page, or an agent catching up."""

from pydantic import BaseModel, ConfigDict

from claude_review.domain.models import AgentStatus, PanelEntry, ReviewMode, ThreadDraft


class ReviewStanding(BaseModel):
    """What a review is and where it has got to."""

    model_config = ConfigDict(frozen=True)

    title: str
    # What makes it the same review when it is opened again, in short: the
    # name its page keeps the reader's unsent work under
    identity: str
    mode: ReviewMode
    # What it was opened against: a commit or a ref, or None for the uncommitted changes
    opened_against: str | None
    # The round being written
    round: int
    # Whether anything is there to answer it
    answerer_attached: bool
    # What the agent last said about itself
    agent: AgentStatus


class CatchUp(BaseModel):
    """What an agent arriving late is told: where the review stands, the threads the page holds, and the panel."""

    model_config = ConfigDict(frozen=True)

    standing: ReviewStanding
    file_count: int
    threads: list[ThreadDraft]
    panel: list[PanelEntry]
