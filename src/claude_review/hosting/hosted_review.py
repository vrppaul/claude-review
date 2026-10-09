"""A review put together for this machine: its parts made, joined up, and given the app that serves it."""

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict

from claude_review.domain.models import ReaderFiles, ReviewWorkspace
from claude_review.domain.protocols import Clock
from claude_review.presentation.app import create_app
from claude_review.presentation.broadcast import PAGE_BACKLOG, BrowserBroadcast
from claude_review.repositories.git_repository import GitRepository
from claude_review.repositories.image_store import DirectoryImageStore
from claude_review.services.image_service import REVIEW_IMAGE_QUOTA, ImageService
from claude_review.services.review.answerer import ANSWERER_LEASE_SECONDS, Answerer
from claude_review.services.review.browser_presence import RELOAD_GRACE_SECONDS, BrowserPresence
from claude_review.services.review.review import Review
from claude_review.services.review.review_lifetime import ReviewLifetime
from claude_review.services.review_opening import ReviewOpening


class HostedReview(BaseModel):
    """A review and the app that serves it."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    review: Review
    app: FastAPI


def host_review(
    opening: ReviewOpening, *, workspace: ReviewWorkspace, reader_files: ReaderFiles, clock: Clock
) -> HostedReview:
    """Put a review together on what it opens on, writing into its own workspace.

    The review's repository writes the trees it is read against into the
    workspace rather than into the repository under review, and its images
    are kept there too.
    """
    broadcast = BrowserBroadcast(backlog=PAGE_BACKLOG)
    review = Review(
        opening,
        repository=GitRepository(objects=workspace.objects),
        images=ImageService(DirectoryImageStore(workspace.images), REVIEW_IMAGE_QUOTA),
        page=broadcast,
        presence=BrowserPresence(reload_grace=RELOAD_GRACE_SECONDS),
        answerer=Answerer(broadcast, clock, lease_seconds=ANSWERER_LEASE_SECONDS),
        lifetime=ReviewLifetime(),
        clock=clock,
    )
    return HostedReview(review=review, app=create_app(review, broadcast, reader_files))
