import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from smart_common.core.db import get_db
from smart_common.core.dependencies import get_current_user
from smart_common.models.user import User
from smart_common.providers.wizard.exceptions import WizardSessionExpiredError
from smart_common.repositories.provider import ProviderRepository
from smart_common.schemas.provider_schema import (
    ProviderCreateRequest,
    ProviderEnabledUpdateRequest,
    ProviderResponse,
    ProviderUpdateRequest,
)
from smart_common.services.provider_service import ProviderService

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

provider_router = APIRouter(
    prefix="/providers",
    tags=["Providers"],
)


@provider_router.get(
    "/list",
    response_model=list[ProviderResponse],
    status_code=200,
    summary="List providers",
    description="Lists all providers configured for the selected microcontroller.",
)
def list_user_providers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ProviderResponse]:
    if current_user.id is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    provider_repository = ProviderRepository(db)
    providers = provider_repository.list_for_user(user_id=current_user.id)

    # Defensive ownership check: never leak providers from other users.
    safe_providers = []
    for provider in providers:
        owned_provider = provider_repository.get_for_user(
            provider_id=provider.id,
            user_id=current_user.id,
        )
        if owned_provider:
            safe_providers.append(provider)

    if len(safe_providers) != len(providers):
        logger.warning(
            "Filtered cross-user providers from list endpoint",
            extra={
                "user_id": current_user.id,
                "returned": len(safe_providers),
                "original": len(providers),
            },
        )

    return safe_providers


@provider_router.post(
    "",
    response_model=ProviderResponse,
    status_code=201,
    summary="Create user provider",
    description="Creates a new provider attached to the specified microcontroller.",
)
def create_provider(
    payload: ProviderCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProviderResponse:

    logger.info("Creating user provider", extra={"payload": payload})

    provider_service = ProviderService(
        provider_repo_factory=lambda session: ProviderRepository(session),
        microcontroller_repo_factory=None,
    )

    payload_dict = payload.model_dump(exclude={"wizard_session_id", "config"})

    if payload.wizard_session_id:
        try:
            provider = provider_service.create_provider_from_wizard(
                db=db,
                user_id=current_user.id,
                wizard_session_id=payload.wizard_session_id,
                payload=payload_dict,
            )
        except WizardSessionExpiredError as exc:
            raise HTTPException(status_code=410, detail=str(exc))
    else:
        provider = provider_service.create_for_user(
            db=db,
            user_id=current_user.id,
            payload=payload_dict,
        )

    return provider


@provider_router.patch(
    "/{provider_uuid}",
    response_model=ProviderResponse,
    status_code=200,
    summary="Update provider",
)
def update_provider(
    provider_uuid: UUID,
    payload: ProviderUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProviderResponse:
    provider_service = ProviderService(
        provider_repo_factory=lambda session: ProviderRepository(session),
        microcontroller_repo_factory=None,
    )

    return provider_service.update_by_uuid(
        db=db,
        user_id=current_user.id,
        provider_uuid=provider_uuid,
        payload=payload.model_dump(exclude_none=True),
    )


@provider_router.patch(
    "/{provider_uuid}/enabled",
    response_model=ProviderResponse,
    status_code=200,
)
def set_provider_enabled(
    provider_uuid: UUID,
    payload: ProviderEnabledUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = ProviderRepository(db)

    provider = repo.get_for_user_by_uuid(
        provider_uuid=provider_uuid,
        user_id=current_user.id,
    )

    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    provider = repo.partial_update(
        provider,
        data={"enabled": payload.enabled},
        allowed_fields={"enabled"},
    )

    return provider
