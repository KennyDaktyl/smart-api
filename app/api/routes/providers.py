from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from smart_common.core.db import get_db
from smart_common.models.user import User
from smart_common.repositories.microcontroller import MicrocontrollerRepository
from smart_common.repositories.provider import ProviderRepository

from app.api.schemas.providers import (
    ProviderCreateRequest,
    ProviderResponse,
    ProviderStatusRequest,
    ProviderUpdateRequest,
)
from app.core.dependencies import get_current_user
from app.services.provider_service import ProviderService

router = APIRouter(prefix="/installations/{installation_id}/microcontrollers/{microcontroller_uuid}/providers", tags=["Providers"])

provider_service = ProviderService(
    lambda db: ProviderRepository(db),
    lambda db: MicrocontrollerRepository(db),
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
    response_model=list[ProviderResponse],
    status_code=200,
    summary="List providers",
    description="Lists all providers configured for the selected microcontroller.",
)
def list_providers(
    installation_id: int,
    microcontroller_uuid: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ProviderResponse]:
    _validate_microcontroller(db, installation_id, microcontroller_uuid, current_user.id)
    return provider_service.list_for_microcontroller(db, current_user.id, microcontroller_uuid)


@router.post(
    "/",
    response_model=ProviderResponse,
    status_code=201,
    summary="Create provider",
    description="Creates a new provider attached to the specified microcontroller.",
)
def create_provider(
    installation_id: int,
    microcontroller_uuid: UUID,
    payload: ProviderCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProviderResponse:
    _validate_microcontroller(db, installation_id, microcontroller_uuid, current_user.id)
    return provider_service.create(db, current_user.id, microcontroller_uuid, payload.model_dump())


@router.patch(
    "/{provider_id}",
    response_model=ProviderResponse,
    status_code=200,
    summary="Update provider",
    description="Updates provider metadata and polling parameters.",
)
def update_provider(
    installation_id: int,
    microcontroller_uuid: UUID,
    provider_id: int,
    payload: ProviderUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProviderResponse:
    microcontroller = _validate_microcontroller(db, installation_id, microcontroller_uuid, current_user.id)
    provider = provider_service.get_provider(db, current_user.id, provider_id)
    if provider.microcontroller_id != microcontroller.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")

    return provider_service.update(
        db, current_user.id, provider_id, payload.model_dump(exclude_unset=True)
    )


@router.patch(
    "/{provider_id}/status",
    response_model=ProviderResponse,
    status_code=200,
    summary="Enable/disable provider",
    description="Toggles whether the provider is allowed to emit measurements.",
)
def set_provider_status(
    installation_id: int,
    microcontroller_uuid: UUID,
    provider_id: int,
    payload: ProviderStatusRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProviderResponse:
    microcontroller = _validate_microcontroller(db, installation_id, microcontroller_uuid, current_user.id)
    provider = provider_service.get_provider(db, current_user.id, provider_id)
    if provider.microcontroller_id != microcontroller.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")

    return provider_service.set_enabled(db, current_user.id, provider_id, payload.enabled)
