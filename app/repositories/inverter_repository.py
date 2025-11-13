from typing import List, Optional

from sqlalchemy.orm import Session, joinedload

from app.models.inverter import Inverter
from app.repositories.base_repository import BaseRepository


class InverterRepository(BaseRepository[Inverter]):
    def __init__(self):
        super().__init__(Inverter)

    def get_by_installation(self, db: Session, installation_id: int) -> List[Inverter]:
        return db.query(Inverter).filter(Inverter.installation_id == installation_id).all()

    def get_by_serial(self, db: Session, serial_number: str) -> Optional[Inverter]:
        return db.query(Inverter).filter(Inverter.serial_number == serial_number).first()

    def get_for_user(self, db: Session, user_id: int) -> List[Inverter]:
        return (
            db.query(Inverter)
            .join(Inverter.installation)
            .filter_by(user_id=user_id)
            .options(joinedload(Inverter.installation))
            .all()
        )

    def get_for_user_by_id(self, db: Session, inverter_id: int, user_id: int) -> Optional[Inverter]:
        return (
            db.query(Inverter)
            .join(Inverter.installation)
            .filter(Inverter.id == inverter_id, Inverter.installation.has(user_id=user_id))
            .first()
        )

    def update_for_user(
        self, db: Session, inverter_id: int, user_id: int, data: dict
    ) -> Optional[Inverter]:
        inverter = self.get_for_user_by_id(db, inverter_id, user_id)
        if not inverter:
            return None

        for field, value in data.items():
            setattr(inverter, field, value)
        db.commit()
        db.refresh(inverter)
        return inverter

    def delete_for_user(self, db: Session, inverter_id: int, user_id: int) -> bool:
        inverter = self.get_for_user_by_id(db, inverter_id, user_id)
        if not inverter:
            return False
        db.delete(inverter)
        db.commit()
        return True
