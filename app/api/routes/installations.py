from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from smart_common.core.db import get_db
from smart_common.core.dependencies import get_current_user
from smart_common.models.user import User
from smart_common.repositories.installation import InstallationRepository
from smart_common.schemas.installations import (InstallationCreateRequest, InstallationResponse,
                                                InstallationUpdateRequest)
from smart_common.services.installation_service import InstallationService

router = APIRouter(prefix="/installations", tags=["Installations"])

installation_service = InstallationService(lambda db: InstallationRepository(db))

# ------------------------------------
# LIST
# ------------------------------------


@router.get(
    "/",
    response_model=list[InstallationResponse],
    status_code=status.HTTP_200_OK,
    summary="List user installations",
    description="Returns all active installations owned by the authenticated user.",
)
def list_installations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[InstallationResponse]:
    return installation_service.list_for_user(db, current_user.id)


# ------------------------------------
# CREATE
# ------------------------------------


@router.post(
    "/",
    response_model=InstallationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create installation",
    description="Registers a new installation under the authenticated user.",
)
def create_installation(
    payload: InstallationCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InstallationResponse:
    return installation_service.create_for_user(
        db,
        current_user.id,
        payload.model_dump(),
    )


# ------------------------------------
# GET BY ID
# ------------------------------------


@router.get(
    "/{installation_id}",
    response_model=InstallationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get installation details",
    description="Returns details for a specific installation if it belongs to the user.",
)
def get_installation(
    installation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InstallationResponse:
    return installation_service.get_for_user(
        db,
        installation_id,
        current_user.id,
    )


# ------------------------------------
# UPDATE (PATCH)
# ------------------------------------


@router.patch(
    "/{installation_id}",
    response_model=InstallationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update installation",
    description="Updates installation fields (name, address).",
)
def update_installation(
    installation_id: int,
    payload: InstallationUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InstallationResponse:
    return installation_service.update_for_user(
        db,
        installation_id,
        current_user.id,
        payload.model_dump(exclude_unset=True),
    )


# ------------------------------------
# DELETE (SOFT)
# ------------------------------------


@router.delete(
    "/{installation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete installation",
    description="Soft deletes an installation owned by the user.",
)
def delete_installation(
    installation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    installation_service.delete_for_user(
        db,
        installation_id,
        current_user.id,
    )
