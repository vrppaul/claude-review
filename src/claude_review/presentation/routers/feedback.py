"""The reader's feedback on the review itself: the issue written of it, for the page to show before it goes."""

from fastapi import APIRouter

from claude_review.presentation.dependencies import MachineDep
from claude_review.presentation.errors import Takes, refusals
from claude_review.presentation.schemas.feedback import FeedbackIssueResponse, FeedbackRequest
from claude_review.services.feedback import issue_of

router = APIRouter()


@router.post("/feedback", responses=refusals(takes=Takes.JSON_BODY))
async def write_the_issue(request: FeedbackRequest, machine: MachineDep) -> FeedbackIssueResponse:
    """Write the issue of what the reader wrote and left ticked, to the letter, and the address that opens it.

    Nothing is sent from here: the page shows the issue as written, and the reader opens it on GitHub or hands
    it to the agent themselves.
    """
    return FeedbackIssueResponse.from_domain(issue_of(request.to_domain(), machine))
