from typing import Generic, Type, TypeVar

from sqlalchemy.orm import Session

from app.core.db import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    def get_all(
        self,
        db: Session,
        *,
        limit: int | None = None,
        offset: int | None = None
    ):
        query = db.query(self.model)

        if offset not in (None, 0):
            query = query.offset(offset)

        if limit is not None:
            query = query.limit(limit)

        return query.all()

    def get_all_with_count(
        self,
        db: Session,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ):
        base_query = db.query(self.model)
        total = base_query.count()
        query = base_query

        if offset is not None:
            query = query.offset(offset)

        if limit is not None:
            query = query.limit(limit)

        items = query.all()
        return items, total

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
            return True
        return False
