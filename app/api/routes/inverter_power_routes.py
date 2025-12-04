import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi_cache.decorator import cache
from sqlalchemy.orm import Session

from app.constans.role import UserRole
from app.core.db import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.repositories.inverter_power_record_repository import InverterPowerRepository
from app.repositories.inverter_repository import InverterRepository

router = APIRouter(prefix="/inverter-power", tags=["Inverter Power"])
logger = logging.getLogger(__name__)

inverter_repo = InverterRepository()


@router.get("/{inverter_id}/power/latest")
@cache(expire=60)
def get_latest_inverter_power(
    inverter_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inverter = inverter_repo.get_for_user_by_id(db, inverter_id, current_user.id)
    logger.info(
        f"Fetching latest power data for inverter ID {inverter_id} by user ID {current_user.id}"
    )
    if not inverter and current_user.role == UserRole.ADMIN.value:
        inverter = inverter_repo.get_by_id(db, inverter_id)

    if not inverter:
        raise HTTPException(status_code=404, detail="Inverter not found")

    if (
        current_user.role != UserRole.ADMIN.value
        and inverter.installation.user_id != current_user.id
    ):
        raise HTTPException(status_code=403, detail="Access denied")

    repo = InverterPowerRepository(db)
    record = repo.get_latest_for_inverter(inverter_id)

    if not record:
        active_power = None
        timestamp = None
        message = "No power data available yet"
    else:
        active_power = float(record.active_power)
        timestamp = record.timestamp
        message = "Latest inverter power data retrieved successfully"

    return {
        "inverter_id": inverter.id,
        "serial_number": inverter.serial_number,
        "active_power": active_power,
        "timestamp": timestamp,
        "message": message,
    }
