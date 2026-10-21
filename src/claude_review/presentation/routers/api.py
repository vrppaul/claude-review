"""Every route a review serves, under one prefix: the one router an app mounts wherever the API is wanted."""

from fastapi import APIRouter

from claude_review.presentation.errors import documented
from claude_review.presentation.origin_guard import NOT_ITS_PAGE_STATUS
from claude_review.presentation.routers import agent, page, reader, session

API_PREFIX = "/api"

# Each route says how it may refuse; every one of them may be refused by the
# origin guard, which stands in front of them all
api_router = APIRouter(prefix=API_PREFIX, responses=documented({NOT_ITS_PAGE_STATUS}))
api_router.include_router(page.router)
api_router.include_router(agent.router)
api_router.include_router(reader.router)
api_router.include_router(session.router)
