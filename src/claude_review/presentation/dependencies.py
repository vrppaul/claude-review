from importlib.metadata import version as installed_version
from pathlib import Path

from fastapi import Request
from pydantic import BaseModel

from claude_review.domain.models import DiffFile, GuideState, ReaderSettings, ReviewMode
from claude_review.domain.protocols import Clock
from claude_review.presentation.state import ServerState
from claude_review.repositories.image_store import DirectoryImageStore
from claude_review.repositories.json_record_store import JsonRecordStore
from claude_review.services.anchor_service import AnchorService
from claude_review.services.image_service import REVIEW_IMAGE_QUOTA, ImageService
from claude_review.services.reader_record_service import ReaderRecordService

PACKAGE_NAME = "claude-review"


def get_state(request: Request) -> ServerState:
    return request.app.state.server


def get_diff_files(request: Request) -> list[DiffFile]:
    return request.app.state.diff_files


def get_review_mode(request: Request) -> ReviewMode:
    return request.app.state.review_mode


def get_review_title(request: Request) -> str:
    return request.app.state.review_title


def get_repo_root(request: Request) -> Path | None:
    return request.app.state.repo_root


def get_diff_base(request: Request) -> str | None:
    return request.app.state.diff_base


def get_clock(request: Request) -> Clock:
    return request.app.state.clock


def get_objects(request: Request) -> Path | None:
    return request.app.state.workspace.objects


def get_anchor_service(request: Request) -> AnchorService:
    """The anchors of one review, read against its own diff as it stands now."""
    return AnchorService(request.app.state.diff_files)


def get_image_service(request: Request) -> ImageService:
    """The image service of one review."""
    store = DirectoryImageStore(request.app.state.workspace.images)
    return ImageService(store, request.app.state.server.images, REVIEW_IMAGE_QUOTA)


def reader_record_service[Record: BaseModel](path: Path, record_type: type[Record]) -> ReaderRecordService[Record]:
    """One record about the reader, kept in its file, for as long as the review runs."""
    return ReaderRecordService(JsonRecordStore(path, record_type), record_type)


def get_settings_service(request: Request) -> ReaderRecordService[ReaderSettings]:
    return request.app.state.settings


def get_guide_service(request: Request) -> ReaderRecordService[GuideState]:
    return request.app.state.guide


def get_release() -> str:
    return installed_version(PACKAGE_NAME)
