# app/repositories/user_repository.py

from typing import List, Optional

from sqlalchemy.orm import Session, joinedload

from app.models.installation import Installation
from app.models.user import User
from app.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self):
        super().__init__(User)

    def get_by_email(self, db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

    def get_with_installations_and_inverters(self, db: Session, user_id: int) -> Optional[User]:
        return (
            db.query(User)
            .options(joinedload(User.installations).joinedload(Installation.inverters))
            .filter(User.id == user_id)
            .first()
        )

    def get_all_with_installations_and_inverters(self, db: Session) -> List[User]:
        return (
            db.query(User)
            .options(joinedload(User.installations).joinedload(Installation.inverters))
            .all()
        )
