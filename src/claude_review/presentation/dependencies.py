"""What a route is handed: the review it serves, and what the app keeps for every review on the machine.

Each is read off the connection, which a request and a socket both are, so
the session socket asks for what it needs the same way every route does. A
route names what it is handed by its type alone, as FastAPI's docs do
(`ReviewDep`): the dependency is said once, here, and no parameter looks as
if it had a default.
"""

from typing import Annotated

from fastapi import Depends
from starlette.requests import HTTPConnection

from claude_review.domain.models import GuideState, ReaderSettings
from claude_review.presentation.broadcast import BrowserBroadcast
from claude_review.services.reader_record_service import ReaderRecordService
from claude_review.services.review.review import Review


def get_review(connection: HTTPConnection) -> Review:
    return connection.app.state.review


def get_broadcast(connection: HTTPConnection) -> BrowserBroadcast:
    return connection.app.state.broadcast


def get_settings_service(connection: HTTPConnection) -> ReaderRecordService[ReaderSettings]:
    return connection.app.state.settings


def get_guide_service(connection: HTTPConnection) -> ReaderRecordService[GuideState]:
    return connection.app.state.guide


def get_release(connection: HTTPConnection) -> str:
    """Which release serves the review, read once when the app was made."""
    return connection.app.state.release


ReviewDep = Annotated[Review, Depends(get_review)]
BroadcastDep = Annotated[BrowserBroadcast, Depends(get_broadcast)]
SettingsServiceDep = Annotated[ReaderRecordService[ReaderSettings], Depends(get_settings_service)]
GuideServiceDep = Annotated[ReaderRecordService[GuideState], Depends(get_guide_service)]
ReleaseDep = Annotated[str, Depends(get_release)]
