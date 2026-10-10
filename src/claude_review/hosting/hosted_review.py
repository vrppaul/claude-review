"""A review put together for this machine: its parts made, joined up, and given the app that serves it."""

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict

from claude_review.domain.interfaces import Clock
from claude_review.domain.models import GuideState, ReaderSettings
from claude_review.hosting.workspace import ReaderFiles, ReviewWorkspace
from claude_review.presentation.app import create_app
from claude_review.presentation.broadcast import PAGE_BACKLOG, BrowserBroadcast
from claude_review.repositories.git_repository import GitRepository
from claude_review.repositories.image_store import DirectoryImageStore
from claude_review.repositories.json_record_store import JsonRecordStore
from claude_review.services.image_service import REVIEW_IMAGE_QUOTA, ImageService
from claude_review.services.reader_record_service import ReaderRecords, ReaderRecordService
from claude_review.services.review.review import Review
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
        clock=clock,
    )
    return HostedReview(review=review, app=create_app(review, broadcast, _reader_records(reader_files)))


def _reader_records(reader_files: ReaderFiles) -> ReaderRecords:
    """What the review remembers about its reader, each record kept in its own file."""
    return ReaderRecords(
        settings=ReaderRecordService(JsonRecordStore(reader_files.settings, ReaderSettings), ReaderSettings),
        guide=ReaderRecordService(JsonRecordStore(reader_files.guide, GuideState), GuideState),
    )
