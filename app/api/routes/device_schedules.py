from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from smart_common.core.db import get_db
from smart_common.models.user import User
from smart_common.repositories.device import DeviceRepository
from smart_common.repositories.device_schedule import DeviceScheduleRepository
from smart_common.repositories.microcontroller import MicrocontrollerRepository

from app.api.schemas.device_schedules import (
    DeviceScheduleCreateRequest,
    DeviceScheduleResponse,
    DeviceScheduleUpdateRequest,
)
from app.core.dependencies import get_current_user
from app.services.device_schedule_service import DeviceScheduleService

router = APIRouter(
    prefix="/installations/{installation_id}/microcontrollers/{microcontroller_uuid}/devices/{device_id}/schedules",
    tags=["Device Schedules"],
)

service = DeviceScheduleService(
    lambda db: DeviceScheduleRepository(db),
    lambda db: DeviceRepository(db),
)


def _validate_microcontroller(
    db: Session,
    installation_id: int,
    microcontroller_uuid: UUID,
    user_id: int,
):
    repo = MicrocontrollerRepository(db)
    microcontroller = repo.get_for_user_by_uuid(microcontroller_uuid, user_id)
    if not microcontroller or microcontroller.installation_id != installation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Microcontroller not found")
    return microcontroller


@router.get(
    "/",
    response_model=list[DeviceScheduleResponse],
    status_code=200,
    summary="List device schedules",
    description="Returns configured schedules for the selected device.",
)
def list_schedules(
    installation_id: int,
    microcontroller_uuid: UUID,
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DeviceScheduleResponse]:
    microcontroller = _validate_microcontroller(
        db, installation_id, microcontroller_uuid, current_user.id
    )
    return service.list_for_device(
        db, current_user.id, device_id, microcontroller.id
    )


@router.post(
    "/",
    response_model=DeviceScheduleResponse,
    status_code=201,
    summary="Create schedule",
    description="Creates a new schedule for the selected device.",
)
def create_schedule(
    installation_id: int,
    microcontroller_uuid: UUID,
    device_id: int,
    payload: DeviceScheduleCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DeviceScheduleResponse:
    microcontroller = _validate_microcontroller(
        db, installation_id, microcontroller_uuid, current_user.id
    )
    return service.create_schedule(
        db, current_user.id, microcontroller.id, payload.model_dump()
    )


@router.put(
    "/{schedule_id}",
    response_model=DeviceScheduleResponse,
    status_code=200,
    summary="Update schedule",
    description="Updates an existing schedule for the device.",
)
def update_schedule(
    installation_id: int,
    microcontroller_uuid: UUID,
    device_id: int,
    schedule_id: int,
    payload: DeviceScheduleUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DeviceScheduleResponse:
    microcontroller = _validate_microcontroller(
        db, installation_id, microcontroller_uuid, current_user.id
    )
    return service.update_schedule(
        db,
        current_user.id,
        microcontroller.id,
        schedule_id,
        payload.model_dump(exclude_unset=True),
    )


@router.delete(
    "/{schedule_id}",
    status_code=204,
    summary="Delete schedule",
    description="Deletes the requested schedule.",
)
def delete_schedule(
    installation_id: int,
    microcontroller_uuid: UUID,
    device_id: int,
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    microcontroller = _validate_microcontroller(
        db, installation_id, microcontroller_uuid, current_user.id
    )
    service.delete_schedule(db, current_user.id, microcontroller.id, schedule_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
