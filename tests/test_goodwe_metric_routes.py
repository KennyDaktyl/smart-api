from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.api.routes import provider_measurements as routes
from smart_common.enums.provider_telemetry import (
    ProviderTelemetryCapability,
    TelemetryAggregationMode,
    TelemetryChartType,
)
from smart_common.enums.unit import PowerUnit
from smart_common.providers.enums import (
    ProviderKind,
    ProviderPowerSource,
    ProviderType,
    ProviderVendor,
)


def test_metric_series_returns_raw_entries_for_battery_soc(monkeypatch):
    provider_uuid = uuid4()
    provider = SimpleNamespace(id=7, uuid=provider_uuid, user_id=3)
    current_user = SimpleNamespace(id=3)

    class FakeProviderRepo:
        def __init__(self, db):
            self.db = db

        def get_for_user_by_uuid(self, *, provider_uuid, user_id):
            assert user_id == current_user.id
            return provider if provider_uuid == provider.uuid else None

    class FakeMeasurementRepo:
        def __init__(self, db):
            self.db = db

        def get_metric_definition(self, *, provider_id, metric_key):
            assert provider_id == provider.id
            assert metric_key == "battery_soc"
            return SimpleNamespace(
                metric_key="battery_soc",
                label="Battery SOC",
                unit="%",
                chart_type=TelemetryChartType.LINE,
                aggregation_mode=TelemetryAggregationMode.RAW,
                capability_tag=ProviderTelemetryCapability.ENERGY_STORAGE,
            )

        def list_metric_samples(self, *, provider_id, metric_key, date_start, date_end):
            assert provider_id == provider.id
            assert metric_key == "battery_soc"
            return [
                SimpleNamespace(
                    measured_at=datetime(2026, 3, 10, 9, 15, tzinfo=timezone.utc),
                    value=55.0,
                ),
                SimpleNamespace(
                    measured_at=datetime(2026, 3, 10, 9, 45, tzinfo=timezone.utc),
                    value=57.5,
                ),
            ]

    monkeypatch.setattr(routes, "ProviderRepository", FakeProviderRepo)
    monkeypatch.setattr(routes, "MeasurementRepository", FakeMeasurementRepo)

    result = routes.get_provider_metric_series(
        provider_uuid=provider_uuid,
        metric_key="battery_soc",
        selected_date=date(2026, 3, 10),
        db=object(),
        current_user=current_user,
    )

    assert result.metric_key == "battery_soc"
    assert result.chart_type == TelemetryChartType.LINE
    assert result.aggregation_mode == TelemetryAggregationMode.RAW
    assert result.capability_tag == ProviderTelemetryCapability.ENERGY_STORAGE
    assert result.unit == "%"
    assert result.source_unit == "%"
    assert result.date == "2026-03-10"
    assert [(entry.timestamp.hour, entry.timestamp.minute, entry.value) for entry in result.entries] == [
        (9, 15, 55.0),
        (9, 45, 57.5),
    ]
    assert result.hours == []


