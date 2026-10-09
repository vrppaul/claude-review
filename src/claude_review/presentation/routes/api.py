"""Every route a review serves, under one prefix, mounted the same way wherever the API is wanted."""

from fastapi import FastAPI

from claude_review.presentation.routes import agent_routes, page_routes, reader_routes, session_socket

API_PREFIX = "/api"


def include_api(app: FastAPI) -> None:
    """Mount the review's routes and its session socket on an app."""
    for routes in (page_routes, agent_routes, reader_routes, session_socket):
        app.include_router(routes.router, prefix=API_PREFIX)
