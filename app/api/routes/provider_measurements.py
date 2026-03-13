from __future__ import annotations

from collections import defaultdict
import logging
from datetime import date as date_type
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from smart_common.core.db import get_db
from smart_common.core.dependencies import get_current_user
from smart_common.enums.provider_telemetry import (
    ProviderTelemetryCapability,
    TelemetryAggregationMode,
    TelemetryChartType,
)
from smart_common.enums.unit import PowerUnit
from smart_common.models.device import Device
from smart_common.models.microcontroller import Microcontroller
from smart_common.models.user import User
from smart_common.providers.enums import ProviderKind, ProviderType
from smart_common.repositories.device_event import DeviceEventRepository
from smart_common.repositories.market_energy_price import MarketEnergyPriceRepository
from smart_common.repositories.provider import ProviderRepository
from smart_common.repositories.measurement_repository import MeasurementRepository
from smart_common.schemas.provider_measurement_schemas import (
    DayPowerOut,
    DayEnergyOut,
    HourlyEnergyPoint,
    HourlyRevenuePoint,
    MarketEnergyPricePointOut,
    PowerEntryPoint,
    ProviderMatchedRevenueOut,
    ProviderMarketPriceOut,
    ProviderTelemetryMetricDefinition,
    ProviderMetricHourlyPoint,
    ProviderMetricPoint,
    ProviderMetricSeriesOut,
    ProviderMeasurementResponse,
    ProviderCurrentHourPoolOut,
    ProviderEnergySeriesOut,
    ProviderPowerSeriesOut,
)
from smart_common.schemas.provider_schema import ProviderTelemetryResponse
from smart_common.services.energy_calculation_service import (
    EnergyCalculationService,
    PowerSample,
)

logger = logging.getLogger(__name__)

provider_measurements_router = APIRouter(
    prefix="/provider-measurements",
    tags=["Provider Telemetry"],
)

