"""API route handlers."""

import asyncio

from fastapi import APIRouter, HTTPException

from claude_review.domain.models import Comment, DiffFile
from claude_review.presentation.schemas import DiffResponse, SubmitRequest, SubmitResponse
from claude_review.services.review_service import ReviewService


def create_router(
    diff_files: list[DiffFile],
    shutdown_event: asyncio.Event,
    result_holder: list[str],
    heartbeat_holder: list[float],
) -> APIRouter:
    """Create the API router with injected dependencies."""
    router = APIRouter(prefix="/api")
    review_service = ReviewService()

    @router.get("/diff")
    async def get_diff() -> DiffResponse:
        return DiffResponse(files=diff_files)

    @router.post("/heartbeat")
    async def heartbeat() -> dict[str, str]:
        heartbeat_holder.clear()
        heartbeat_holder.append(asyncio.get_event_loop().time())
        return {"status": "ok"}

    @router.post("/submit")
    async def submit_review(request: SubmitRequest) -> SubmitResponse:
        if shutdown_event.is_set():
            raise HTTPException(status_code=409, detail="Review already submitted")

        comments = [
            Comment(
                file=c.file,
                start_line=c.start_line,
                end_line=c.end_line,
                body=c.body,
            )
            for c in request.comments
        ]

        result = review_service.format_review(comments)
        result_holder.append(result.markdown)
        shutdown_event.set()

        return SubmitResponse(
            markdown=result.markdown,
            comment_count=result.comment_count,
        )

    return router