def test_metric_series_returns_hourly_energy_for_grid_power(monkeypatch):
    provider_uuid = uuid4()
    provider = SimpleNamespace(id=8, uuid=provider_uuid, user_id=4)
    current_user = SimpleNamespace(id=4)

    class FakeProviderRepo:
        def __init__(self, db):
            self.db = db

        def get_for_user_by_uuid(self, *, provider_uuid, user_id):
            assert user_id == current_user.id
            return provider if provider_uuid == provider.uuid else None

    class FakeMeasurementRepo:
        def __init__(self, db):
            self.db = db

        def get_metric_definition(self, *, provider_id, metric_key):
            assert provider_id == provider.id
            assert metric_key == "grid_power"
            return SimpleNamespace(
                metric_key="grid_power",
                label="Grid power",
                unit="W",
                chart_type=TelemetryChartType.BAR,
                aggregation_mode=TelemetryAggregationMode.HOURLY_INTEGRAL,
                capability_tag=ProviderTelemetryCapability.POWER_METER,
            )

        def list_metric_samples(self, *, provider_id, metric_key, date_start, date_end):
            assert provider_id == provider.id
            assert metric_key == "grid_power"
            return [
                SimpleNamespace(
                    measured_at=datetime(2026, 3, 10, 10, 0, tzinfo=timezone.utc),
                    value=100.0,
                ),
                SimpleNamespace(
                    measured_at=datetime(2026, 3, 10, 11, 0, tzinfo=timezone.utc),
                    value=200.0,
                ),
                SimpleNamespace(
                    measured_at=datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc),
                    value=0.0,
                ),
            ]

    monkeypatch.setattr(routes, "ProviderRepository", FakeProviderRepo)
    monkeypatch.setattr(routes, "MeasurementRepository", FakeMeasurementRepo)

    result = routes.get_provider_metric_series(
        provider_uuid=provider_uuid,
        metric_key="grid_power",
        selected_date=date(2026, 3, 10),
        db=object(),
        current_user=current_user,
    )

    assert result.metric_key == "grid_power"
    assert result.chart_type == TelemetryChartType.BAR
    assert result.aggregation_mode == TelemetryAggregationMode.HOURLY_INTEGRAL
    assert result.capability_tag == ProviderTelemetryCapability.POWER_METER
    assert result.unit == "Wh"
    assert result.source_unit == "W"
    assert result.entries == []
    assert [(point.hour.hour, point.value) for point in result.hours] == [
        (10, 100.0),
        (11, 200.0),
    ]