BATTERY_SOC_METRIC_KEY = "battery_soc"
GRID_POWER_METRIC_KEY = "grid_power"


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
    provider = _get_provider_or_404(
        db=db,
        provider_uuid=provider_uuid,
        user_id=current_user.id,
    )

    now = datetime.now(timezone.utc)
    start, end = _resolve_day_window(selected_date=selected_date, now=now)
    repo = MeasurementRepository(db)
    max_interval_seconds = _resolve_sample_hold_seconds(
        provider.default_expected_interval_sec
    )
    return _build_provider_energy_series(
        provider=provider,
        repo=repo,
        start=start,
        end=end,
        max_interval_seconds=max_interval_seconds,
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
    provider = _get_provider_or_404(
        db=db,
        provider_uuid=provider_uuid,
        user_id=current_user.id,
    )

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
    "/provider/{provider_uuid}/telemetry",
    response_model=ProviderTelemetryResponse,
)
def get_provider_telemetry(
    provider_uuid: UUID,
    selected_date: date_type | None = Query(None, alias="date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProviderTelemetryResponse:
    provider = _get_provider_or_404(
        db=db,
        provider_uuid=provider_uuid,
        user_id=current_user.id,
    )

    now = datetime.now(timezone.utc)
    start, end = _resolve_day_window(selected_date=selected_date, now=now)
    history_end = start + timedelta(days=1) - timedelta(microseconds=1)
    repo = MeasurementRepository(db)
    market_repo = MarketEnergyPriceRepository(db)
    max_interval_seconds = _resolve_sample_hold_seconds(
        provider.default_expected_interval_sec
    )
    energy_series = _build_provider_energy_series(
        provider=provider,
        repo=repo,
        start=start,
        end=end,
        max_interval_seconds=max_interval_seconds,
    )
    day_key = start.date().isoformat()
    day = energy_series.days[day_key]
    day_samples = _build_day_power_samples(
        repo=repo,
        provider_id=provider.id,
        start=start,
        end=end,
        carry_forward_seconds=max_interval_seconds,
    )
    revenue_market_entries = market_repo.list_between(
        market="RCE",
        date_start=start,
        date_end=end + timedelta(microseconds=1),
    )
    definitions = _list_metric_definitions_for_provider(
        provider=provider,
        repo=repo,
    )

    metrics = [
        _build_metric_series(
            repo=repo,
            provider_id=provider.id,
            definition=definition,
            start=start,
            end=end,
        )
        for definition in definitions
    ]

    reference_ts = end
    settlement_price = _build_market_price_context(
        repo=market_repo,
        market="RCE",
        label="RCE",
        start=start,
        end=history_end,
        reference_ts=reference_ts,
        energy_unit=energy_series.unit,
    )
    forecast_price = _build_market_price_context(
        repo=market_repo,
        market="RCE_FCST",
        label="Prognoza PSE",
        start=start,
        end=history_end,
        reference_ts=reference_ts,
        energy_unit=energy_series.unit,
    )

    return ProviderTelemetryResponse(
        provider=provider,
        date=day_key,
        measured_unit=_resolve_measured_unit_from_day(day),
        energy_unit=energy_series.unit,
        day=day,
        metrics=metrics,
        settlement_price=settlement_price,
        forecast_price=forecast_price,
        matched_revenue=_build_matched_revenue_summary(
            samples=day_samples,
            market_entries=revenue_market_entries,
            energy_unit=energy_series.unit,
            hourly_points=day.hours,
            max_interval_seconds=max_interval_seconds,
        ),
    )


@provider_measurements_router.get(
    "/provider/{provider_uuid}/metrics/{metric_key}",
    response_model=ProviderMetricSeriesOut,
)
def get_provider_metric_series(
    provider_uuid: UUID,
    metric_key: str,
    selected_date: date_type | None = Query(None, alias="date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProviderMetricSeriesOut:
    provider = _get_provider_or_404(
        db=db,
        provider_uuid=provider_uuid,
        user_id=current_user.id,
    )

    now = datetime.now(timezone.utc)
    start, end = _resolve_day_window(selected_date=selected_date, now=now)
    repo = MeasurementRepository(db)
    definition = _get_metric_definition_for_provider(
        provider=provider,
        repo=repo,
        metric_key=metric_key,
    )
    if definition is None:
        raise HTTPException(status_code=404, detail="Metric not found")
    return _build_metric_series(
        repo=repo,
        provider_id=provider.id,
        definition=definition,
        start=start,
        end=end,
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
    provider = _get_provider_or_404(
        db=db,
        provider_uuid=provider_uuid,
        user_id=current_user.id,
    )

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
    max_interval_seconds = _resolve_sample_hold_seconds(
        provider.default_expected_interval_sec
    )

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
        carry_forward_seconds=max_interval_seconds,
    )

    production_energy = _integrate_window_energy(
        hour_samples,
        max_interval_seconds=max_interval_seconds,
    )
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


def _get_provider_or_404(
    *,
    db: Session,
    provider_uuid: UUID,
    user_id: int,
):
    provider = ProviderRepository(db).get_for_user_by_uuid(
        provider_uuid=provider_uuid,
        user_id=user_id,
    )
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider


def _build_provider_energy_series(
    *,
    provider,
    repo: MeasurementRepository,
    start: datetime,
    end: datetime,
    max_interval_seconds: float | None = None,
) -> ProviderEnergySeriesOut:
    samples = _build_day_power_samples(
        repo=repo,
        provider_id=provider.id,
        start=start,
        end=end,
        carry_forward_seconds=max_interval_seconds,
    )
    raw_measurements = repo.list_measurements(
        provider_id=provider.id,
        date_start=start,
        date_end=end,
    )
    hourly_energy = EnergyCalculationService.integrate_hourly(
        samples,
        max_interval_seconds=max_interval_seconds,
    )

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
                extra_data=dict(measurement.extra_data or {}),
            )
        )

    for hour_dt, energy in hourly_energy.items():
        hour_day_key = hour_dt.date().isoformat()
        day = days.setdefault(hour_day_key, _empty_day(hour_day_key))
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


def _build_metric_series(
    *,
    repo: MeasurementRepository,
    provider_id: int,
    definition,
    start: datetime,
    end: datetime,
) -> ProviderMetricSeriesOut:
    raw_samples = repo.list_metric_samples(
        provider_id=provider_id,
        metric_key=definition.metric_key,
        date_start=start,
        date_end=end,
    )

    entries: list[ProviderMetricPoint] = []
    hours: list[ProviderMetricHourlyPoint] = []
    output_unit = definition.unit

    if definition.aggregation_mode == TelemetryAggregationMode.RAW:
        entries = [
            ProviderMetricPoint(
                timestamp=_to_utc_aware(sample.measured_at),
                value=round(float(sample.value), 5),
            )
            for sample in raw_samples
        ]
    elif definition.aggregation_mode == TelemetryAggregationMode.HOURLY_INTEGRAL:
        hourly_energy = EnergyCalculationService.integrate_hourly(
            [
                PowerSample(
                    ts=_to_utc_aware(sample.measured_at),
                    value=float(sample.value),
                )
                for sample in raw_samples
            ]
        )
        output_unit = _energy_unit_from_unit(definition.unit)
        hours = [
            ProviderMetricHourlyPoint(
                hour=hour_dt,
                value=round(energy, 5),
            )
            for hour_dt, energy in sorted(hourly_energy.items())
        ]

    return ProviderMetricSeriesOut(
        metric_key=definition.metric_key,
        label=definition.label,
        unit=output_unit,
        source_unit=definition.unit,
        chart_type=definition.chart_type,
        aggregation_mode=definition.aggregation_mode,
        capability_tag=definition.capability_tag,
        date=start.date().isoformat(),
        entries=entries,
        hours=hours,
    )


def _list_metric_definitions_for_provider(
    *,
    provider,
    repo: MeasurementRepository,
) -> list[ProviderTelemetryMetricDefinition]:
    definitions = {
        definition.metric_key: ProviderTelemetryMetricDefinition.model_validate(
            definition,
            from_attributes=True,
        )
        for definition in repo.list_metric_definitions(provider_id=provider.id)
    }

    if provider.has_energy_storage and BATTERY_SOC_METRIC_KEY not in definitions:
        definitions[BATTERY_SOC_METRIC_KEY] = _build_synthetic_metric_definition(
            BATTERY_SOC_METRIC_KEY
        )

    if provider.has_power_meter and GRID_POWER_METRIC_KEY not in definitions:
        definitions[GRID_POWER_METRIC_KEY] = _build_synthetic_metric_definition(
            GRID_POWER_METRIC_KEY
        )

    return [
        definitions[key]
        for key in sorted(definitions.keys())
    ]


def _get_metric_definition_for_provider(
    *,
    provider,
    repo: MeasurementRepository,
    metric_key: str,
) -> ProviderTelemetryMetricDefinition | None:
    definition = repo.get_metric_definition(
        provider_id=provider.id,
        metric_key=metric_key,
    )
    if definition is not None:
        return ProviderTelemetryMetricDefinition.model_validate(
            definition,
            from_attributes=True,
        )

    if provider.has_energy_storage and metric_key == BATTERY_SOC_METRIC_KEY:
        return _build_synthetic_metric_definition(metric_key)

    if provider.has_power_meter and metric_key == GRID_POWER_METRIC_KEY:
        return _build_synthetic_metric_definition(metric_key)

    return None


def _build_synthetic_metric_definition(
    metric_key: str,
) -> ProviderTelemetryMetricDefinition:
    if metric_key == BATTERY_SOC_METRIC_KEY:
        return ProviderTelemetryMetricDefinition(
            metric_key=BATTERY_SOC_METRIC_KEY,
            label="Battery SOC",
            unit=PowerUnit.PERCENT.value,
            chart_type=TelemetryChartType.LINE,
            aggregation_mode=TelemetryAggregationMode.RAW,
            capability_tag=ProviderTelemetryCapability.ENERGY_STORAGE,
        )

    if metric_key == GRID_POWER_METRIC_KEY:
        return ProviderTelemetryMetricDefinition(
            metric_key=GRID_POWER_METRIC_KEY,
            label="Grid power",
            unit=PowerUnit.WATT.value,
            chart_type=TelemetryChartType.BAR,
            aggregation_mode=TelemetryAggregationMode.HOURLY_INTEGRAL,
            capability_tag=ProviderTelemetryCapability.POWER_METER,
        )

    raise HTTPException(status_code=404, detail="Metric not found")


def _resolve_measured_unit_from_day(day: DayEnergyOut) -> str | None:
    for entry in day.entries:
        if entry.measured_unit:
            return entry.measured_unit
    return None


def _build_day_power_samples(
    *,
    repo: MeasurementRepository,
    provider_id: int,
    start: datetime,
    end: datetime,
    carry_forward_seconds: float | None = None,
) -> list[PowerSample]:
    previous_sample = repo.get_last_power_sample_before(
        provider_id=provider_id,
        before=start,
    )
    if previous_sample is not None:
        previous_ts, _ = previous_sample
        if _to_utc_aware(previous_ts).date() != start.date():
            previous_sample = None
    raw_samples = repo.list_power_samples(
        provider_id=provider_id,
        date_start=start,
        date_end=end,
    )
    return _build_window_samples(
        raw_samples=raw_samples,
        previous_sample=previous_sample,
        start=start,
        end=end,
        carry_forward_seconds=carry_forward_seconds,
    )


def _build_market_price_context(
    *,
    repo: MarketEnergyPriceRepository,
    market: str,
    label: str,
    start: datetime,
    end: datetime,
    reference_ts: datetime,
    energy_unit: str | None,
) -> ProviderMarketPriceOut | None:
    active_entry = repo.get_active_at(market=market, timestamp=reference_ts)
    if active_entry is None:
        active_entry = repo.get_latest_before(market=market, timestamp=reference_ts)
    if active_entry is None:
        return None

    history_entries = repo.list_between(
        market=market,
        date_start=start,
        date_end=end + timedelta(microseconds=1),
    )
    history = [
        MarketEnergyPricePointOut(
            interval_start=_to_utc_aware(entry.interval_start),
            interval_end=_to_utc_aware(entry.interval_end),
            price=round(float(entry.price_value), 6),
            currency=entry.currency,
            unit=entry.price_unit,
        )
        for entry in history_entries
    ]

    price = round(float(active_entry.price_value), 6)
    price_per_energy_unit = _convert_market_price_to_energy_unit(
        price=price,
        price_unit=active_entry.price_unit,
        energy_unit=energy_unit,
    )

    return ProviderMarketPriceOut(
        market=active_entry.market,
        label=label,
        price=price,
        currency=active_entry.currency,
        unit=active_entry.price_unit,
        interval_start=_to_utc_aware(active_entry.interval_start),
        interval_end=_to_utc_aware(active_entry.interval_end),
        source_updated_at=(
            _to_utc_aware(active_entry.source_updated_at)
            if active_entry.source_updated_at is not None
            else None
        ),
        price_per_energy_unit=price_per_energy_unit,
        energy_unit=energy_unit,
        history=history,
    )


def _build_matched_revenue_summary(
    *,
    samples: list[PowerSample],
    market_entries: list[object],
    energy_unit: str | None,
    hourly_points: list[HourlyEnergyPoint] | None = None,
    max_interval_seconds: float | None = None,
) -> ProviderMatchedRevenueOut | None:
    if not samples or len(samples) < 2 or not market_entries:
        return None

    total_export_energy = 0.0
    total_revenue = 0.0
    matched_intervals = 0
    hourly_revenue: dict[datetime, float] = defaultdict(float)
    hourly_export_energy: dict[datetime, float] = defaultdict(float)

    sorted_entries = sorted(
        market_entries,
        key=lambda entry: _to_utc_aware(entry.interval_start),
    )

    for interval_start, interval_end, power in _iter_effective_power_intervals(
        samples=samples,
        max_interval_seconds=max_interval_seconds,
    ):
        cursor = interval_start
        while cursor < interval_end:
            market_entry = _find_market_entry_for_timestamp(
                market_entries=sorted_entries,
                timestamp=cursor,
            )
            if market_entry is None:
                break

            market_end = _to_utc_aware(market_entry.interval_end)
            hour_end = cursor.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            segment_end = min(interval_end, market_end, hour_end)
            dt_hours = (segment_end - cursor).total_seconds() / 3600.0
            if dt_hours <= 0:
                break

            energy = power * dt_hours
            export_energy = max(0.0, energy)
            price_per_energy_unit = _convert_market_price_to_energy_unit(
                price=float(market_entry.price_value),
                price_unit=market_entry.price_unit,
                energy_unit=energy_unit,
            )

            if export_energy > 0 and price_per_energy_unit is not None:
                hour_bucket = cursor.replace(minute=0, second=0, microsecond=0)
                total_export_energy += export_energy
                total_revenue += export_energy * price_per_energy_unit
                matched_intervals += 1
                hourly_export_energy[hour_bucket] += export_energy
                hourly_revenue[hour_bucket] += export_energy * price_per_energy_unit

            cursor = segment_end

    if matched_intervals == 0:
        return None

    if hourly_points is not None:
        for point in hourly_points:
            hour_dt = _to_utc_aware(point.hour)
            point.revenue = round(hourly_revenue.get(hour_dt, 0.0), 6)

    first_entry = sorted_entries[0]
    return ProviderMatchedRevenueOut(
        market=str(first_entry.market),
        label="RCE dopasowane do interwału próbki",
        currency=str(first_entry.currency),
        energy_unit=energy_unit,
        total_export_energy=round(total_export_energy, 5),
        total_revenue=round(total_revenue, 6),
        matched_intervals=matched_intervals,
        hours=[
            HourlyRevenuePoint(
                hour=hour_dt,
                revenue=round(revenue, 6),
                export_energy=round(hourly_export_energy.get(hour_dt, 0.0), 5),
            )
            for hour_dt, revenue in sorted(hourly_revenue.items())
        ],
    )


def _find_market_entry_for_timestamp(
    *,
    market_entries: list[object],
    timestamp: datetime,
):
    for entry in market_entries:
        interval_start = _to_utc_aware(entry.interval_start)
        interval_end = _to_utc_aware(entry.interval_end)
        if interval_start <= timestamp < interval_end:
            return entry
    return None


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
    carry_forward_seconds: float | None = None,
) -> list[PowerSample]:
    points: list[PowerSample] = []

    if previous_sample:
        previous_ts, previous_value = previous_sample
        previous_ts_utc = _to_utc_aware(previous_ts)
        if _is_sample_fresh_for_boundary(
            sample_ts=previous_ts_utc,
            boundary_ts=start,
            carry_forward_seconds=carry_forward_seconds,
        ):
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
        carry_until = end
        if carry_forward_seconds is not None and carry_forward_seconds > 0:
            carry_until = min(
                end,
                deduped[-1].ts + timedelta(seconds=carry_forward_seconds),
            )
        if carry_until > deduped[-1].ts:
            deduped.append(PowerSample(ts=carry_until, value=deduped[-1].value))

    return deduped


def _integrate_window_energy(
    samples: list[PowerSample],
    *,
    max_interval_seconds: float | None = None,
) -> float:
    intervals = EnergyCalculationService.integrate_intervals(
        samples,
        max_interval_seconds=max_interval_seconds,
    )
    return float(sum(interval.energy for interval in intervals))


def _iter_effective_power_intervals(
    *,
    samples: list[PowerSample],
    max_interval_seconds: float | None = None,
):
    for left, right in zip(samples, samples[1:]):
        interval_end = right.ts
        if max_interval_seconds is not None and max_interval_seconds > 0:
            capped_end = left.ts + timedelta(seconds=max_interval_seconds)
            if capped_end < interval_end:
                interval_end = capped_end
        if interval_end <= left.ts:
            continue
        yield left.ts, interval_end, left.value


def _resolve_sample_hold_seconds(expected_interval_sec: int | None) -> float | None:
    if expected_interval_sec is None or expected_interval_sec <= 0:
        return None
    return float(min(max(expected_interval_sec * 5, 300), 900))


def _is_sample_fresh_for_boundary(
    *,
    sample_ts: datetime,
    boundary_ts: datetime,
    carry_forward_seconds: float | None,
) -> bool:
    if carry_forward_seconds is None or carry_forward_seconds <= 0:
        return True
    return (boundary_ts - sample_ts).total_seconds() <= carry_forward_seconds


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


def _convert_market_price_to_energy_unit(
    *,
    price: float,
    price_unit: str | None,
    energy_unit: str | None,
) -> float | None:
    if not price_unit or not energy_unit:
        return None

    normalized_price_unit = price_unit.strip().lower()
    normalized_energy_unit = energy_unit.strip().lower()

    if normalized_price_unit == "mwh":
        if normalized_energy_unit == "kwh":
            return round(price / 1000.0, 6)
        if normalized_energy_unit == "wh":
            return round(price / 1_000_000.0, 9)

    if normalized_price_unit == normalized_energy_unit:
        return round(price, 6)

    return None


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


def _energy_unit_from_unit(unit: str | None) -> str | None:
    if unit == PowerUnit.KILOWATT.value:
        return "kWh"
    if unit == PowerUnit.WATT.value:
        return "Wh"
    return unit
