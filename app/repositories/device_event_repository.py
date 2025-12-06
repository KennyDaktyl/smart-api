from datetime import datetime, timezone
from typing import List

from sqlalchemy.orm import Session

from app.models.device_event import DeviceEvent


class DeviceEventRepository:
    def create_state_event(
        self,
        db: Session,
        *,
        device_id: int,
        pin_state: bool,
        trigger_reason: str | None = None,
        power_kw: float | None = None,
        timestamp: datetime | None = None,
    ) -> DeviceEvent:
        # Persist a state-change event emitted by agent telemetry
        event = DeviceEvent(
            device_id=device_id,
            state="ON" if pin_state else "OFF",
            pin_state=pin_state,
            trigger_reason=trigger_reason,
            power_kw=power_kw,
            timestamp=timestamp or datetime.now(timezone.utc),
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event

    def list_for_device(
        self,
        db: Session,
        device_id: int,
        limit: int = 200,
        date_start=None,
        date_end=None,
    ) -> List[DeviceEvent]:
        query = db.query(DeviceEvent).filter(DeviceEvent.device_id == device_id)

        if date_start is not None:
            query = query.filter(DeviceEvent.timestamp >= date_start)
        if date_end is not None:
            query = query.filter(DeviceEvent.timestamp <= date_end)

        return query.order_by(DeviceEvent.timestamp.desc()).limit(limit).all()