def test_provider_telemetry_returns_day_and_synthetic_metrics(monkeypatch):
    provider_uuid = uuid4()
    provider = SimpleNamespace(
        id=9,
        uuid=provider_uuid,
        name="GoodWe roof",
        provider_type=ProviderType.API,
        kind=ProviderKind.POWER,
        vendor=ProviderVendor.GOODWE,
        external_id="station-1",
        unit=PowerUnit.WATT,
        power_source=ProviderPowerSource.METER,
        value_min=-5000.0,
        value_max=10000.0,
        default_expected_interval_sec=None,
        has_power_meter=True,
        has_energy_storage=True,
        enabled=True,
        config={},
        telemetry_metrics=[],
        created_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 3, 10, tzinfo=timezone.utc),
        last_value=None,
        user_id=5,
    )
    current_user = SimpleNamespace(id=5)

    class FakeProviderRepo:
        def __init__(self, db):
            self.db = db

        def get_for_user_by_uuid(self, *, provider_uuid, user_id):
            assert user_id == current_user.id
            return provider if provider_uuid == provider.uuid else None

    class FakeMeasurementRepo:
        def __init__(self, db):
            self.db = db

        def list_power_samples(self, *, provider_id, date_start, date_end):
            assert provider_id == provider.id
            return [
                (datetime(2026, 3, 10, 10, 0, tzinfo=timezone.utc), 100.0),
                (datetime(2026, 3, 10, 11, 0, tzinfo=timezone.utc), 200.0),
            ]

        def list_measurements(self, *, provider_id, date_start, date_end):
            assert provider_id == provider.id
            return [
                SimpleNamespace(
                    id=1001,
                    measured_at=datetime(2026, 3, 10, 10, 0, tzinfo=timezone.utc),
                    measured_value=100.0,
                    measured_unit="W",
                    metadata_payload={},
                    extra_data={},
                )
            ]

        def list_metric_definitions(self, *, provider_id):
            assert provider_id == provider.id
            return []

        def list_metric_samples(self, *, provider_id, metric_key, date_start, date_end):
            assert provider_id == provider.id
            if metric_key == "battery_soc":
                return [
                    SimpleNamespace(
                        measured_at=datetime(2026, 3, 10, 10, 15, tzinfo=timezone.utc),
                        value=55.0,
                    ),
                    SimpleNamespace(
                        measured_at=datetime(2026, 3, 10, 10, 45, tzinfo=timezone.utc),
                        value=57.0,
                    ),
                ]

            if metric_key == "grid_power":
                return [
                    SimpleNamespace(
                        measured_at=datetime(2026, 3, 10, 10, 0, tzinfo=timezone.utc),
                        value=100.0,
                    ),
                    SimpleNamespace(
                        measured_at=datetime(2026, 3, 10, 11, 0, tzinfo=timezone.utc),
                        value=200.0,
                    ),
                    SimpleNamespace(
                        measured_at=datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc),
                        value=0.0,
                    ),
                ]

            return []

        def get_metric_definition(self, *, provider_id, metric_key):
            return None

        def get_last_power_sample_before(self, *, provider_id, before):
            assert provider_id == provider.id
            return None

    class FakeMarketPriceRepo:
        def __init__(self, db):
            self.db = db

        def get_active_at(self, *, market, timestamp):
            return None

        def get_latest_before(self, *, market, timestamp):
            if market == "RCE":
                return SimpleNamespace(
                    market="RCE",
                    interval_start=datetime(2026, 3, 10, 11, 0, tzinfo=timezone.utc),
                    interval_end=datetime(2026, 3, 10, 11, 15, tzinfo=timezone.utc),
                    price_value=450.0,
                    currency="PLN",
                    price_unit="MWh",
                    source_updated_at=datetime(2026, 3, 9, 13, 44, tzinfo=timezone.utc),
                )

            if market == "RCE_FCST":
                return SimpleNamespace(
                    market="RCE_FCST",
                    interval_start=datetime(2026, 3, 10, 11, 0, tzinfo=timezone.utc),
                    interval_end=datetime(2026, 3, 10, 11, 15, tzinfo=timezone.utc),
                    price_value=520.0,
                    currency="PLN",
                    price_unit="MWh",
                    source_updated_at=datetime(2026, 3, 10, 10, 55, tzinfo=timezone.utc),
                )

            return None

        def list_between(self, *, market, date_start, date_end):
            if market == "RCE":
                return [
                    SimpleNamespace(
                        market="RCE",
                        interval_start=datetime(2026, 3, 10, 10, 0, tzinfo=timezone.utc),
                        interval_end=datetime(2026, 3, 10, 10, 15, tzinfo=timezone.utc),
                        price_value=400.0,
                        currency="PLN",
                        price_unit="MWh",
                    ),
                    SimpleNamespace(
                        market="RCE",
                        interval_start=datetime(2026, 3, 10, 11, 0, tzinfo=timezone.utc),
                        interval_end=datetime(2026, 3, 10, 11, 15, tzinfo=timezone.utc),
                        price_value=450.0,
                        currency="PLN",
                        price_unit="MWh",
                    ),
                ]

            if market == "RCE_FCST":
                return [
                    SimpleNamespace(
                        market="RCE_FCST",
                        interval_start=datetime(2026, 3, 10, 10, 0, tzinfo=timezone.utc),
                        interval_end=datetime(2026, 3, 10, 10, 15, tzinfo=timezone.utc),
                        price_value=410.0,
                        currency="PLN",
                        price_unit="MWh",
                    ),
                    SimpleNamespace(
                        market="RCE_FCST",
                        interval_start=datetime(2026, 3, 10, 11, 0, tzinfo=timezone.utc),
                        interval_end=datetime(2026, 3, 10, 11, 15, tzinfo=timezone.utc),
                        price_value=520.0,
                        currency="PLN",
                        price_unit="MWh",
                    ),
                ]

            return []

    monkeypatch.setattr(routes, "ProviderRepository", FakeProviderRepo)
    monkeypatch.setattr(routes, "MeasurementRepository", FakeMeasurementRepo)
    monkeypatch.setattr(routes, "MarketEnergyPriceRepository", FakeMarketPriceRepo)

    result = routes.get_provider_telemetry(
        provider_uuid=provider_uuid,
        selected_date=date(2026, 3, 10),
        db=object(),
        current_user=current_user,
    )

    assert result.provider.uuid == provider_uuid
    assert result.provider.has_power_meter is True
    assert result.provider.has_energy_storage is True
    assert result.date == "2026-03-10"
    assert result.day.date == "2026-03-10"
    assert result.measured_unit == "W"
    assert result.energy_unit == "Wh"

    metrics = {metric.metric_key: metric for metric in result.metrics}
    assert set(metrics.keys()) == {"battery_soc", "grid_power"}
    assert [entry.value for entry in metrics["battery_soc"].entries] == [55.0, 57.0]
    assert [(point.hour.hour, point.value) for point in metrics["grid_power"].hours] == [
        (10, 100.0),
        (11, 200.0),
    ]
    assert result.settlement_price is not None
    assert result.settlement_price.market == "RCE"
    assert result.settlement_price.price == 450.0
    assert result.settlement_price.price_per_energy_unit == 0.00045
    assert result.settlement_price.energy_unit == "Wh"
    assert len(result.settlement_price.history) == 2
    assert result.forecast_price is not None
    assert result.forecast_price.market == "RCE_FCST"
    assert result.forecast_price.price == 520.0
    assert result.forecast_price.price_per_energy_unit == 0.00052
    assert len(result.forecast_price.history) == 2
    assert result.matched_revenue is not None
    assert result.matched_revenue.market == "RCE"
    assert result.matched_revenue.total_export_energy == 75.0
    assert result.matched_revenue.total_revenue == 0.0325
    assert result.matched_revenue.matched_intervals == 2


