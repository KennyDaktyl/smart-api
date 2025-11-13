import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.adapters.adapter_cache import get_adapter_for_user
from app.adapters.huawei_adapter import HuaweiAdapter
from app.core.db import get_db
from app.core.dependencies import get_current_user
from app.core.security import decrypt_password
from app.repositories.user_repository import UserRepository

router = APIRouter(prefix="/huawei", tags=["Huawei API"])
logger = logging.getLogger(__name__)


@router.get("/stations")
def get_huawei_stations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        adapter = get_adapter_for_user(db, current_user)
        stations = adapter.get_stations()

        if not stations:
            return {"message": "No stations found", "count": 0, "stations": []}

        return {
            "message": "Station list retrieved successfully",
            "count": len(stations),
            "stations": stations,
        }
    except Exception as e:
        logger.exception("Failed to fetch Huawei stations")
        raise HTTPException(status_code=400, detail=f"Failed to fetch stations: {str(e)}")


@router.get("/devices")
def get_huawei_devices_for_station(
    station_code: str = Query(..., description="Huawei station code (e.g., NE=165855378)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        adapter = get_adapter_for_user(db, current_user)
        devices = adapter.get_devices_for_station(station_code)

        if not devices:
            return {
                "message": f"No devices found for station {station_code}",
                "count": 0,
                "devices": [],
            }

        return {
            "message": f"Device list retrieved successfully for station {station_code}",
            "count": len(devices),
            "devices": devices,
        }

    except Exception as e:
        logger.exception("Failed to fetch Huawei devices for station")
        raise HTTPException(status_code=400, detail=f"Failed to fetch devices: {str(e)}")


@router.get("/device/production")
def get_huawei_device_production(
    device_id: str = Query(..., description="Huawei device ID (e.g. 1000000165855382)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        adapter = get_adapter_for_user(db, current_user)
        production = adapter.get_production(device_id)

        if not production:
            return {
                "message": f"No production data found for device {device_id}",
                "device_id": device_id,
                "data": {},
            }

        return {
            "message": f"Real-time production data retrieved successfully for device {device_id}",
            "device_id": device_id,
            "data": production,
        }

    except Exception as e:
        logger.exception("Failed to fetch Huawei device production data")
        raise HTTPException(status_code=500, detail=f"Failed to fetch production data: {str(e)}")
