# app/repositories/user_repository.py
from typing import List, Optional

from sqlalchemy.orm import Session, joinedload

from app.models.device import Device
from app.models.installation import Installation
from app.models.inverter import Inverter
from app.models.raspberry import Raspberry
from app.models.user import User
from app.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self):
        super().__init__(User)

    def get_by_email(self, db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

    def activate_user(self, db: Session, user: User) -> User:
        user.is_active = True
        db.commit()
        db.refresh(user)
        return user

    def update_password(self, db: Session, user: User, password_hash: str) -> User:
        user.password_hash = password_hash
        user.is_active = True
        db.commit()
        db.refresh(user)
        return user

    def get_user_installations_details(self, db: Session, user_id: int) -> Optional[User]:
        return (
            db.query(User)
            .options(
                joinedload(User.installations)
                .joinedload(Installation.inverters)
                .joinedload(Inverter.raspberries)
                .joinedload(Raspberry.devices)
            )
            .filter(User.id == user_id)
            .first()
        )

    def get_all_with_installations_and_inverters(self, db: Session) -> List[User]:
        return (
            db.query(User)
            .options(joinedload(User.installations).joinedload(Installation.inverters))
            .all()
        )
