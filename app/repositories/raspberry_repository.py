from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.raspberry import Raspberry
from app.repositories.base_repository import BaseRepository


class RaspberryRepository(BaseRepository[Raspberry]):
    def __init__(self):
        super().__init__(Raspberry)

    def get_by_uuid(self, db: Session, uuid: UUID) -> Optional[Raspberry]:
        return db.query(Raspberry).filter(Raspberry.uuid == uuid).first()

    def get_for_user(self, db: Session, user_id: int) -> List[Raspberry]:
        return db.query(Raspberry).filter(Raspberry.user_id == user_id).all()

    def get_for_user_by_uuid(self, db: Session, uuid: UUID, user_id: int) -> Optional[Raspberry]:
        return (
            db.query(Raspberry).filter(Raspberry.uuid == uuid, Raspberry.user_id == user_id).first()
        )

    def update_for_user(
        self, db: Session, uuid: UUID, user_id: int, data: dict
    ) -> Optional[Raspberry]:
        raspberry = self.get_for_user_by_uuid(db, uuid, user_id)
        if not raspberry:
            return None

        for field, value in data.items():
            setattr(raspberry, field, value)
        db.commit()
        db.refresh(raspberry)
        return raspberry

    def delete_for_user(self, db: Session, uuid: UUID, user_id: int) -> bool:
        raspberry = self.get_for_user_by_uuid(db, uuid, user_id)
        if not raspberry:
            return False
        db.delete(raspberry)
        db.commit()
        return True

    def mark_online(self, db: Session, uuid: UUID, system_info: dict | None = None):
        raspberry = self.get_by_uuid(db, uuid)
        if not raspberry:
            return None
        raspberry.is_online = True
        raspberry.last_seen = datetime.now(timezone.utc)
        if system_info:
            raspberry.system_info = system_info
        db.commit()
        return raspberry