def test_provider_telemetry_splits_energy_across_hour_boundaries(monkeypatch):
    provider_uuid = uuid4()
    provider = SimpleNamespace(
        id=10,
        uuid=provider_uuid,
        name="Boundary test",
        provider_type=ProviderType.API,
        kind=ProviderKind.POWER,
        vendor=ProviderVendor.GOODWE,
        external_id="station-2",
        unit=PowerUnit.WATT,
        power_source=ProviderPowerSource.METER,
        value_min=-5000.0,
        value_max=10000.0,
        default_expected_interval_sec=None,
        has_power_meter=True,
        has_energy_storage=False,
        enabled=True,
        config={},
        telemetry_metrics=[],
        created_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 3, 10, tzinfo=timezone.utc),
        last_value=None,
        user_id=6,
    )
    current_user = SimpleNamespace(id=6)

    class FakeProviderRepo:
        def __init__(self, db):
            self.db = db

        def get_for_user_by_uuid(self, *, provider_uuid, user_id):
            assert user_id == current_user.id
            return provider if provider_uuid == provider.uuid else None

    class FakeMeasurementRepo:
        def __init__(self, db):
            self.db = db

        def list_power_samples(self, *, provider_id, date_start, date_end):
            assert provider_id == provider.id
            return [
                (datetime(2026, 3, 10, 10, 30, tzinfo=timezone.utc), 120.0),
                (datetime(2026, 3, 10, 11, 30, tzinfo=timezone.utc), 0.0),
            ]

        def list_measurements(self, *, provider_id, date_start, date_end):
            assert provider_id == provider.id
            return []

        def list_metric_definitions(self, *, provider_id):
            assert provider_id == provider.id
            return []

        def list_metric_samples(self, *, provider_id, metric_key, date_start, date_end):
            return []

        def get_metric_definition(self, *, provider_id, metric_key):
            return None

        def get_last_power_sample_before(self, *, provider_id, before):
            assert provider_id == provider.id
            return None

    class FakeMarketPriceRepo:
        def __init__(self, db):
            self.db = db

        def get_active_at(self, *, market, timestamp):
            return None

        def get_latest_before(self, *, market, timestamp):
            return None

        def list_between(self, *, market, date_start, date_end):
            if market == "RCE_FCST":
                return []
            return [
                SimpleNamespace(
                    market="RCE",
                    interval_start=datetime(2026, 3, 10, 10, 30, tzinfo=timezone.utc),
                    interval_end=datetime(2026, 3, 10, 11, 0, tzinfo=timezone.utc),
                    price_value=500.0,
                    currency="PLN",
                    price_unit="MWh",
                ),
                SimpleNamespace(
                    market="RCE",
                    interval_start=datetime(2026, 3, 10, 11, 0, tzinfo=timezone.utc),
                    interval_end=datetime(2026, 3, 10, 11, 30, tzinfo=timezone.utc),
                    price_value=200.0,
                    currency="PLN",
                    price_unit="MWh",
                ),
            ]

    monkeypatch.setattr(routes, "ProviderRepository", FakeProviderRepo)
    monkeypatch.setattr(routes, "MeasurementRepository", FakeMeasurementRepo)
    monkeypatch.setattr(routes, "MarketEnergyPriceRepository", FakeMarketPriceRepo)

    result = routes.get_provider_telemetry(
        provider_uuid=provider_uuid,
        selected_date=date(2026, 3, 10),
        db=object(),
        current_user=current_user,
    )

    assert [(point.hour.hour, point.energy) for point in result.day.hours] == [
        (10, 60.0),
        (11, 60.0),
    ]
    assert result.day.export_energy == 120.0
    assert result.matched_revenue is not None
    assert result.matched_revenue.total_export_energy == 120.0
    assert result.matched_revenue.total_revenue == 0.042
    assert [(point.hour.hour, point.revenue) for point in result.day.hours] == [
        (10, 0.03),
        (11, 0.012),
    ]


