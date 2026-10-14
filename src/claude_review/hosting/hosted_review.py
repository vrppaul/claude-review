"""A review put together for this machine: its parts made, joined up, and given the app that serves it."""

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict

from claude_review.domain.interfaces import Clock, ReviewedRepository
from claude_review.domain.models import GuideState, ReaderSettings
from claude_review.hosting.workspace import ReaderFiles, ReviewWorkspace
from claude_review.presentation.app import create_app
from claude_review.presentation.broadcast import PAGE_BACKLOG, BrowserBroadcast
from claude_review.repositories.image_store import DirectoryImageStore
from claude_review.repositories.json_record_store import JsonRecordStore
from claude_review.services.image_service import REVIEW_IMAGE_QUOTA, ImageService
from claude_review.services.reader_record_service import ReaderRecords, ReaderRecordService
from claude_review.services.review.review import KeptForTheReader, Review
from claude_review.services.review_opening import ReviewOpening


class HostedReview(BaseModel):
    """A review and the app that serves it."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    review: Review
    app: FastAPI


def host_review(
    opening: ReviewOpening,
    *,
    repository: ReviewedRepository,
    workspace: ReviewWorkspace,
    reader_files: ReaderFiles,
    clock: Clock,
) -> HostedReview:
    """Put a review together on what it opens on, reading through the repository it is given.

    Whoever hosts it says how the repository is read — the command line
    through git, writing the trees the review is read against into the
    workspace rather than into the repository under review — and its images
    are kept in the workspace too. One broadcast is made with it and handed
    to both: to the review, as the channel it tells its pages through, and
    to the app, which serves those pages. So are the reader's settings: the
    app reads them, and the review acts on whether stories are on.
    """
    broadcast = BrowserBroadcast(backlog=PAGE_BACKLOG, identity=opening.identity_digest)
    records = _reader_records(reader_files)
    images = ImageService(DirectoryImageStore(workspace.images), REVIEW_IMAGE_QUOTA)
    review = Review(
        opening,
        repository=repository,
        page=broadcast,
        clock=clock,
        kept=KeptForTheReader(images=images, settings=records.settings),
    )
    return HostedReview(review=review, app=create_app(review, broadcast, records))


def _reader_records(reader_files: ReaderFiles) -> ReaderRecords:
    """What the review remembers about its reader, each record kept in its own file."""
    return ReaderRecords(
        settings=ReaderRecordService(JsonRecordStore(reader_files.settings, ReaderSettings), ReaderSettings),
        guide=ReaderRecordService(JsonRecordStore(reader_files.guide, GuideState), GuideState),
    )
