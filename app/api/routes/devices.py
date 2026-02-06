import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from smart_common.core.db import get_db
from smart_common.core.dependencies import get_current_user
from smart_common.models.user import User
from smart_common.repositories.device import DeviceRepository
from smart_common.repositories.microcontroller import MicrocontrollerRepository
from smart_common.schemas.device_schema import (
    DeviceCreateRequest,
    DeviceUpdateRequest,
    DeviceResponse,
    DeviceSetManualStateRequest,
    DeviceManualStateResponse,
)
from smart_common.services.device_service import DeviceService

logger = logging.getLogger(__name__)

device_router = APIRouter(
    prefix="/devices",
    tags=["Devices"],
)

# =====================================================
# LIST
# =====================================================


@device_router.get("", response_model=list[DeviceResponse])
def list_devices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info("LIST devices | user_id=%s", current_user.id)

    repo = DeviceRepository(db)
    devices = repo.list_for_user(current_user.id)

    logger.debug(
        "LIST devices result | user_id=%s count=%s",
        current_user.id,
        len(devices),
    )

    return [DeviceResponse.model_validate(d, from_attributes=True) for d in devices]


# =====================================================
# DETAIL
# =====================================================


@device_router.get("/{device_id}", response_model=DeviceResponse)
def get_device_detail(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info(
        "GET device detail | device_id=%s user_id=%s",
        device_id,
        current_user.id,
    )

    repo = DeviceRepository(db)
    device = repo.get_for_user_by_id(device_id, current_user.id)

    if not device:
        logger.warning(
            "GET device detail NOT FOUND | device_id=%s user_id=%s",
            device_id,
            current_user.id,
        )
        raise HTTPException(status_code=404, detail="Device not found")

    logger.debug(
        "GET device detail OK | device_id=%s microcontroller_id=%s",
        device.id,
        device.microcontroller_id,
    )

    return DeviceResponse.model_validate(device, from_attributes=True)


# =====================================================
# CREATE
# =====================================================


@device_router.post(
    "/microcontroller/{microcontroller_uuid}",
    response_model=DeviceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_device(
    microcontroller_uuid: UUID,
    payload: DeviceCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info(
        "CREATE device | user_id=%s microcontroller_uuid=%s name=%s",
        current_user.id,
        microcontroller_uuid,
        payload.name,
    )

    logger.debug(
        "CREATE device payload | %s",
        payload.model_dump(exclude_unset=True),
    )

    service = DeviceService(DeviceRepository, MicrocontrollerRepository)

    device = await service.create_device(
        db=db,
        user_id=current_user.id,
        mc_uuid=microcontroller_uuid,
        payload=payload.model_dump(exclude_unset=True),
    )

    logger.info(
        "CREATE device OK | device_id=%s microcontroller_id=%s",
        device.id,
        device.microcontroller_id,
    )

    return DeviceResponse.model_validate(device, from_attributes=True)


# =====================================================
# UPDATE
# =====================================================


@device_router.put("/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: int,
    payload: DeviceUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info(
        "UPDATE device | device_id=%s user_id=%s",
        device_id,
        current_user.id,
    )

    logger.debug(
        "UPDATE device payload | device_id=%s data=%s",
        device_id,
        payload.model_dump(exclude_unset=True),
    )

    service = DeviceService(DeviceRepository, MicrocontrollerRepository)

    device = await service.update_device(
        db=db,
        user_id=current_user.id,
        device_id=device_id,
        payload=payload.model_dump(exclude_unset=True),
    )

    logger.info(
        "UPDATE device OK | device_id=%s mode=%s",
        device.id,
        device.mode,
    )

    return DeviceResponse.model_validate(device, from_attributes=True)


# =====================================================
# DELETE
# =====================================================


@device_router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info(
        "DELETE device | device_id=%s user_id=%s",
        device_id,
        current_user.id,
    )

    service = DeviceService(DeviceRepository, MicrocontrollerRepository)

    await service.delete_device(
        db=db,
        user_id=current_user.id,
        device_id=device_id,
    )

    logger.info(
        "DELETE device OK | device_id=%s",
        device_id,
    )


# =====================================================
# MANUAL STATE (COMMAND)
# =====================================================


@device_router.put(
    "/{device_id}/manual_state",
    response_model=DeviceManualStateResponse,
)
async def set_device_manual_state(
    device_id: int,
    payload: DeviceSetManualStateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = DeviceService(DeviceRepository, MicrocontrollerRepository)

    device_dto, ack = await service.set_manual_state(
        db=db,
        user_id=current_user.id,
        device_id=device_id,
        state=payload.state,
    )

    if ack:
        logger.info(
            "SET MANUAL STATE ACK | device_id=%s state=%s",
            device_dto.id,
            payload.state,
        )
    else:
        logger.warning(
            "SET MANUAL STATE NO ACK | device_id=%s state=%s",
            device_dto.id,
            payload.state,
        )

    return DeviceManualStateResponse(
        status="OK" if ack else "NOK",
        message=None if ack else "Microcontroller did not acknowledge command",
        device=device_dto,
    )


# =====================================================
# LIST FOR MICROCONTROLLER
# =====================================================


@device_router.get(
    "/microcontroller/{microcontroller_uuid}",
    response_model=list[DeviceResponse],
)
def list_devices_for_microcontroller(
    microcontroller_uuid: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info(
        "LIST devices for microcontroller | user_id=%s microcontroller_uuid=%s",
        current_user.id,
        microcontroller_uuid,
    )

    service = DeviceService(DeviceRepository, MicrocontrollerRepository)

    devices = service.list_for_microcontroller(
        db=db,
        user_id=current_user.id,
        mc_uuid=microcontroller_uuid,
    )

    logger.debug(
        "LIST devices for microcontroller result | mc_uuid=%s count=%s",
        microcontroller_uuid,
        len(devices),
    )

    return [DeviceResponse.model_validate(d, from_attributes=True) for d in devices]
