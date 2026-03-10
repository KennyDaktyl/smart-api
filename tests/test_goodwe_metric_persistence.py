from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from smart_common.enums.provider_telemetry import (
    ProviderTelemetryCapability,
    TelemetryAggregationMode,
    TelemetryChartType,
)
from smart_common.enums.unit import PowerUnit
from smart_common.repositories.measurement_repository import MeasurementRepository
from smart_common.schemas.normalized_measurement import (
    NormalizedMeasurement,
    NormalizedMetric,
)


class FakeQuery:
    def __init__(self, result=None):
        self._result = result

    def filter(self, *args, **kwargs):
        return self

    def filter_by(self, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def first(self):
        return self._result

    def delete(self, synchronize_session=False):
        return 0


class FakeSession:
    def __init__(self):
        self.added = []
        self.flushed = 0

    def add(self, obj):
        if getattr(obj, "__tablename__", None) == "provider_measurements" and getattr(
            obj, "id", None
        ) is None:
            obj.id = 501

        self.added.append(obj)

    def flush(self):
        self.flushed += 1

    def query(self, model):
        return FakeQuery(None)

    def get(self, model, key):
        return None


def test_save_measurement_persists_dynamic_metric_definitions_and_samples():
    session = FakeSession()
    repo = MeasurementRepository(session)
    provider = SimpleNamespace(
        id=7,
        has_power_meter=True,
        has_energy_storage=True,
    )
    measured_at = datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc)
    measurement = NormalizedMeasurement(
        provider_id=7,
        value=820.0,
        unit=PowerUnit.WATT.value,
        measured_at=measured_at,
        metadata={},
        extra_metrics=[
            NormalizedMetric(
                key="battery_soc",
                value=55.0,
                unit=PowerUnit.PERCENT.value,
                label="Battery SOC",
                chart_type=TelemetryChartType.LINE,
                aggregation_mode=TelemetryAggregationMode.RAW,
                capability_tag=ProviderTelemetryCapability.ENERGY_STORAGE,
            ),
            NormalizedMetric(
                key="grid_power",
                value=820.0,
                unit=PowerUnit.WATT.value,
                label="Grid power",
                chart_type=TelemetryChartType.BAR,
                aggregation_mode=TelemetryAggregationMode.HOURLY_INTEGRAL,
                capability_tag=ProviderTelemetryCapability.POWER_METER,
            ),
        ],
    )

    entry = repo.save_measurement(provider, measurement)

    definitions = [
        obj for obj in session.added if getattr(obj, "__tablename__", None) == "provider_metric_definitions"
    ]
    samples = [
        obj for obj in session.added if getattr(obj, "__tablename__", None) == "provider_metric_samples"
    ]

    assert entry is not None
    assert entry.provider_id == provider.id
    assert len(definitions) == 2
    assert {definition.metric_key for definition in definitions} == {
        "battery_soc",
        "grid_power",
    }
    assert len(samples) == 2
    assert {sample.metric_key for sample in samples} == {
        "battery_soc",
        "grid_power",
    }
    assert {sample.provider_measurement_id for sample in samples} == {entry.id}
    assert {sample.unit for sample in samples} == {"%", "W"}
