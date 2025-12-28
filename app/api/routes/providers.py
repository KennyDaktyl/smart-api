import logging
from fastapi import APIRouter, Depends, HTTPException
from smart_common.core.db import get_db
from smart_common.core.dependencies import get_current_user
from smart_common.models.user import User
from smart_common.providers.wizard.exceptions import WizardSessionExpiredError
from smart_common.repositories.provider import ProviderRepository
from smart_common.schemas.provider_schema import ProviderCreateRequest, ProviderResponse
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

    provider_repository = ProviderRepository(db)
    return provider_repository.list_for_user(user_id=current_user.id)


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
