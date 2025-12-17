from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from smart_common.core.db import get_db
from smart_common.models.user import User
from smart_common.repositories.installation import InstallationRepository

from app.api.schemas.installations import InstallationCreateRequest, InstallationResponse
from app.core.dependencies import get_current_user
from app.services.installation_service import InstallationService

router = APIRouter(prefix="/installations", tags=["Installations"])

installation_service = InstallationService(lambda db: InstallationRepository(db))


@router.get(
    "/",
    response_model=list[InstallationResponse],
    status_code=200,
    summary="List user installations",
    description="Returns all installations owned by the authenticated user.",
)
def list_installations(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[InstallationResponse]:
    return installation_service.list_for_user(db, current_user.id)


@router.post(
    "/",
    response_model=InstallationResponse,
    status_code=201,
    summary="Create installation",
    description="Registers a new installation under the authenticated user.",
)
def create_installation(
    payload: InstallationCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InstallationResponse:
    return installation_service.create_for_user(db, current_user.id, payload.model_dump())


@router.get(
    "/{installation_id}",
    response_model=InstallationResponse,
    status_code=200,
    summary="Get installation details",
    description="Returns details for a specific installation if it belongs to the user.",
)
def get_installation(
    installation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InstallationResponse:
    return installation_service.get_for_user(db, installation_id, current_user.id)
