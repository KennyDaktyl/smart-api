from typing import Callable
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from smart_common.models.installation import Installation
from smart_common.models.microcontroller import Microcontroller
from smart_common.repositories.installation import InstallationRepository
from smart_common.repositories.microcontroller import MicrocontrollerRepository


class MicrocontrollerService:
    def __init__(
        self,
        repo_factory: Callable[[Session], MicrocontrollerRepository],
        installation_repo_factory: Callable[[Session], InstallationRepository],
    ):
        self._repo_factory = repo_factory
        self._installation_repo_factory = installation_repo_factory

    def _repo(self, db: Session) -> MicrocontrollerRepository:
        return self._repo_factory(db)

    def _installation_repo(self, db: Session) -> InstallationRepository:
        return self._installation_repo_factory(db)

    def _ensure_installation(self, db: Session, user_id: int, installation_id: int) -> Installation:
        installation = self._installation_repo(db).get_for_user_by_id(installation_id, user_id)
        if not installation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Installation not found")
        return installation

    def list_for_installation(
        self, db: Session, user_id: int, installation_id: int
    ) -> list[Microcontroller]:
        self._ensure_installation(db, user_id, installation_id)
        return (
            db.query(Microcontroller)
            .join(Microcontroller.installation)
            .filter(
                Microcontroller.installation_id == installation_id,
                Installation.user_id == user_id,
            )
            .all()
        )

    def register_microcontroller(
        self,
        db: Session,
        user_id: int,
        installation_id: int,
        payload: dict,
    ) -> Microcontroller:
        installation = self._ensure_installation(db, user_id, installation_id)

        data = {
            **payload,
            "installation_id": installation.id,
        }

        return self._repo(db).create(data)


    def update(
        self, db: Session, user_id: int, uuid: UUID, payload: dict
    ) -> Microcontroller:
        microcontroller = self._repo(db).update_for_user(uuid, user_id, payload)
        if not microcontroller:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Microcontroller not found or does not belong to user",
            )
        db.commit()
        db.refresh(microcontroller)
        return microcontroller

    def set_enabled(self, db: Session, user_id: int, uuid: UUID, enabled: bool) -> Microcontroller:
        return self.update(db, user_id, uuid, {"enabled": enabled})
