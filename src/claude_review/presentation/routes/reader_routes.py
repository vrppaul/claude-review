"""What every review on the machine remembers about its reader: how they read, and how far they were shown around.

Both records are read the same way — the record, and whether anything was
kept — and changed the same way: what is sent is changed, a field sent as
null or left out is not.
"""

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from claude_review.domain import models
from claude_review.presentation.dependencies import get_guide_service, get_settings_service
from claude_review.presentation.refusals import Takes, refusals
from claude_review.presentation.wire.base import WireModel
from claude_review.presentation.wire.records import (
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
async def reader_settings(
    settings: ReaderRecordService[models.ReaderSettings] = Depends(get_settings_service),
) -> KeptRecord[ReaderSettings]:
    """Say how this reader reads, as chosen in any review on this machine."""
    return await _kept(settings, ReaderSettings)


@router.put("/settings", responses=refusals(takes=Takes.JSON_BODY))
async def change_reader_settings(
    request: SettingsChange,
    settings: ReaderRecordService[models.ReaderSettings] = Depends(get_settings_service),
) -> ReaderSettings:
    """Keep a choice the reader made, for this review and every later one."""
    changed = ReaderSettings.of(await settings.change(request))
    log.info("settings_changed", changed=sorted(request.model_fields_set))
    return changed


@router.get("/guide")
async def guide_state(
    guide: ReaderRecordService[models.GuideState] = Depends(get_guide_service),
) -> KeptRecord[GuideState]:
    """Say how far this reader has been shown around, in any review on this machine."""
    return await _kept(guide, GuideState)


@router.put("/guide", responses=refusals(takes=Takes.JSON_BODY))
async def change_guide_state(
    request: GuideChange,
    guide: ReaderRecordService[models.GuideState] = Depends(get_guide_service),
) -> GuideState:
    """Remember what the reader has now been shown."""
    return GuideState.of(await guide.change(request))


async def _kept[Record: BaseModel, Wire: WireModel](
    service: ReaderRecordService[Record], wire_type: type[Wire]
) -> KeptRecord[Wire]:
    """A record as kept, or the defaults for a reader nothing has been kept about, and which it is."""
    kept = await service.read()
    return KeptRecord(record=wire_type.of(kept or service.defaults()), stored=kept is not None)
