from datetime import datetime, timezone
from typing import Callable

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from smart_common.enums.device_event import DeviceEventType
from smart_common.models.device import Device
from smart_common.repositories.device import DeviceRepository
from smart_common.repositories.device_event import DeviceEventRepository
from smart_common.schemas.device_event_schema import DeviceEventOut


class DeviceEventService:
    def __init__(
        self,
        event_repo_factory: Callable[[Session], DeviceEventRepository],
        device_repo_factory: Callable[[Session], DeviceRepository],
    ):
        self._event_repo_factory = event_repo_factory
        self._device_repo_factory = device_repo_factory

    def _event_repo(self, db: Session) -> DeviceEventRepository:
        return self._event_repo_factory(db)

    def _device_repo(self, db: Session) -> DeviceRepository:
        return self._device_repo_factory(db)

    def _get_device(self, db: Session, user_id: int, device_id: int) -> Device:
        device = self._device_repo(db).get_for_user_by_id(device_id, user_id)
        if not device:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
        return device

    def _ensure_utc(self, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    def list_device_events(
        self,
        db: Session,
        user_id: int,
        device_id: int,
        limit: int,
        date_start: datetime | None,
        date_end: datetime | None,
        event_type: DeviceEventType | None = None,
    ) -> dict:
        device = self._get_device(db, user_id, device_id)
        start = self._ensure_utc(date_start)
        end = self._ensure_utc(date_end)
        now = datetime.now(timezone.utc)
        if not start:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if not end:
            end = now

        events = self._event_repo(db).list_for_device(
            device_id=device.id, limit=limit, date_start=start, date_end=end, event_type=event_type
        )

        schema_events = [DeviceEventOut.model_validate(event) for event in events]

        rated_power_kw = (
            float(device.rated_power_w) / 1000 if device.rated_power_w is not None else None
        )
        total_seconds_on = 0.0
        energy_kwh = 0.0

        def to_utc(dt: datetime) -> datetime:
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

        for idx, event in enumerate(schema_events):
            current_ts = to_utc(event.created_at)
            next_ts = (
                to_utc(schema_events[idx + 1].created_at)
                if idx + 1 < len(schema_events)
                else end
            )

            if event.pin_state:
                segment_seconds = max(0, (next_ts - current_ts).total_seconds())
                total_seconds_on += segment_seconds
                power_kw = (
                    rated_power_kw
                    if rated_power_kw is not None
                    else (float(event.measured_value) if event.measured_value else 0.0)
                )
                energy_kwh += power_kw * (segment_seconds / 3600)

        total_minutes_on = int(total_seconds_on // 60)
        energy_value = round(energy_kwh, 3) if energy_kwh else None

        return {
            "events": schema_events,
            "total_minutes_on": total_minutes_on,
            "energy_kwh": energy_value,
            "rated_power_kw": rated_power_kw,
        }
