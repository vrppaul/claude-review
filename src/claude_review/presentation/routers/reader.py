"""What every review on the machine remembers about its reader: how they read, and how far they were shown around.

Both records are read the same way — the record, and whether anything was
kept — and changed the same way: what is sent is changed, a field sent as
null or left out is not.
"""

from collections.abc import Callable

import structlog
from fastapi import APIRouter
from pydantic import BaseModel

from claude_review.presentation.dependencies import GuideServiceDep, ReviewDep, SettingsServiceDep
from claude_review.presentation.errors import Takes, refusals
from claude_review.presentation.schemas.base import Schema
from claude_review.presentation.schemas.records import (
    GuideChange,
    GuideState,
    KeptRecord,
    ReaderSettings,
    SettingsChange,
)
from claude_review.services.reader_record_service import ReaderRecordService

log = structlog.get_logger()

router = APIRouter()


@router.get("/settings")
async def reader_settings(settings: SettingsServiceDep) -> KeptRecord[ReaderSettings]:
    """Say how this reader reads, as chosen in any review on this machine."""
    return await _kept(settings, ReaderSettings.from_domain)


@router.put("/settings", responses=refusals(takes=Takes.JSON_BODY))
async def change_reader_settings(request: SettingsChange, review: ReviewDep) -> ReaderSettings:
    """Keep a choice the reader made, for this review and every later one; stories turned on or off ask or stop here."""
    changed = ReaderSettings.from_domain(await review.change_settings(request))
    log.info("settings_changed", changed=sorted(request.model_fields_set))
    return changed


@router.get("/guide")
async def guide_state(guide: GuideServiceDep) -> KeptRecord[GuideState]:
    """Say how far this reader has been shown around, in any review on this machine."""
    return await _kept(guide, GuideState.from_domain)


@router.put("/guide", responses=refusals(takes=Takes.JSON_BODY))
async def change_guide_state(request: GuideChange, guide: GuideServiceDep) -> GuideState:
    """Remember what the reader has now been shown."""
    return GuideState.from_domain(await guide.change(request))


async def _kept[Record: BaseModel, Answered: Schema](
    service: ReaderRecordService[Record], answer_of: Callable[[Record], Answered]
) -> KeptRecord[Answered]:
    """A record as kept, or the defaults for a reader nothing has been kept about, and which it is."""
    kept = await service.read()
    return KeptRecord(record=answer_of(kept or service.defaults()), stored=kept is not None)
