from __future__ import annotations

import logging
from datetime import date as date_type
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from smart_common.core.db import get_db
from smart_common.core.dependencies import get_current_agent, get_current_user
from smart_common.models.user import User
from smart_common.enums.device_event import DeviceEventType
from smart_common.schemas.device_event_schema import (
    DeviceEventCreate,
    DeviceEventCreateFromAgent,
    DeviceEventCreateFromAgentBase,
    DeviceEventCreateFromAgentByUUID,
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


def _resolve_state_value(
    *,
    is_on: bool | None,
    pin_state: bool | None,
    device_state: str | None,
) -> bool | None:
    if isinstance(is_on, bool):
        return is_on

    if isinstance(pin_state, bool):
        return pin_state

    if isinstance(device_state, str):
        normalized = device_state.strip().upper()
        if normalized in {"ON", "TRUE", "1"}:
            return True
        if normalized in {"OFF", "FALSE", "0"}:
            return False

    return None


def _sync_device_config_state(device, *, is_on: bool) -> None:
    microcontroller = getattr(device, "microcontroller", None)
    if not microcontroller:
        return

    config = dict(microcontroller.config or {})
    raw_devices_config = config.get("devices_config")

    devices_config = (
        [dict(item) for item in raw_devices_config if isinstance(item, dict)]
        if isinstance(raw_devices_config, list)
        else []
    )

    updated = False
    for item in devices_config:
        if (
            item.get("device_id") == device.id
            or item.get("pin_number") == device.device_number
        ):
            mode_value = (
                device.mode.value if hasattr(device.mode, "value") else str(device.mode)
            )
            threshold_value = (
                float(device.threshold_value) if device.threshold_value is not None else None
            )
            rated_power = (
                float(device.rated_power) if device.rated_power is not None else None
            )
            item["device_id"] = device.id
            item["device_uuid"] = str(device.uuid)
            item["device_number"] = device.device_number
            item["pin_number"] = device.device_number
            item["is_on"] = is_on
            item["mode"] = mode_value
            item["rated_power"] = rated_power
            item["threshold_value"] = threshold_value
            updated = True

    if not updated:
        mode_value = device.mode.value if hasattr(device.mode, "value") else str(device.mode)
        threshold_value = (
            float(device.threshold_value) if device.threshold_value is not None else None
        )
        rated_power = (
            float(device.rated_power) if device.rated_power is not None else None
        )
        devices_config.append(
            {
                "device_id": device.id,
                "device_uuid": str(device.uuid),
                "device_number": device.device_number,
                "pin_number": device.device_number,
                "mode": mode_value,
                "rated_power": rated_power,
                "threshold_value": threshold_value,
                "is_on": is_on,
            }
        )

    config["devices_config"] = devices_config
    microcontroller.config = config


def _create_agent_event(
    *,
    db: Session,
    device,
    payload: DeviceEventCreateFromAgentBase,
) -> DeviceEventOut:
    event_payload = payload.model_dump(
        exclude_unset=True,
        exclude={"device_id", "device_number", "is_on"},
    )
    event_payload["device_id"] = device.id

    if event_payload.get("pin_state") is None and payload.is_on is not None:
        event_payload["pin_state"] = payload.is_on

    if event_payload.get("source") is None:
        event_payload["source"] = "agent"

    resolved_state = _resolve_state_value(
        is_on=payload.is_on,
        pin_state=event_payload.get("pin_state"),
        device_state=payload.device_state,
    )
    if payload.event_type == DeviceEventType.STATE and resolved_state is not None:
        device.manual_state = resolved_state
        device.last_state_change_at = payload.created_at or datetime.now(timezone.utc)
        _sync_device_config_state(device, is_on=resolved_state)

    event = DeviceEventRepository(db).create(
        **event_payload,
    )

    return DeviceEventOut.model_validate(event, from_attributes=True)

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
    payload: DeviceEventCreateFromAgent,
    db: Session = Depends(get_db),
    agent=Depends(get_current_agent),
) -> DeviceEventOut:
    device_repo = DeviceRepository(db)

    if payload.device_id is not None:
        device = db.query(device_repo.model).filter_by(id=payload.device_id).first()
    else:
        matches = (
            db.query(device_repo.model)
            .filter_by(device_number=payload.device_number)
            .all()
        )
        if not matches:
            device = None
        elif len(matches) > 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "device_number is ambiguous. Send device_id or call "
                    "/api/device-events/agent/{device_uuid}."
                ),
            )
        else:
            device = matches[0]

    if (
        payload.device_id is not None
        and payload.device_number is not None
        and device
        and device.device_number != payload.device_number
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="device_id and device_number do not match",
        )

    logger.info(
        "Creating device event from agent",
        extra={
            "agent": agent["name"],
            "device_id": payload.device_id,
            "device_number": payload.device_number,
            "event_type": payload.event_type.value,
            "event_name": payload.event_name.value,
        },
    )

    if not device:
        logger.warning(
            "Agent sent event for unknown device",
            extra={
                "device_id": payload.device_id,
                "device_number": payload.device_number,
                "agent": agent["name"],
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    return _create_agent_event(
        db=db,
        device=device,
        payload=payload,
    )


@device_events_router.post(
    "/agent/{device_uuid}",
    response_model=DeviceEventOut,
    status_code=201,
    summary="Create device event (agent, by device UUID)",
)
def create_device_event_from_agent_by_uuid(
    device_uuid: UUID,
    payload: DeviceEventCreateFromAgentByUUID,
    db: Session = Depends(get_db),
    agent=Depends(get_current_agent),
) -> DeviceEventOut:
    device = DeviceRepository(db).get_by_uuid(device_uuid)

    logger.info(
        "Creating device event from agent by uuid",
        extra={
            "agent": agent["name"],
            "device_uuid": str(device_uuid),
            "event_type": payload.event_type.value,
            "event_name": payload.event_name.value,
        },
    )

    if not device:
        logger.warning(
            "Agent sent event for unknown device uuid",
            extra={
                "device_uuid": str(device_uuid),
                "agent": agent["name"],
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    return _create_agent_event(
        db=db,
        device=device,
        payload=payload,
    )


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
    selected_date: date_type | None = Query(None, alias="date"),
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
            selected_date=selected_date,
            event_type=event_type,
        )
    )
