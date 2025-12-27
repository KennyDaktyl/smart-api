from fastapi import APIRouter
from smart_common.core.db import get_db
from smart_common.core.dependencies import get_current_user
from smart_common.models.user import User
from smart_common.repositories.provider import ProviderRepository
from smart_common.schemas.provider_schema import ProviderCreateRequest, ProviderResponse

from sqlalchemy.orm import Session
from fastapi import Depends

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

    provider_repository = ProviderRepository()
    provider = provider_repository.create(
        db=db,
        obj_in=payload,
        user_id=current_user.id,
    )
    return provider
