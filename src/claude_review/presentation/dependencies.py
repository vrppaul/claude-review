from fastapi import Request

from claude_review.domain.models import DiffFile, ReviewMode
from claude_review.presentation.schemas import ServerState
from claude_review.services.review_service import ReviewService


def get_state(request: Request) -> ServerState:
    return request.app.state.server_state


def get_diff_files(request: Request) -> list[DiffFile]:
    return request.app.state.diff_files


def get_review_service(request: Request) -> ReviewService:
    return request.app.state.review_service


def get_review_mode(request: Request) -> ReviewMode:
    return request.app.state.review_mode
