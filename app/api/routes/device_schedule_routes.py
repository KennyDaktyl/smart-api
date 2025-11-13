import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.constans.role import UserRole
from app.core.db import get_db
from app.core.dependencies import get_current_user
from app.core.roles import require_role
from app.models.device_schedule import DeviceSchedule
from app.models.user import User
from app.repositories.device_schedule_repository import DeviceScheduleRepository
from app.schemas.device_schedule_schema import (DeviceScheduleCreate, DeviceScheduleOut,
                                                DeviceScheduleUpdate)

router = APIRouter(prefix="/devices/schedules", tags=["Device Schedules"])
logger = logging.getLogger(__name__)

schedule_repo = DeviceScheduleRepository()


@router.get(
    "/",
    response_model=list[DeviceScheduleOut],
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def list_all_schedules(db: Session = Depends(get_db)):
    return schedule_repo.get_all(db)


@router.get("/device/{device_id}", response_model=list[DeviceScheduleOut])
def list_device_schedules(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return schedule_repo.get_for_device(db, device_id, current_user.id)


@router.post("/", response_model=DeviceScheduleOut)
def create_schedule(
    payload: DeviceScheduleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    schedule: DeviceSchedule = schedule_repo.create(db, payload.model_dump())
    logger.info(f"✅ Schedule created for device {schedule.device_id}")
    return schedule


@router.put("/{schedule_id}", response_model=DeviceScheduleOut)
def update_schedule(
    schedule_id: int,
    payload: DeviceScheduleUpdate,
    db: Session = Depends(get_db),
):
    """Aktualizuje harmonogram."""
    update_data = payload.model_dump(exclude_unset=True)
    schedule = schedule_repo.update(db, schedule_id, update_data)

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    return schedule


@router.delete("/{schedule_id}")
def delete_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
):
    """Usuwa harmonogram."""
    deleted = schedule_repo.delete(db, schedule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Schedule not found")

    return {"message": "Schedule deleted successfully"}