def test_provider_telemetry_does_not_carry_stale_value_across_night(monkeypatch):
    provider_uuid = uuid4()
    provider = SimpleNamespace(
        id=11,
        uuid=provider_uuid,
        name="Night gap",
        provider_type=ProviderType.API,
        kind=ProviderKind.POWER,
        vendor=ProviderVendor.HUAWEI,
        external_id="station-3",
        unit=PowerUnit.KILOWATT,
        power_source=ProviderPowerSource.INVERTER,
        value_min=0.0,
        value_max=10.0,
        default_expected_interval_sec=180,
        has_power_meter=False,
        has_energy_storage=False,
        enabled=True,
        config={},
        telemetry_metrics=[],
        created_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 3, 10, tzinfo=timezone.utc),
        last_value=None,
        user_id=7,
    )
    current_user = SimpleNamespace(id=7)

    class FakeProviderRepo:
        def __init__(self, db):
            self.db = db

        def get_for_user_by_uuid(self, *, provider_uuid, user_id):
            assert user_id == current_user.id
            return provider if provider_uuid == provider.uuid else None

    class FakeMeasurementRepo:
        def __init__(self, db):
            self.db = db

        def list_power_samples(self, *, provider_id, date_start, date_end):
            assert provider_id == provider.id
            return [
                (datetime(2026, 3, 13, 6, 36, tzinfo=timezone.utc), 1.5),
                (datetime(2026, 3, 13, 6, 39, tzinfo=timezone.utc), 1.5),
            ]

        def list_measurements(self, *, provider_id, date_start, date_end):
            return []

        def list_metric_definitions(self, *, provider_id):
            return []

        def list_metric_samples(self, *, provider_id, metric_key, date_start, date_end):
            return []

        def get_metric_definition(self, *, provider_id, metric_key):
            return None

        def get_last_power_sample_before(self, *, provider_id, before):
            assert provider_id == provider.id
            return (datetime(2026, 3, 12, 23, 57, tzinfo=timezone.utc), 0.16)

    class FakeMarketPriceRepo:
        def __init__(self, db):
            self.db = db

        def get_active_at(self, *, market, timestamp):
            return None

        def get_latest_before(self, *, market, timestamp):
            return None

        def list_between(self, *, market, date_start, date_end):
            return []

    monkeypatch.setattr(routes, "ProviderRepository", FakeProviderRepo)
    monkeypatch.setattr(routes, "MeasurementRepository", FakeMeasurementRepo)
    monkeypatch.setattr(routes, "MarketEnergyPriceRepository", FakeMarketPriceRepo)

    result = routes.get_provider_telemetry(
        provider_uuid=provider_uuid,
        selected_date=date(2026, 3, 13),
        db=object(),
        current_user=current_user,
    )

    assert [(point.hour.hour, point.energy) for point in result.day.hours] == [
        (6, 0.45),
    ]
