from typing import Callable
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from smart_common.models.provider import Provider
from smart_common.repositories.microcontroller import MicrocontrollerRepository
from smart_common.repositories.provider import ProviderRepository


class ProviderService:
    def __init__(
        self,
        provider_repo_factory: Callable[[Session], ProviderRepository],
        microcontroller_repo_factory: Callable[[Session], MicrocontrollerRepository],
    ):
        self._provider_repo_factory = provider_repo_factory
        self._microcontroller_repo_factory = microcontroller_repo_factory

    def _repo(self, db: Session) -> ProviderRepository:
        return self._provider_repo_factory(db)

    def _microcontroller_repo(self, db: Session) -> MicrocontrollerRepository:
        return self._microcontroller_repo_factory(db)

    def _ensure_microcontroller(self, db: Session, user_id: int, mc_uuid: UUID) -> int:
        microcontroller = self._microcontroller_repo(db).get_for_user_by_uuid(mc_uuid, user_id)
        if not microcontroller:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Microcontroller not found")
        return microcontroller.id

    def list_for_microcontroller(
        self, db: Session, user_id: int, mc_uuid: UUID
    ) -> list[Provider]:
        microcontroller_id = self._ensure_microcontroller(db, user_id, mc_uuid)
        return (
            db.query(Provider)
            .filter(Provider.microcontroller_id == microcontroller_id)
            .all()
        )

    def create(
        self, db: Session, user_id: int, mc_uuid: UUID, payload: dict
    ) -> Provider:
        microcontroller_id = self._ensure_microcontroller(db, user_id, mc_uuid)
        if payload.get("min_value") is None or payload.get("max_value") is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Both min_value and max_value must be provided",
            )

        provider = Provider(microcontroller_id=microcontroller_id, **payload)
        self._repo(db).create(provider)
        db.commit()
        db.refresh(provider)
        return provider

    def _ensure_provider(self, db: Session, user_id: int, provider_id: int) -> Provider:
        provider = self._repo(db).get_for_user(provider_id, user_id)
        if not provider:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
        return provider

    def update(self, db: Session, user_id: int, provider_id: int, payload: dict) -> Provider:
        provider = self._ensure_provider(db, user_id, provider_id)
        changes = {k: v for k, v in payload.items() if v is not None}
        if not changes:
            return provider

        for attr, value in changes.items():
            setattr(provider, attr, value)

        self._repo(db).update(provider)
        db.commit()
        db.refresh(provider)
        return provider

    def set_enabled(self, db: Session, user_id: int, provider_id: int, enabled: bool) -> Provider:
        provider = self._ensure_provider(db, user_id, provider_id)
        provider.enabled = enabled
        db.commit()
        db.refresh(provider)
        return provider

    def get_provider(self, db: Session, user_id: int, provider_id: int) -> Provider:
        return self._ensure_provider(db, user_id, provider_id)
