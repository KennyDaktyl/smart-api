from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from smart_common.core.db import get_db
from smart_common.core.dependencies import get_current_user
from smart_common.models.device import Device
from smart_common.models.user import User
from smart_common.repositories.device import DeviceRepository
from smart_common.repositories.microcontroller import MicrocontrollerRepository
from smart_common.schemas.devices import DeviceCreateRequest, DeviceResponse, DeviceUpdateRequest
from smart_common.services.device_service import DeviceService

router = APIRouter(
    prefix="/installations/{installation_id}/microcontrollers/{microcontroller_uuid}/devices",
    tags=["Devices"],
)

device_service = DeviceService(
    lambda db: DeviceRepository(db),
    lambda db: MicrocontrollerRepository(db),
)


def _validate_microcontroller(
    db: Session, installation_id: int, microcontroller_uuid: UUID, user_id: int
):
    repo = MicrocontrollerRepository(db)
    microcontroller = repo.get_for_user_by_uuid(microcontroller_uuid, user_id)
    if not microcontroller or microcontroller.installation_id != installation_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Microcontroller not found"
        )
    return microcontroller


def _ensure_device_belongs_to(mc_id: int, device: Device):
    if device.microcontroller_id != mc_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found for the selected microcontroller",
        )


@router.get(
    "/",
    response_model=list[DeviceResponse],
    status_code=200,
    summary="List devices",
    description="Lists all devices attached to the selected microcontroller.",
)
def list_devices(
    installation_id: int,
    microcontroller_uuid: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DeviceResponse]:
    _validate_microcontroller(db, installation_id, microcontroller_uuid, current_user.id)
    return device_service.list_for_microcontroller(db, current_user.id, microcontroller_uuid)


@router.post(
    "/",
    response_model=DeviceResponse,
    status_code=201,
    summary="Create device",
    description="Registers a new device under the selected microcontroller.",
)
async def create_device(
    installation_id: int,
    microcontroller_uuid: UUID,
    payload: DeviceCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DeviceResponse:
    _validate_microcontroller(db, installation_id, microcontroller_uuid, current_user.id)
    return await device_service.create_device(
        db, current_user.id, microcontroller_uuid, payload.model_dump()
    )


@router.put(
    "/{device_id}",
    response_model=DeviceResponse,
    status_code=200,
    summary="Update device",
    description="Updates a device assigned to the microcontroller.",
)
async def update_device(
    installation_id: int,
    microcontroller_uuid: UUID,
    device_id: int,
    payload: DeviceUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DeviceResponse:
    microcontroller = _validate_microcontroller(
        db, installation_id, microcontroller_uuid, current_user.id
    )
    device = device_service.get_device(db, device_id, current_user.id)
    _ensure_device_belongs_to(microcontroller.id, device)
    return await device_service.update_device(
        db, current_user.id, device_id, payload.model_dump(exclude_unset=True)
    )


@router.delete(
    "/{device_id}",
    status_code=204,
    summary="Delete device",
    description="Deletes a device that belongs to the chosen microcontroller.",
)
async def delete_device(
    installation_id: int,
    microcontroller_uuid: UUID,
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    microcontroller = _validate_microcontroller(
        db, installation_id, microcontroller_uuid, current_user.id
    )
    device = device_service.get_device(db, device_id, current_user.id)
    _ensure_device_belongs_to(microcontroller.id, device)
    await device_service.delete_device(db, current_user.id, device_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
