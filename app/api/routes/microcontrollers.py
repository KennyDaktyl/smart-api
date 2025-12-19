from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from smart_common.core.db import get_db
from smart_common.core.dependencies import get_current_user
from smart_common.models.user import User
from smart_common.repositories.installation import InstallationRepository
from smart_common.repositories.microcontroller import MicrocontrollerRepository
from smart_common.schemas.microcontrollers import (MicrocontrollerCreateRequest,
                                                   MicrocontrollerResponse,
                                                   MicrocontrollerStatusRequest,
                                                   MicrocontrollerUpdateRequest)
from smart_common.services.microcontroller_service import MicrocontrollerService

router = APIRouter(
    prefix="/installations/{installation_id}/microcontrollers", tags=["Microcontrollers"]
)

microcontroller_service = MicrocontrollerService(
    lambda db: MicrocontrollerRepository(db),
    lambda db: InstallationRepository(db),
)


def _ensure_installation_matches(installation_id: int, microcontroller) -> None:
    if microcontroller.installation_id != installation_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Microcontroller not found"
        )


@router.get(
    "/",
    response_model=list[MicrocontrollerResponse],
    status_code=200,
    summary="List microcontrollers",
    description="Lists all microcontrollers registered under the requested installation.",
)
def list_microcontrollers(
    installation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MicrocontrollerResponse]:
    return microcontroller_service.list_for_installation(db, current_user.id, installation_id)


@router.post(
    "/",
    response_model=MicrocontrollerResponse,
    status_code=201,
    summary="Register microcontroller",
    description="Registers a new microcontroller for the installation owned by the user.",
)
def register_microcontroller(
    installation_id: int,
    payload: MicrocontrollerCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MicrocontrollerResponse:
    return microcontroller_service.register_microcontroller(
        db, current_user.id, installation_id, payload.model_dump()
    )


@router.put(
    "/{microcontroller_uuid}",
    response_model=MicrocontrollerResponse,
    status_code=200,
    summary="Update microcontroller",
    description="Updates the metadata of a microcontroller that belongs to the user.",
)
def update_microcontroller(
    installation_id: int,
    microcontroller_uuid: UUID,
    payload: MicrocontrollerUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MicrocontrollerResponse:
    microcontroller = microcontroller_service.get_owned(db, current_user.id, microcontroller_uuid)
    _ensure_installation_matches(installation_id, microcontroller)
    return microcontroller_service.update(
        db, current_user.id, microcontroller_uuid, payload.model_dump(exclude_unset=True)
    )


@router.patch(
    "/{microcontroller_uuid}/status",
    response_model=MicrocontrollerResponse,
    status_code=200,
    summary="Enable/disable microcontroller",
    description="Toggles the enabled flag for a microcontroller owned by the user.",
)
def set_microcontroller_status(
    installation_id: int,
    microcontroller_uuid: UUID,
    payload: MicrocontrollerStatusRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MicrocontrollerResponse:
    microcontroller = microcontroller_service.get_owned(db, current_user.id, microcontroller_uuid)
    _ensure_installation_matches(installation_id, microcontroller)
    return microcontroller_service.set_enabled(
        db, current_user.id, microcontroller_uuid, payload.enabled
    )
