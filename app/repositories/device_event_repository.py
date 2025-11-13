from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import DeviceEvent


class DeviceEventRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_event(
        self, device_id: int, active_power: float, event_name="production_update", state="active"
    ):
        event = DeviceEvent(
            event_name=event_name,
            device_id=device_id,
            state=state,
            active_power=active_power,
            timestamp=datetime.now(timezone.utc),
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event
