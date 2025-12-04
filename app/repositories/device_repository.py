from typing import List, Optional

from sqlalchemy.orm import Session, joinedload

from app.models.device import Device
from app.repositories.base_repository import BaseRepository


class DeviceRepository(BaseRepository[Device]):
    def __init__(self):
        super().__init__(Device)

    def create(self, db: Session, obj_in: dict):
        obj = self.model(**obj_in)
        db.add(obj)
        db.flush()
        db.refresh(obj)
        return obj

    def get_for_user(self, db: Session, user_id: int) -> List[Device]:
        """Zwraca urządzenia przypisane do danego użytkownika."""
        return (
            db.query(Device)
            .filter(Device.user_id == user_id)
            .options(joinedload(Device.raspberry))
            .all()
        )

    def get_for_user_by_id(self, db: Session, device_id: int, user_id: int) -> Optional[Device]:
        """Zwraca pojedyncze urządzenie użytkownika."""
        return db.query(Device).filter(Device.id == device_id, Device.user_id == user_id).first()

    def update_for_user(
        self, db: Session, device_id: int, user_id: int, data: dict
    ) -> Optional[Device]:
        """Aktualizuje urządzenie należące do użytkownika."""
        device = self.get_for_user_by_id(db, device_id, user_id)
        if not device:
            return None

        for field, value in data.items():
            setattr(device, field, value)
        db.commit()
        db.refresh(device)
        return device

    def delete_for_user(self, db: Session, device_id: int, user_id: int) -> bool:
        """Usuwa urządzenie należące do użytkownika."""
        device = self.get_for_user_by_id(db, device_id, user_id)
        if not device:
            return False
        db.delete(device)
        db.commit()
        return True

    def get_for_raspberry(self, db: Session, raspberry_id: int, user_id: int) -> List[Device]:
        """Zwraca urządzenia użytkownika przypisane do danej Raspberry."""
        return (
            db.query(Device)
            .filter(Device.raspberry_id == raspberry_id, Device.user_id == user_id)
            .order_by(Device.id)
            .all()
        )

    def get_by_raspberry(self, db: Session, raspberry_id: int) -> List[Device]:
        """Zwraca WSZYSTKIE urządzenia (dla admina)."""
        return (
            db.query(Device).filter(Device.raspberry_id == raspberry_id).order_by(Device.id).all()
        )
