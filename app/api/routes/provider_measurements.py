from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from smart_common.core.db import get_db
from smart_common.core.dependencies import get_current_user
from smart_common.models.user import User
from smart_common.repositories.provider import ProviderRepository
from smart_common.repositories.measurement_repository import MeasurementRepository
from smart_common.schemas.provider_measurement_schemas import (
    DayEnergyOut,
    HourlyEnergyPoint,
    ProviderEnergySeriesOut,
)

logger = logging.getLogger(__name__)

provider_measurements_router = APIRouter(
    prefix="/provider-measurements",
    tags=["Provider Telemetry"],
)


@provider_measurements_router.get(
    "/provider/{provider_uuid}/energy",
    response_model=ProviderEnergySeriesOut,
    summary="Provider hourly energy (Wh) grouped by day",
)
def list_provider_energy(
    provider_uuid: UUID,
    date_start: datetime | None = Query(None),
    date_end: datetime | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProviderEnergySeriesOut:

    provider = ProviderRepository(db).get_for_user_by_uuid(
        provider_uuid=provider_uuid,
        user_id=current_user.id,
    )
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    now = datetime.now(timezone.utc)

    start = (
        date_start.astimezone(timezone.utc)
        if date_start
        else now.replace(hour=0, minute=0, second=0, microsecond=0)
    )
    end = date_end.astimezone(timezone.utc) if date_end else now

    if start > end:
        raise HTTPException(status_code=400, detail="date_start must be <= date_end")

    # ===============================
    # FETCH HOURLY ENERGY (REPO)
    # ===============================
    rows = MeasurementRepository(db).list_hourly_energy(
        provider_id=provider.id,
        date_start=start,
        date_end=end,
    )

    days: dict[str, DayEnergyOut] = {}

    for hour_dt, avg_power_w in rows:
        if avg_power_w is None:
            continue

        hour_dt = hour_dt.astimezone(timezone.utc)
        day_key = hour_dt.date().isoformat()

        energy_wh = float(avg_power_w)

        day = days.setdefault(
            day_key,
            DayEnergyOut(
                date=day_key,
                total_energy_wh=0.0,
                import_wh=0.0,
                export_wh=0.0,
                hours=[],
            ),
        )

        day.hours.append(
            HourlyEnergyPoint(
                hour=hour_dt,
                energy_wh=energy_wh,
            )
        )

        day.total_energy_wh += energy_wh

        if energy_wh < 0:
            day.import_wh += abs(energy_wh)
        else:
            day.export_wh += energy_wh

    # ===============================
    # ENSURE EMPTY DAYS EXIST
    # ===============================
    cursor = start.date()
    end_day = end.date()

    while cursor <= end_day:
        key = cursor.isoformat()
        days.setdefault(
            key,
            DayEnergyOut(
                date=key,
                total_energy_wh=0.0,
                import_wh=0.0,
                export_wh=0.0,
                hours=[],
            ),
        )
        cursor += timedelta(days=1)

    return ProviderEnergySeriesOut(days=days)
