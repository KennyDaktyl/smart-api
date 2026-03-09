from smart_common.enums.provider_telemetry import (
    ProviderTelemetryCapability,
    TelemetryAggregationMode,
    TelemetryChartType,
)
from smart_common.enums.unit import PowerUnit
from smart_common.providers.adapters.goodwe import GoodWeProviderAdapter
from smart_common.providers.enums import ProviderPowerSource


def _build_adapter() -> GoodWeProviderAdapter:
    return GoodWeProviderAdapter(
        username="user",
        password="secret",
        provider_id=7,
        provider_external_id="station-1",
        provider_power_source=ProviderPowerSource.METER,
    )


def test_goodwe_fetch_measurement_exposes_dynamic_metrics_for_export(monkeypatch):
    adapter = _build_adapter()
    snapshot = {
        "hasPowerflow": True,
        "powerflow": {
            "grid": "820W",
            "loadStatus": -1,
            "soc": "63",
            "pv": "1450W",
        },
    }
    monkeypatch.setattr(adapter, "_get_powerflow_snapshot", lambda _: snapshot)

    measurement = adapter.fetch_measurement()
    metrics = {metric.key: metric for metric in measurement.extra_metrics}

    assert measurement.value == 820.0
    assert measurement.unit == PowerUnit.WATT.value

    assert metrics["grid_power"].value == 820.0
    assert metrics["grid_power"].unit == PowerUnit.WATT.value
    assert metrics["grid_power"].chart_type == TelemetryChartType.BAR
    assert (
        metrics["grid_power"].aggregation_mode
        == TelemetryAggregationMode.HOURLY_INTEGRAL
    )
    assert (
        metrics["grid_power"].capability_tag
        == ProviderTelemetryCapability.POWER_METER
    )

    assert metrics["battery_soc"].value == 63.0
    assert metrics["battery_soc"].unit == PowerUnit.PERCENT.value
    assert metrics["battery_soc"].chart_type == TelemetryChartType.LINE
    assert metrics["battery_soc"].aggregation_mode == TelemetryAggregationMode.RAW
    assert (
        metrics["battery_soc"].capability_tag
        == ProviderTelemetryCapability.ENERGY_STORAGE
    )


def test_goodwe_fetch_measurement_uses_negative_grid_metric_for_import(monkeypatch):
    adapter = _build_adapter()
    snapshot = {
        "hasPowerflow": True,
        "powerflow": {
            "grid": 410,
            "loadStatus": 1,
            "pv": 950,
        },
    }
    monkeypatch.setattr(adapter, "_get_powerflow_snapshot", lambda _: snapshot)

    measurement = adapter.fetch_measurement()
    metrics = {metric.key: metric for metric in measurement.extra_metrics}

    assert measurement.value == -410.0
    assert metrics["grid_power"].value == -410.0
    assert "battery_soc" not in metrics
