import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi_cache.decorator import cache

from app.constans.role import UserRole
from app.core.db import SessionLocal
from app.core.dependencies import get_current_user
from app.models.user import User
from app.repositories.inverter_power_record_repository import InverterPowerRepository
from app.repositories.inverter_repository import InverterRepository

router = APIRouter(prefix="/inverter-power", tags=["Inverter Power"])
logger = logging.getLogger(__name__)

inverter_repo = InverterRepository()


def _build_latest_inverter_power(
    inverter_id: int, user_id: int, user_role: str
):
    db = SessionLocal()
    try:
        inverter = inverter_repo.get_for_user_by_id(db, inverter_id, user_id)
        logger.info(
            f"Fetching latest power data for inverter ID {inverter_id} by user ID {user_id}"
        )
        if not inverter and user_role == UserRole.ADMIN.value:
            inverter = inverter_repo.get_by_id(db, inverter_id)

        if not inverter:
            raise HTTPException(status_code=404, detail="Inverter not found")

        if (
            user_role != UserRole.ADMIN.value
            and inverter.installation.user_id != user_id
        ):
            raise HTTPException(status_code=403, detail="Access denied")

        repo = InverterPowerRepository(db)
        record = repo.get_latest_for_inverter(inverter_id)

        if not record:
            active_power = None
            timestamp = None
            message = "No power data available yet"
        else:
            active_power = float(record.active_power) if record.active_power is not None else None
            timestamp = record.timestamp
            message = "Latest inverter power data retrieved successfully"

        return {
            "inverter_id": inverter.id,
            "serial_number": inverter.serial_number,
            "active_power": active_power,
            "timestamp": timestamp,
            "message": message,
        }
    finally:
        db.close()


@cache(expire=60)
async def _get_latest_inverter_power_cached(
    inverter_id: int, user_id: int, user_role: str
):
    return await asyncio.to_thread(
        _build_latest_inverter_power, inverter_id, user_id, user_role
    )


@router.get("/{inverter_id}/power/latest")
async def get_latest_inverter_power(
    inverter_id: int,
    current_user: User = Depends(get_current_user),
):
    return await _get_latest_inverter_power_cached(
        inverter_id,
        current_user.id,
        current_user.role,
    )
