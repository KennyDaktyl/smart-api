from typing import List, Optional

from sqlalchemy.orm import Session, joinedload

from app.models.installation import Installation
from app.repositories.base_repository import BaseRepository


class InstallationRepository(BaseRepository[Installation]):
    def __init__(self):
        super().__init__(Installation)

    def get_by_user(self, db: Session, user_id: int) -> List[Installation]:
        return (
            db.query(Installation)
            .filter(Installation.user_id == user_id)
            .options(joinedload(Installation.inverters))
            .all()
        )

    def get_by_station_code(self, db: Session, station_code: str) -> Optional[Installation]:
        return db.query(Installation).filter(Installation.station_code == station_code).first()

    def get_for_user_by_id(
        self, db: Session, installation_id: int, user_id: int
    ) -> Optional[Installation]:
        return (
            db.query(Installation)
            .filter(Installation.id == installation_id, Installation.user_id == user_id)
            .first()
        )

    def update_for_user(
        self, db: Session, installation_id: int, user_id: int, data: dict
    ) -> Optional[Installation]:
        installation = self.get_for_user_by_id(db, installation_id, user_id)
        if not installation:
            return None

        for field, value in data.items():
            setattr(installation, field, value)
        db.commit()
        db.refresh(installation)
        return installation

    def delete_for_user(self, db: Session, installation_id: int, user_id: int) -> bool:
        installation = self.get_for_user_by_id(db, installation_id, user_id)
        if not installation:
            return False
        db.delete(installation)
        db.commit()
        return True
