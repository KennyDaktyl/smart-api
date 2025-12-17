from typing import Callable

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from smart_common.models.installation import Installation
from smart_common.repositories.installation import InstallationRepository


class InstallationService:
    def __init__(self, repo_factory: Callable[[Session], InstallationRepository]):
        self._repo_factory = repo_factory

    def _repo(self, db: Session) -> InstallationRepository:
        return self._repo_factory(db)

    def list_for_user(self, db: Session, user_id: int) -> list[Installation]:
        return self._repo(db).get_by_user(user_id)

    def get_for_user(self, db: Session, installation_id: int, user_id: int) -> Installation:
        installation = self._repo(db).get_for_user_by_id(installation_id, user_id)
        if not installation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Installation not found")

        return installation

    def create_for_user(self, db: Session, user_id: int, payload: dict) -> Installation:
        repo = self._repo(db)
        if repo.get_by_station_code(payload["station_code"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Installation with this station code already exists",
            )

        installation = Installation(user_id=user_id, **payload)
        repo.create(installation)
        db.commit()
        db.refresh(installation)
        return installation
