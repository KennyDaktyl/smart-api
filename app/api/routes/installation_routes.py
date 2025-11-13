import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.constans.role import UserRole
from app.core.db import get_db
from app.core.dependencies import get_current_user
from app.core.roles import require_role
from app.repositories.installation_repository import InstallationRepository
from app.schemas.installation_schema import InstallationCreate, InstallationOut, InstallationUpdate
from app.models.user import User

router = APIRouter(prefix="/installations", tags=["Installations"])
logger = logging.getLogger(__name__)

installation_repo = InstallationRepository()


@router.get(
    "/", response_model=list[InstallationOut], dependencies=[Depends(require_role(UserRole.ADMIN))]
)
def list_installations(
    db: Session = Depends(get_db),
):
    return installation_repo.get_all(db)


@router.get("/{installation_id}", response_model=InstallationOut)
def get_installation_detail(
    installation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    installation = installation_repo.get_by_id(db, installation_id)

    if not installation:
        raise HTTPException(status_code=404, detail="Installation not found")

    if current_user.role != UserRole.ADMIN and installation.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return installation


@router.post("/", response_model=InstallationOut)
def create_installation(
    payload: InstallationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = installation_repo.get_by_station_code(db, payload.station_code)
    if existing:
        raise HTTPException(status_code=400, detail="Installation already exists")

    new_installation = installation_repo.create(
        db,
        {
            "name": payload.name,
            "station_code": payload.station_code,
            "station_addr": payload.station_addr,
            "user_id": current_user.id,
        },
    )
    return new_installation


@router.put("/{installation_id}", response_model=InstallationOut)
def update_installation(
    installation_id: int,
    payload: InstallationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    update_data = payload.model_dump(exclude_unset=True)
    installation = installation_repo.update_for_user(
        db, installation_id, current_user.id, update_data
    )

    if not installation:
        raise HTTPException(status_code=404, detail="Installation not found")

    return installation


@router.delete("/{installation_id}")
def delete_installation(
    installation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deleted = installation_repo.delete_for_user(db, installation_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Installation not found")

    return {"message": "Installation deleted successfully"}
