"""What every review on the machine remembers about its reader: how they read, and how far they were shown around."""

import structlog
from fastapi import APIRouter, Depends

from claude_review.domain.models import GuideState, ReaderSettings
from claude_review.presentation.dependencies import get_guide_service, get_settings_service
from claude_review.presentation.schemas import GuideChange, GuideResponse, SettingsChange, SettingsResponse
from claude_review.services.reader_record_service import ReaderRecordService

log = structlog.get_logger()

router = APIRouter()


@router.get("/settings")
async def reader_settings(
    settings: ReaderRecordService[ReaderSettings] = Depends(get_settings_service),
) -> SettingsResponse:
    """Say how this reader reads, as chosen in any review on this machine."""
    kept = await settings.read()
    return SettingsResponse(settings=kept or ReaderSettings(), stored=kept is not None)


@router.put("/settings")
async def change_reader_settings(
    request: SettingsChange,
    settings: ReaderRecordService[ReaderSettings] = Depends(get_settings_service),
) -> ReaderSettings:
    """Keep a choice the reader made, for this review and every later one."""
    # A choice sent as null is a choice not sent
    changed = await settings.change(request.model_dump(exclude_none=True))
    log.info("settings_changed", changed=sorted(request.model_fields_set))
    return changed


@router.get("/guide")
async def guide_state(guide: ReaderRecordService[GuideState] = Depends(get_guide_service)) -> GuideResponse:
    """Say how far this reader has been shown around, in any review on this machine."""
    kept = await guide.read()
    return GuideResponse(guide=kept or GuideState(), stored=kept is not None)


@router.put("/guide")
async def change_guide_state(
    request: GuideChange,
    guide: ReaderRecordService[GuideState] = Depends(get_guide_service),
) -> GuideState:
    """Remember what the reader has now been shown."""
    return await guide.change(request.model_dump(exclude_unset=True))
