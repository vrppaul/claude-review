from importlib.metadata import version as installed_version
from pathlib import Path

from fastapi import Request
from starlette.applications import Starlette

from claude_review.domain.models import DiffFile, ReviewMode
from claude_review.presentation.state import ServerState
from claude_review.repositories.image_store import DirectoryImageStore
from claude_review.services.image_service import ImageService

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


def get_objects(request: Request) -> Path | None:
    return request.app.state.workspace.objects


def image_service_for(app: Starlette) -> ImageService:
    """The image service of one review, for a route or for the session socket."""
    store = DirectoryImageStore(app.state.workspace.images)
    return ImageService(store, app.state.server.images)


def get_image_service(request: Request) -> ImageService:
    return image_service_for(request.app)


def get_release() -> str:
    return installed_version(PACKAGE_NAME)
