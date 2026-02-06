from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from smart_common.core.db import get_db
from smart_common.core.dependencies import get_current_agent, get_current_user
from smart_common.models.user import User
from smart_common.enums.device_event import DeviceEventType
from smart_common.schemas.device_event_schema import (
    DeviceEventCreate,
    DeviceEventOut,
    DeviceEventSeriesOut,
)
from smart_common.repositories.device import DeviceRepository
from smart_common.repositories.device_event import DeviceEventRepository
from smart_common.services.device_event_service import DeviceEventService

logger = logging.getLogger(__name__)

device_events_router = APIRouter(
    prefix="/device-events",
    tags=["Device Events"],
)

# =====================================================
# CREATE EVENT
# =====================================================


@device_events_router.post(
    "",
    response_model=DeviceEventOut,
    status_code=201,
    summary="Create device event",
)
def create_device_event(
    payload: DeviceEventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DeviceEventOut:
    logger.info(
        "Creating device event",
        extra={
            "user_id": current_user.id,
            "device_id": payload.device_id,
            "event_type": payload.event_type.value,
            "event_name": payload.event_name.value,
        },
    )

    device = DeviceRepository(db).get_for_user_by_id(
        device_id=payload.device_id,
        user_id=current_user.id,
    )

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    event = DeviceEventRepository(db).create(**payload.model_dump(exclude_unset=True))

    return DeviceEventOut.model_validate(event, from_attributes=True)


@device_events_router.post(
    "/agent",
    response_model=DeviceEventOut,
    status_code=201,
    summary="Create device event (agent)",
)
def create_device_event_from_agent(
    payload: DeviceEventCreate,
    db: Session = Depends(get_db),
    agent=Depends(get_current_agent),
) -> DeviceEventOut:
    logger.info(
        "Creating device event from agent",
        extra={
            "agent": agent["name"],
            "device_id": payload.device_id,
            "event_type": payload.event_type.value,
            "event_name": payload.event_name.value,
        },
    )

    device = (
        db.query(DeviceRepository(db).model).filter_by(id=payload.device_id).first()
    )

    if not device:
        logger.warning(
            "Agent sent event for unknown device",
            extra={"device_id": payload.device_id, "agent": agent["name"]},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    event = DeviceEventRepository(db).create(
        **payload.model_dump(exclude_unset=True),
    )

    return DeviceEventOut.model_validate(event, from_attributes=True)


# =====================================================
# LIST EVENTS FOR DEVICE
# =====================================================


@device_events_router.get(
    "/device/{device_id}",
    response_model=DeviceEventSeriesOut,
    summary="List device events",
)
def list_device_events(
    device_id: int,
    limit: int = Query(200, ge=1, le=1000),
    date_start: datetime | None = Query(None),
    date_end: datetime | None = Query(None),
    event_type: DeviceEventType | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DeviceEventSeriesOut:
    service = DeviceEventService(
        event_repo_factory=lambda db: DeviceEventRepository(db),
        device_repo_factory=lambda db: DeviceRepository(db),
    )

    return DeviceEventSeriesOut(
        **service.list_device_events(
            db=db,
            user_id=current_user.id,
            device_id=device_id,
            limit=limit,
            date_start=date_start,
            date_end=date_end,
            event_type=event_type,
        )
    )
