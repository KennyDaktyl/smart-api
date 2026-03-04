from __future__ import annotations

import logging
from datetime import date as date_type
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from smart_common.core.db import get_db
from smart_common.core.dependencies import get_current_user
from smart_common.enums.unit import PowerUnit
from smart_common.models.device import Device
from smart_common.models.microcontroller import Microcontroller
from smart_common.models.user import User
from smart_common.providers.enums import ProviderKind, ProviderType
from smart_common.repositories.device_event import DeviceEventRepository
from smart_common.repositories.provider import ProviderRepository
from smart_common.repositories.measurement_repository import MeasurementRepository
from smart_common.schemas.provider_measurement_schemas import (
    DayPowerOut,
    DayEnergyOut,
    HourlyEnergyPoint,
    PowerEntryPoint,
    ProviderMeasurementResponse,
    ProviderCurrentHourPoolOut,
    ProviderEnergySeriesOut,
    ProviderPowerSeriesOut,
)
from smart_common.services.energy_calculation_service import (
    EnergyCalculationService,
    PowerSample,
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
    selected_date: date_type | None = Query(None, alias="date"),
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

    start, end = _resolve_day_window(selected_date=selected_date, now=now)

    repo = MeasurementRepository(db)

    raw_samples = repo.list_power_samples(
        provider_id=provider.id,
        date_start=start,
        date_end=end,
    )

    samples = [
        PowerSample(ts=_to_utc_aware(ts), value=float(p))
        for ts, p in raw_samples
    ]

    raw_measurements = repo.list_measurements(
        provider_id=provider.id,
        date_start=start,
        date_end=end,
    )
    hourly_energy = EnergyCalculationService.integrate_hourly(samples)

    day_key = start.date().isoformat()
    days: dict[str, DayEnergyOut] = {day_key: _empty_day(day_key)}

    for measurement in raw_measurements:
        measured_at = _to_utc_aware(measurement.measured_at)
        measurement_day_key = measured_at.date().isoformat()
        day = days.setdefault(measurement_day_key, _empty_day(measurement_day_key))
        day.entries.append(
            ProviderMeasurementResponse(
                id=measurement.id,
                measured_at=measured_at,
                measured_value=(
                    float(measurement.measured_value)
                    if measurement.measured_value is not None
                    else None
                ),
                measured_unit=measurement.measured_unit,
                metadata_payload=dict(measurement.metadata_payload or {}),
            )
        )

    for hour_dt, energy in hourly_energy.items():
        hour_day_key = hour_dt.date().isoformat()

        day = days.setdefault(
            hour_day_key,
            _empty_day(hour_day_key),
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

    for day in days.values():
        day.hours.sort(key=lambda point: point.hour)
        day.entries.sort(key=lambda point: point.measured_at)
        day.total_energy = round(day.total_energy, 5)
        day.import_energy = round(day.import_energy, 5)
        day.export_energy = round(day.export_energy, 5)

    return ProviderEnergySeriesOut(
        unit=_energy_unit_from_power(provider.unit),
        days=days,
    )


@provider_measurements_router.get(
    "/provider/{provider_uuid}/power",
    response_model=ProviderPowerSeriesOut,
)
def list_provider_power(
    provider_uuid: UUID,
    selected_date: date_type | None = Query(None, alias="date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProviderPowerSeriesOut:
    provider = ProviderRepository(db).get_for_user_by_uuid(
        provider_uuid=provider_uuid,
        user_id=current_user.id,
    )
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    if provider.kind != ProviderKind.POWER:
        raise HTTPException(
            status_code=422,
            detail="Raw power is available only for POWER providers",
        )

    now = datetime.now(timezone.utc)
    start, end = _resolve_day_window(selected_date=selected_date, now=now)

    raw_samples = MeasurementRepository(db).list_power_samples(
        provider_id=provider.id,
        date_start=start,
        date_end=end,
    )

    day_key = start.date().isoformat()
    days: dict[str, DayPowerOut] = {day_key: _empty_power_day(day_key)}

    for ts, value in raw_samples:
        ts_utc = _to_utc_aware(ts)
        point_day_key = ts_utc.date().isoformat()
        day = days.setdefault(point_day_key, _empty_power_day(point_day_key))
        day.entries.append(
            PowerEntryPoint(
                timestamp=ts_utc,
                power=round(float(value), 5),
            )
        )

    for day in days.values():
        day.entries.sort(key=lambda point: point.timestamp)

    return ProviderPowerSeriesOut(
        unit=provider.unit.value if provider.unit else None,
        days=days,
    )


@provider_measurements_router.get(
    "/provider/{provider_uuid}/energy/current-hour-pool",
    response_model=ProviderCurrentHourPoolOut,
)
def get_provider_current_hour_pool(
    provider_uuid: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProviderCurrentHourPoolOut:
    provider = ProviderRepository(db).get_for_user_by_uuid(
        provider_uuid=provider_uuid,
        user_id=current_user.id,
    )
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    if provider.kind != ProviderKind.POWER:
        raise HTTPException(
            status_code=422,
            detail="Current-hour pool is available only for POWER providers",
        )

    energy_unit = _energy_unit_from_power(provider.unit)
    if energy_unit is None:
        raise HTTPException(
            status_code=422,
            detail="Provider unit must be W or kW",
        )

    now = datetime.now(timezone.utc)
    start, end = _resolve_hour_window(now=now)

    measurement_repo = MeasurementRepository(db)
    previous_sample = measurement_repo.get_last_power_sample_before(
        provider_id=provider.id,
        before=start,
    )
    raw_samples = measurement_repo.list_power_samples(
        provider_id=provider.id,
        date_start=start,
        date_end=end,
    )

    hour_samples = _build_window_samples(
        raw_samples=raw_samples,
        previous_sample=previous_sample,
        start=start,
        end=end,
    )

    production_energy = _integrate_window_energy(hour_samples)
    current_power = hour_samples[-1].value if hour_samples else None

    provider_includes_device_consumption = provider.provider_type != ProviderType.API
    device_consumption_energy = 0.0
    devices_considered = 0

    if not provider_includes_device_consumption:
        devices = _list_devices_for_power_provider(
            db=db,
            user_id=current_user.id,
            provider_id=provider.id,
        )
        event_repo = DeviceEventRepository(db)
        device_consumption_kwh = 0.0

        for device in devices:
            if device.rated_power is None:
                continue

            rated_power_kw = float(device.rated_power)
            if rated_power_kw <= 0:
                continue

            devices_considered += 1
            on_seconds = _calculate_device_on_seconds(
                device=device,
                event_repo=event_repo,
                start=start,
                end=end,
            )
            if on_seconds <= 0:
                continue

            device_consumption_kwh += rated_power_kw * (on_seconds / 3600.0)

        device_consumption_energy = _convert_kwh_to_energy_unit(
            value_kwh=device_consumption_kwh,
            energy_unit=energy_unit,
        )

    net_energy = production_energy - device_consumption_energy
    available_energy = max(0.0, net_energy)

    return ProviderCurrentHourPoolOut(
        provider_uuid=provider.uuid,
        hour_start=start,
        as_of=end,
        unit=energy_unit,
        current_power=round(current_power, 5) if current_power is not None else None,
        current_power_unit=provider.unit.value if provider.unit else None,
        production_energy=round(production_energy, 5),
        device_consumption_energy=round(device_consumption_energy, 5),
        net_energy=round(net_energy, 5),
        available_energy=round(available_energy, 5),
        provider_includes_device_consumption=provider_includes_device_consumption,
        devices_considered=devices_considered,
    )


def _resolve_day_window(
    *,
    selected_date: date_type | None,
    now: datetime,
) -> tuple[datetime, datetime]:
    day = selected_date or now.date()
    start = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc)

    if day == now.date():
        return start, now

    end = start + timedelta(days=1) - timedelta(microseconds=1)
    return start, end


def _to_utc_aware(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


def _resolve_hour_window(*, now: datetime) -> tuple[datetime, datetime]:
    start = now.replace(minute=0, second=0, microsecond=0)
    return start, now


def _build_window_samples(
    *,
    raw_samples: list[tuple[datetime, float]],
    previous_sample: tuple[datetime, float] | None,
    start: datetime,
    end: datetime,
) -> list[PowerSample]:
    points: list[PowerSample] = []

    if previous_sample:
        _, previous_value = previous_sample
        points.append(PowerSample(ts=start, value=float(previous_value)))

    for ts, value in raw_samples:
        ts_utc = _to_utc_aware(ts)
        if ts_utc < start or ts_utc > end:
            continue
        points.append(PowerSample(ts=ts_utc, value=float(value)))

    if not points:
        return []

    points.sort(key=lambda sample: sample.ts)

    deduped: list[PowerSample] = []
    for sample in points:
        if deduped and deduped[-1].ts == sample.ts:
            deduped[-1] = sample
        else:
            deduped.append(sample)

    if deduped[-1].ts < end:
        deduped.append(PowerSample(ts=end, value=deduped[-1].value))

    return deduped


def _integrate_window_energy(samples: list[PowerSample]) -> float:
    intervals = EnergyCalculationService.integrate_intervals(samples)
    return float(sum(interval.energy for interval in intervals))


def _list_devices_for_power_provider(
    *,
    db: Session,
    user_id: int,
    provider_id: int,
) -> list[Device]:
    return (
        db.query(Device)
        .join(Device.microcontroller)
        .filter(
            Microcontroller.user_id == user_id,
            Microcontroller.power_provider_id == provider_id,
            Microcontroller.enabled.is_(True),
        )
        .all()
    )


def _calculate_device_on_seconds(
    *,
    device: Device,
    event_repo: DeviceEventRepository,
    start: datetime,
    end: datetime,
) -> float:
    if end <= start:
        return 0.0

    previous_state_event = event_repo.get_last_state_for_device_before(
        device_id=device.id,
        before=start,
    )
    hour_state_events = event_repo.list_state_for_device(
        device_id=device.id,
        date_start=start,
        date_end=end,
    )

    current_state = _resolve_state_from_event(previous_state_event)
    if current_state is None:
        current_state = _resolve_state_from_device_snapshot(device=device, start=start)

    if current_state is None and hour_state_events:
        first_event_state = _resolve_state_from_event(hour_state_events[0])
        if first_event_state is not None:
            # STATE events are transitions, so before the first event
            # we assume the opposite state.
            current_state = not first_event_state

    if current_state is None and not hour_state_events:
        return _fallback_on_seconds_from_device_snapshot(
            device=device,
            start=start,
            end=end,
        )

    on_seconds = 0.0
    cursor = start

    for event in hour_state_events:
        event_ts = _clamp_to_window(_to_utc_aware(event.created_at), start, end)
        if event_ts < cursor:
            continue

        if current_state is True:
            on_seconds += (event_ts - cursor).total_seconds()

        cursor = event_ts
        next_state = _resolve_state_from_event(event)
        if next_state is not None:
            current_state = next_state

    if current_state is True and cursor < end:
        on_seconds += (end - cursor).total_seconds()

    return max(0.0, on_seconds)


def _resolve_state_from_event(event) -> bool | None:
    if event is None:
        return None

    pin_state = getattr(event, "pin_state", None)
    if isinstance(pin_state, bool):
        return pin_state

    device_state = getattr(event, "device_state", None)
    if isinstance(device_state, str):
        normalized = device_state.strip().upper()
        if normalized in {"ON", "TRUE", "1"}:
            return True
        if normalized in {"OFF", "FALSE", "0"}:
            return False

    return None


def _resolve_state_from_device_snapshot(
    *,
    device: Device,
    start: datetime,
) -> bool | None:
    if not isinstance(device.manual_state, bool):
        return None

    if device.last_state_change_at is None:
        return device.manual_state

    last_change = _to_utc_aware(device.last_state_change_at)
    if last_change <= start:
        return device.manual_state

    return None


def _fallback_on_seconds_from_device_snapshot(
    *,
    device: Device,
    start: datetime,
    end: datetime,
) -> float:
    if not isinstance(device.manual_state, bool):
        return 0.0

    last_change = device.last_state_change_at
    if last_change is None:
        return (end - start).total_seconds() if device.manual_state else 0.0

    last_change_utc = _to_utc_aware(last_change)
    if last_change_utc <= start:
        return (end - start).total_seconds() if device.manual_state else 0.0

    if last_change_utc >= end:
        return 0.0

    if device.manual_state:
        # State switched to ON in this hour.
        return (end - last_change_utc).total_seconds()

    # State switched to OFF in this hour.
    return (last_change_utc - start).total_seconds()


def _clamp_to_window(ts: datetime, start: datetime, end: datetime) -> datetime:
    if ts < start:
        return start
    if ts > end:
        return end
    return ts


def _convert_kwh_to_energy_unit(*, value_kwh: float, energy_unit: str) -> float:
    if energy_unit == "Wh":
        return value_kwh * 1000.0
    return value_kwh


def _empty_day(day_key: str) -> DayEnergyOut:
    return DayEnergyOut(
        date=day_key,
        total_energy=0.0,
        import_energy=0.0,
        export_energy=0.0,
        hours=[],
        entries=[],
    )


def _empty_power_day(day_key: str) -> DayPowerOut:
    return DayPowerOut(
        date=day_key,
        entries=[],
    )


def _energy_unit_from_power(unit: PowerUnit | None) -> str | None:
    if unit == PowerUnit.KILOWATT:
        return "kWh"
    if unit == PowerUnit.WATT:
        return "Wh"
    return None
