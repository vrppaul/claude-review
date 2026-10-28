"""What a route is handed: the review it serves, what the app keeps for every review on the machine, and where it runs.

Each is read off the connection, which a request and a socket both are, so
the session socket asks for what it needs the same way every route does. A
route names what it is handed by its type alone, as FastAPI's docs do
(`ReviewDep`): the dependency is said once, here, and no parameter looks as
if it had a default.
"""

from typing import Annotated

from fastapi import Depends, Header
from starlette.requests import HTTPConnection

from claude_review.domain.feedback import Machine
from claude_review.domain.models import GuideState, ReaderSettings
from claude_review.presentation.broadcast import BrowserBroadcast
from claude_review.services.feedback import THIS_OPERATING_SYSTEM, browser_named
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


def get_machine(release: ReleaseDep, user_agent: Annotated[str | None, Header()] = None) -> Machine:
    """Where the review runs, and the browser the request came from, as the user agent it sends names it.

    A request with no user agent is a browser nobody can name, not a wrong request.
    """
    return Machine(release=release, operating_system=THIS_OPERATING_SYSTEM, browser=browser_named(user_agent))


MachineDep = Annotated[Machine, Depends(get_machine)]
