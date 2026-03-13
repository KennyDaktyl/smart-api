from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from smart_common.core.db import get_db
from smart_common.core.dependencies import get_current_user
from smart_common.models.user import User
from smart_common.repositories.microcontroller import MicrocontrollerRepository
from smart_common.repositories.provider import ProviderRepository
from smart_common.schemas.microcontroller_schema import (
    MicrocontrollerCreateRequest,
    MicrocontrollerResponse,
    MicrocontrollerSetProviderRequest,
    MicrocontrollerUpdateRequest,
)
from smart_common.services.microcontroller_service import MicrocontrollerService

logger = logging.getLogger(__name__)

microcontroller_router = APIRouter(
    prefix="/microcontrollers",
    tags=["Microcontrollers"],
)

# =====================================================
# LIST FOR CURRENT USER
# =====================================================


@microcontroller_router.get(
    "/get_for_user",
    response_model=list[MicrocontrollerResponse],
)
def list_user_microcontrollers_legacy(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = MicrocontrollerRepository(db)
    microcontrollers = repo.get_for_user(user_id=current_user.id)

    return [
        MicrocontrollerResponse.model_validate(m, from_attributes=True)
        for m in microcontrollers
    ]


# =====================================================
# DETAILS
# =====================================================


@microcontroller_router.get(
    "/details/{microcontroller_uuid}",
    response_model=MicrocontrollerResponse,
    summary="Get microcontroller details",
)
def get_microcontroller(
    microcontroller_uuid: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MicrocontrollerResponse:
    repo = MicrocontrollerRepository(db)

    microcontroller = repo.get_for_user_by_uuid(
        uuid=microcontroller_uuid,
        user_id=current_user.id,
    )

    if not microcontroller:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Microcontroller not found",
        )

    return MicrocontrollerResponse.model_validate(
        microcontroller,
        from_attributes=True,
    )


# =====================================================
# CREATE
# =====================================================


@microcontroller_router.post(
    "",
    response_model=MicrocontrollerResponse,
    status_code=201,
    summary="Create microcontroller",
)
def create_microcontroller(
    payload: MicrocontrollerCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MicrocontrollerResponse:
    logger.info(
        "Creating microcontroller",
        extra={
            "user_id": current_user.id,
            "name": payload.name,
        },
    )

    data = payload.model_dump(exclude_unset=True)
    service = MicrocontrollerService(repo_factory=MicrocontrollerRepository)
    microcontroller = service.register_microcontroller_for_user(
        db,
        user_id=current_user.id,
        payload=data,
    )

    return MicrocontrollerResponse.model_validate(
        microcontroller,
        from_attributes=True,
    )


# =====================================================
# DELETE
# =====================================================


@microcontroller_router.delete(
    "/delete/{microcontroller_uuid}",
    status_code=204,
    summary="Delete microcontroller",
)
def delete_microcontroller(
    microcontroller_uuid: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    repo = MicrocontrollerRepository(db)

    deleted = repo.delete_for_user(
        uuid=microcontroller_uuid,
        user_id=current_user.id,
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Microcontroller not found",
        )


@microcontroller_router.patch(
    "/{microcontroller_uuid}",
    response_model=MicrocontrollerResponse,
    summary="Update microcontroller",
)
async def update_microcontroller(
    microcontroller_uuid: UUID,
    payload: MicrocontrollerUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MicrocontrollerResponse:
    service = MicrocontrollerService(repo_factory=MicrocontrollerRepository)

    data = payload.model_dump(exclude_unset=True)
    assigned_sensors = data.pop("assigned_sensors", None)

    microcontroller = service.update_microcontroller_for_user(
        db,
        microcontroller_uuid=microcontroller_uuid,
        user_id=current_user.id,
        data=data,
        assigned_sensors=assigned_sensors,
    )

    if assigned_sensors is not None or "max_devices" in data:
        await service.sync_agent_config_from_microcontroller(
            db,
            microcontroller=microcontroller,
        )

    return MicrocontrollerResponse.model_validate(
        microcontroller,
        from_attributes=True,
    )


@microcontroller_router.put(
    "/set_provider/{microcontroller_uuid}/",
    response_model=MicrocontrollerResponse,
    summary="Set or clear power provider for microcontroller",
)
async def set_microcontroller_provider(
    microcontroller_uuid: UUID,
    payload: MicrocontrollerSetProviderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MicrocontrollerResponse:
    service = MicrocontrollerService(
        repo_factory=MicrocontrollerRepository,
        provider_repo_factory=ProviderRepository,
    )

    microcontroller = await service.set_power_provider(
        db=db,
        microcontroller_uuid=microcontroller_uuid,
        user_id=current_user.id,
        provider_uuid=payload.provider_uuid,
    )

    return MicrocontrollerResponse.model_validate(
        microcontroller,
        from_attributes=True,
    )
