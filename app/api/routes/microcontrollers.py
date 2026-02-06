from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from smart_common.core.db import get_db
from smart_common.core.dependencies import get_current_user
from smart_common.models.user import User
from smart_common.repositories.microcontroller import MicrocontrollerRepository
from smart_common.schemas.microcontroller_schema import (
    MicrocontrollerCreateRequest,
    MicrocontrollerResponse,
    MicrocontrollerSetProviderRequest,
)

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

    repo = MicrocontrollerRepository(db)

    data = payload.model_dump(exclude_unset=True)
    data["user_id"] = current_user.id

    microcontroller = repo.create(data)

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


@microcontroller_router.put(
    "/set_provider/{microcontroller_uuid}/",
    response_model=MicrocontrollerResponse,
    summary="Set or clear power provider for microcontroller",
)
def set_microcontroller_provider(
    microcontroller_uuid: UUID,
    payload: MicrocontrollerSetProviderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MicrocontrollerResponse:
    repo = MicrocontrollerRepository(db)

    microcontroller = repo.set_power_provider_for_user(
        microcontroller_uuid=microcontroller_uuid,
        user_id=current_user.id,
        provider_uuid=payload.provider_uuid,
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
