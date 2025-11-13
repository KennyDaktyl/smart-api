from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.device import Device
from app.models.device_schedule import DeviceSchedule
from app.repositories.base_repository import BaseRepository


class DeviceScheduleRepository(BaseRepository[DeviceSchedule]):
    def __init__(self):
        super().__init__(DeviceSchedule)

    def get_for_device(self, db: Session, device_id: int, user_id: int) -> List[DeviceSchedule]:
        """Zwraca harmonogramy tylko dla urządzeń danego użytkownika."""
        return (
            db.query(DeviceSchedule)
            .join(Device)
            .filter(DeviceSchedule.device_id == device_id, Device.user_id == user_id)
            .all()
        )

    def update(self, db: Session, schedule_id: int, data: dict) -> Optional[DeviceSchedule]:
        """Aktualizuje harmonogram."""
        schedule = self.get_by_id(db, schedule_id)
        if not schedule:
            return None

        for field, value in data.items():
            setattr(schedule, field, value)
        db.commit()
        db.refresh(schedule)
        return schedule
