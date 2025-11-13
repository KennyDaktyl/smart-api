from typing import Generic, Type, TypeVar

from sqlalchemy.orm import Session

from app.core.db import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    def get_all(self, db: Session):
        return db.query(self.model).all()

    def get_by_id(self, db: Session, id: int):
        return db.query(self.model).filter(self.model.id == id).first()

    def create(self, db: Session, obj_in: dict):
        obj = self.model(**obj_in)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def delete(self, db: Session, id: int):
        obj = self.get_by_id(db, id)
        if obj:
            db.delete(obj)
            db.commit()
