import logging
import secrets
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.constans.role import UserRole
from app.core.db import get_db
from app.core.dependencies import get_current_user
from app.core.roles import require_role
from app.core.security import get_password_hash
from app.repositories.raspberry_repository import RaspberryRepository
from app.schemas.raspberry_schema import (RaspberryCreate, RaspberryCreateOut, RaspberryOut,
                                          RaspberryUpdate)
from app.models.user import User

router = APIRouter(prefix="/raspberries", tags=["Raspberry"])
logger = logging.getLogger(__name__)

raspberry_repo = RaspberryRepository()


@router.get(
    "/", response_model=list[RaspberryOut], dependencies=[Depends(require_role(UserRole.ADMIN))]
)
def list_raspberries(db: Session = Depends(get_db)):
    """Zwraca wszystkie Raspberry — tylko dla administratora."""
    return raspberry_repo.get_all(db)


@router.get("/me", response_model=list[RaspberryOut])
def list_my_raspberries(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Zwraca Raspberry przypisane do aktualnego użytkownika."""
    return raspberry_repo.get_for_user(db, current_user.id)


@router.get("/{raspberry_uuid}", response_model=RaspberryOut)
def get_raspberry_detail(
    raspberry_uuid: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    raspberry = raspberry_repo.get_for_user_by_uuid(db, raspberry_uuid, current_user.id)

    if not raspberry and current_user.role == UserRole.ADMIN:
        raspberry = raspberry_repo.get_by_uuid(db, raspberry_uuid)

    if not raspberry:
        raise HTTPException(status_code=404, detail="Raspberry not found")

    if current_user.role != UserRole.ADMIN and raspberry.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return raspberry


@router.post("/", response_model=RaspberryCreateOut)
def create_raspberry(
    payload: RaspberryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Tworzy nowe Raspberry i zwraca jednorazowo plaintext secret."""
    if current_user.role != UserRole.ADMIN and payload.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    secret_plain = secrets.token_urlsafe(32)
    hashed_secret = get_password_hash(secret_plain)

    raspberry_data = payload.model_dump()
    raspberry_data["secret_key"] = hashed_secret

    raspberry = raspberry_repo.create(db, raspberry_data)
    logger.info(f"✅ Raspberry created: {raspberry.uuid}")

    return {
        "id": raspberry.id,
        "uuid": raspberry.uuid,
        "name": raspberry.name,
        "description": raspberry.description,
        "software_version": raspberry.software_version,
        "max_devices": raspberry.max_devices,
        "user_id": raspberry.user_id,
        "inverter_id": raspberry.inverter_id,
        "secret_plain": secret_plain,
    }


@router.put("/{raspberry_uuid}", response_model=RaspberryOut)
def update_raspberry(
    raspberry_uuid: UUID,
    payload: RaspberryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Aktualizuje istniejące Raspberry."""
    update_data = payload.model_dump(exclude_unset=True)
    update_data["last_seen"] = datetime.now(timezone.utc)

    raspberry = raspberry_repo.update_for_user(db, raspberry_uuid, current_user.id, update_data)
    if not raspberry:
        raise HTTPException(status_code=404, detail="Raspberry not found")

    return raspberry


@router.delete("/{raspberry_uuid}")
def delete_raspberry(
    raspberry_uuid: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Usuwa Raspberry — admin lub właściciel."""
    deleted = raspberry_repo.delete_for_user(db, raspberry_uuid, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Raspberry not found")

    return {"message": "Raspberry deleted successfully"}
