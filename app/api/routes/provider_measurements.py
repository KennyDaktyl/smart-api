from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from smart_common.core.db import get_db
from smart_common.core.dependencies import get_current_user
from smart_common.enums.unit import PowerUnit
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
    summary="Provider hourly energy portfolio grouped by day",
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

    rows = MeasurementRepository(db).list_hourly_energy(
        provider_id=provider.id,
        date_start=start,
        date_end=end,
    )

    days: dict[str, DayEnergyOut] = {}

    for hour_dt, energy in rows:
        if energy is None:
            continue

        hour_dt = hour_dt.astimezone(timezone.utc)
        day_key = hour_dt.date().isoformat()
        energy = float(energy)

        day = days.setdefault(
            day_key,
            DayEnergyOut(
                date=day_key,
                total_energy=0.0,
                import_energy=0.0,
                export_energy=0.0,
                hours=[],
            ),
        )

        day.hours.append(
            HourlyEnergyPoint(
                hour=hour_dt,
                energy=energy,
            )
        )

        day.total_energy += energy

        if energy < 0:
            day.import_energy += abs(energy)
        else:
            day.export_energy += energy

    cursor = start.date()
    end_day = end.date()

    while cursor <= end_day:
        key = cursor.isoformat()
        days.setdefault(
            key,
            DayEnergyOut(
                date=key,
                total_energy=0.0,
                import_energy=0.0,
                export_energy=0.0,
                hours=[],
            ),
        )
        cursor += timedelta(days=1)

    return ProviderEnergySeriesOut(
        unit=_energy_unit_from_power(provider.unit),
        days=days,
    )


def _energy_unit_from_power(unit: PowerUnit | None) -> str | None:
    if unit == PowerUnit.KILOWATT:
        return "kWh"
    if unit == PowerUnit.WATT:
        return "Wh"
    return None
