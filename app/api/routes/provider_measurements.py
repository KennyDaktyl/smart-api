from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException
from smart_common.services.energy_calculation_service import EnergyCalculationService, PowerSample
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

    start = date_start.astimezone(timezone.utc) if date_start else now.replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    end = date_end.astimezone(timezone.utc) if date_end else now

    if start > end:
        raise HTTPException(status_code=400, detail="date_start must be <= date_end")

    repo = MeasurementRepository(db)

    raw_samples = repo.list_power_samples(
        provider_id=provider.id,
        date_start=start,
        date_end=end,
    )

    samples = [
        PowerSample(ts=ts.astimezone(timezone.utc), value=float(p))
        for ts, p in raw_samples
    ]

    hourly_energy = EnergyCalculationService.integrate_hourly(samples)

    days: dict[str, DayEnergyOut] = {}

    for hour_dt, energy in hourly_energy.items():
        day_key = hour_dt.date().isoformat()

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
                energy=round(energy, 5),
            )
        )

        day.total_energy += energy
        day.export_energy += max(0.0, energy)
        day.import_energy += max(0.0, -energy)

    cursor = start.date()
    while cursor <= end.date():
        days.setdefault(
            cursor.isoformat(),
            DayEnergyOut(
                date=cursor.isoformat(),
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
