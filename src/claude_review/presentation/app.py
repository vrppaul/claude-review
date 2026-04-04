"""FastAPI application factory."""

import asyncio
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from claude_review.domain.models import DiffFile
from claude_review.presentation.routes import create_router

STATIC_DIR = Path(__file__).parent.parent / "static" / "dist"


def create_app(
    diff_files: list[DiffFile],
    shutdown_event: asyncio.Event,
    result_holder: list[str] | None = None,
    heartbeat_holder: list[float] | None = None,
) -> FastAPI:
    """Create the FastAPI application with injected dependencies."""
    app = FastAPI(title="Claude Review")

    router = create_router(
        diff_files=diff_files,
        shutdown_event=shutdown_event,
        result_holder=result_holder if result_holder is not None else [],
        heartbeat_holder=heartbeat_holder if heartbeat_holder is not None else [],
    )
    app.include_router(router)

    if STATIC_DIR.exists():
        app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

    return app
