from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from smart_common.core.db import get_db
from smart_common.enums.device_event import DeviceEventType
from smart_common.models.user import User
from smart_common.repositories.device import DeviceRepository
from smart_common.repositories.device_event import DeviceEventRepository
from smart_common.repositories.microcontroller import MicrocontrollerRepository

from app.api.schemas.device_events import DeviceEventTimelineResponse
from app.core.dependencies import get_current_user
from app.services.device_event_service import DeviceEventService

router = APIRouter(
    prefix="/installations/{installation_id}/microcontrollers/{microcontroller_uuid}/devices/{device_id}/events",
    tags=["Device Events"],
)

service = DeviceEventService(
    lambda db: DeviceEventRepository(db),
    lambda db: DeviceRepository(db),
)


def _validate_microcontroller(
    db: Session,
    installation_id: int,
    microcontroller_uuid: UUID,
    user_id: int,
):
    repo = MicrocontrollerRepository(db)
    microcontroller = repo.get_for_user_by_uuid(microcontroller_uuid, user_id)
    if not microcontroller or microcontroller.installation_id != installation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Microcontroller not found")
    return microcontroller


@router.get(
    "/",
    response_model=DeviceEventTimelineResponse,
    status_code=200,
    summary="List device events",
    description="Returns device events with telemetry summary over a time window.",
)
def list_device_events(
    installation_id: int,
    microcontroller_uuid: UUID,
    device_id: int,
    limit: int = Query(200, ge=1, le=1000, description="Maximum number of events to return"),
    date_start: datetime | None = Query(
        None, description="UTC start time (inclusive) for the event window"
    ),
    date_end: datetime | None = Query(
        None, description="UTC end time (inclusive) for the event window"
    ),
    event_type: DeviceEventType | None = Query(
        None,
        description="Optional filter for event type",
        example=DeviceEventType.STATE.value,
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DeviceEventTimelineResponse:
    microcontroller = _validate_microcontroller(
        db, installation_id, microcontroller_uuid, current_user.id
    )
    timeline = service.list_device_events(
        db,
        current_user.id,
        device_id,
        limit,
        date_start,
        date_end,
        event_type,
    )
    return DeviceEventTimelineResponse.model_validate(timeline)
