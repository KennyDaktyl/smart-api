import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.constans.role import UserRole
from app.core.db import get_db
from app.core.dependencies import get_current_user
from app.core.roles import require_role
from app.models.inverter import Inverter
from app.repositories.installation_repository import InstallationRepository
from app.repositories.inverter_repository import InverterRepository
from app.schemas.inverter_schema import InverterCreate, InverterOut, InverterUpdate

router = APIRouter(prefix="/inverters", tags=["Inverters"])
logger = logging.getLogger(__name__)

inverter_repo = InverterRepository()
installation_repo = InstallationRepository()


@router.get(
    "/", response_model=list[InverterOut], dependencies=[Depends(require_role(UserRole.ADMIN))]
)
def list_inverters(
    db: Session = Depends(get_db),
):
    return inverter_repo.get_all(db)


@router.get("/{inverter_id}", response_model=InverterOut)
def get_inverter_detail(
    inverter_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inverter = inverter_repo.get_for_user_by_id(db, inverter_id, current_user.id)

    if not inverter and current_user.role == UserRole.ADMIN:
        inverter = inverter_repo.get_by_id(db, inverter_id)

    if not inverter:
        raise HTTPException(status_code=404, detail="Inverter not found")

    if current_user.role != UserRole.ADMIN and inverter.installation.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return inverter


@router.post("/", response_model=InverterOut)
def create_inverter(
    payload: InverterCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    installation = installation_repo.get_for_user_by_id(
        db, payload.installation_id, current_user.id
    )
    if not installation:
        raise HTTPException(status_code=404, detail="Installation not found")

    existing = inverter_repo.get_by_serial(db, payload.serial_number)
    if existing:
        raise HTTPException(
            status_code=400, detail="Inverter with this serial number already exists"
        )

    payload: Inverter = payload.model_dump()
    inverter = inverter_repo.create(
        db,
        payload,
    )
    return inverter


@router.put("/{inverter_id}", response_model=InverterOut)
def update_inverter(
    inverter_id: int,
    payload: InverterUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    update_data = payload.model_dump(exclude_unset=True)
    update_data["last_updated"] = datetime.now(timezone.utc)

    inverter = inverter_repo.update_for_user(db, inverter_id, current_user.id, update_data)
    if not inverter:
        raise HTTPException(status_code=404, detail="Inverter not found")

    return inverter


@router.delete("/{inverter_id}")
def delete_inverter(
    inverter_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deleted = inverter_repo.delete_for_user(db, inverter_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Inverter not found")

    return {"message": "Inverter deleted successfully"}
