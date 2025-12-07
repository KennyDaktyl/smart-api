import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.repositories.device_repository import DeviceRepository
from app.repositories.device_event_repository import DeviceEventRepository
from app.schemas.device_event_schema import (
    DeviceEventCreate,
    DeviceEventOut,
    DeviceEventSeriesOut,
)

router = APIRouter(prefix="/device-events", tags=["Device Events"])

repo = DeviceEventRepository()
logger = logging.getLogger(__name__)


@router.post("/", response_model=DeviceEventOut)
def log_device_state(payload: DeviceEventCreate, db: Session = Depends(get_db)):
    timestamp = payload.timestamp or datetime.now(timezone.utc)

    event = repo.create_state_event(
        db,
        device_id=payload.device_id,
        pin_state=payload.pin_state,
        trigger_reason=payload.trigger_reason,
        power_kw=payload.power_kw,
        timestamp=timestamp,
    )

    logger.info(
        "Device event persisted",
        extra={
            "device_id": payload.device_id,
            "pin_state": payload.pin_state,
            "trigger_reason": payload.trigger_reason,
            "power_kw": payload.power_kw,
            "timestamp": timestamp.isoformat(),
        },
    )

    return event


@router.get("/device/{device_id}", response_model=DeviceEventSeriesOut)
def list_device_events(
    device_id: int,
    limit: int = Query(200, ge=1, le=1000),
    date_start: datetime | None = Query(None),
    date_end: datetime | None = Query(None),
    db: Session = Depends(get_db),
) -> DeviceEventSeriesOut:
    def to_utc(dt: datetime) -> datetime:
        # SQLite zwraca naivo; wymuszamy UTC dla spójnych obliczeń
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    # Domyślnie zwracamy dane z dzisiaj
    default_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    start = to_utc(date_start) if date_start else default_start
    end = to_utc(date_end) if date_end else now

    events = repo.list_for_device(
        db, device_id=device_id, limit=limit, date_start=start, date_end=end
    )

    device = DeviceRepository().get_by_id(db, device_id)
    rated_power_kw = float(device.rated_power_kw) if device and device.rated_power_kw else None

    # Przeliczenie czasu pracy (ON) na podstawie kolejnych zdarzeń
    events_sorted = sorted(events, key=lambda e: e.timestamp)
    total_minutes_on = 0
    energy_kwh = 0.0

    for idx, event in enumerate(events_sorted):
        current_ts = to_utc(event.timestamp)
        next_ts = (
            to_utc(events_sorted[idx + 1].timestamp) if idx + 1 < len(events_sorted) else end
        )

        if event.pin_state:
            duration_minutes = int((next_ts - current_ts).total_seconds() // 60)
            total_minutes_on += duration_minutes
            power_for_segment = float(event.power_kw) if event.power_kw is not None else (
                rated_power_kw or 0.0
            )
            energy_kwh += (power_for_segment * duration_minutes) / 60

    avg_power = None
    on_events_with_power = [
        float(e.power_kw)
        if e.power_kw is not None
        else rated_power_kw
        for e in events
        if e.pin_state
    ]
    if rated_power_kw is not None and not on_events_with_power:
        avg_power = rated_power_kw
    elif on_events_with_power:
        avg_power = float(sum(on_events_with_power) / len(on_events_with_power))

    return DeviceEventSeriesOut(
        events=events,
        total_minutes_on=total_minutes_on,
        average_power_kw=avg_power,
        energy_kwh=round(energy_kwh, 3) if energy_kwh else None,
        rated_power_kw=rated_power_kw,
    )
