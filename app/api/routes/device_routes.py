# app/api/routes/device_routes.py

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.constans.role import UserRole
from app.core.db import get_db
from app.core.dependencies import get_current_user
from app.core.nats_client import NatsClient
from app.core.roles import require_role
from app.repositories.device_repository import DeviceRepository
from app.schemas.device_schema import DeviceCreate, DeviceUpdate
from app.services.device_service import DeviceService
from app.models.user import User

router = APIRouter(prefix="/devices", tags=["Devices"])

device_service = DeviceService(DeviceRepository(), NatsClient())


@router.get("/", dependencies=[Depends(require_role(UserRole.ADMIN))])
def list_devices(db: Session = Depends(get_db)):
    return device_service.list_all(db)


@router.get("/me")
def list_my_devices(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return device_service.list_for_user(db, current_user.id)


@router.get("/{device_id}")
def get_device(
    device_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    return device_service.get_device(db, device_id, current_user)


@router.post("")
async def create_device(
    payload: DeviceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    data = payload.model_dump()
    data["user_id"] = current_user.id
    return await device_service.create_device(db, data)


@router.put("/{device_id}")
def update_device(
    device_id: int,
    payload: DeviceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = payload.model_dump(exclude_unset=True)
    data["last_update"] = datetime.now(timezone.utc)
    return device_service.update_device(db, device_id, current_user.id, data)


@router.patch("/{device_id}/manual_state")
async def set_manual_state(
    device_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if "state" not in payload:
        raise HTTPException(400, "Missing 'state' field")

    return await device_service.set_manual_state(db, device_id, current_user, payload["state"])


@router.get("/raspberry/{raspberry_id}")
def list_devices_for_raspberry(
    raspberry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    device_repo = DeviceRepository()
    return device_repo.get_for_raspberry(
        db=db,
        raspberry_id=raspberry_id,
        user_id=current_user.id
    )