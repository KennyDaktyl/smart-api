from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from smart_common.core.db import get_db
from smart_common.core.dependencies import get_current_user
from smart_common.models.user import User
from smart_common.repositories.device import DeviceRepository
from smart_common.repositories.device_auto_config import DeviceAutoConfigRepository
from smart_common.repositories.microcontroller import MicrocontrollerRepository
from smart_common.repositories.provider import ProviderRepository
from smart_common.schemas.device_auto_config import (DeviceAutoConfigRequest,
                                                     DeviceAutoConfigResponse,
                                                     DeviceAutoConfigStatusRequest)
from smart_common.services.device_auto_config_service import DeviceAutoConfigService

router = APIRouter(
    prefix="/installations/{installation_id}/microcontrollers/{microcontroller_uuid}/devices/{device_id}/auto-config",
    tags=["Device Auto Config"],
)

service = DeviceAutoConfigService(
    lambda db: DeviceAutoConfigRepository(db),
    lambda db: DeviceRepository(db),
    lambda db: ProviderRepository(db),
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Microcontroller not found"
        )
    return microcontroller


@router.get(
    "/",
    response_model=DeviceAutoConfigResponse,
    status_code=200,
    summary="Get AUTO configuration",
    description="Returns the AUTO configuration for the selected device.",
)
def get_auto_config(
    installation_id: int,
    microcontroller_uuid: UUID,
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DeviceAutoConfigResponse:
    microcontroller = _validate_microcontroller(
        db, installation_id, microcontroller_uuid, current_user.id
    )
    config = service.get_config(db, current_user.id, device_id, microcontroller.id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="AUTO configuration not found"
        )
    return config


@router.post(
    "/",
    response_model=DeviceAutoConfigResponse,
    status_code=201,
    summary="Create or update AUTO configuration",
    description="Creates or replaces AUTO configuration for the device.",
)
def create_auto_config(
    installation_id: int,
    microcontroller_uuid: UUID,
    device_id: int,
    payload: DeviceAutoConfigRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DeviceAutoConfigResponse:
    microcontroller = _validate_microcontroller(
        db, installation_id, microcontroller_uuid, current_user.id
    )
    return service.create_or_update(
        db, current_user.id, device_id, microcontroller.id, payload.model_dump()
    )


@router.put(
    "/",
    response_model=DeviceAutoConfigResponse,
    status_code=200,
    summary="Update AUTO configuration",
    description="Updates the existing AUTO configuration for the device.",
)
def update_auto_config(
    installation_id: int,
    microcontroller_uuid: UUID,
    device_id: int,
    payload: DeviceAutoConfigRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DeviceAutoConfigResponse:
    microcontroller = _validate_microcontroller(
        db, installation_id, microcontroller_uuid, current_user.id
    )
    return service.create_or_update(
        db, current_user.id, device_id, microcontroller.id, payload.model_dump()
    )


@router.patch(
    "/status",
    response_model=DeviceAutoConfigResponse,
    status_code=200,
    summary="Enable/disable AUTO configuration",
    description="Toggles the AUTO mode for the device.",
)
def set_auto_config_status(
    installation_id: int,
    microcontroller_uuid: UUID,
    device_id: int,
    payload: DeviceAutoConfigStatusRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DeviceAutoConfigResponse:
    microcontroller = _validate_microcontroller(
        db, installation_id, microcontroller_uuid, current_user.id
    )
    return service.set_enabled(db, current_user.id, device_id, microcontroller.id, payload.enabled)
