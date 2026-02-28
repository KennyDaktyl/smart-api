from types import SimpleNamespace
from uuid import uuid4

import app.api.routes.schedulers as scheduler_routes
from smart_common.enums.unit import PowerUnit


def test_get_power_threshold_units_uses_only_user_provider_units(monkeypatch):
    providers = [
        SimpleNamespace(id=1, uuid=uuid4(), name="Provider W", unit=PowerUnit.WATT),
        SimpleNamespace(
            id=2, uuid=uuid4(), name="Provider kW", unit=PowerUnit.KILOWATT
        ),
    ]

    class DummyProviderRepository:
        def __init__(self, db):
            self.db = db

        def list_power_for_user(self, user_id: int):
            assert user_id == 123
            return providers

    monkeypatch.setattr(
        scheduler_routes,
        "ProviderRepository",
        DummyProviderRepository,
    )

    response = scheduler_routes.get_power_threshold_units(
        db=object(),
        current_user=SimpleNamespace(id=123),
    )

    assert response.units == ["W", "kW"]
    assert [provider.unit for provider in response.providers] == ["W", "kW"]


def test_get_power_threshold_units_returns_empty_units_when_no_provider_has_unit(
    monkeypatch,
):
    providers = [
        SimpleNamespace(id=1, uuid=uuid4(), name="No Unit", unit=None),
    ]

    class DummyProviderRepository:
        def __init__(self, db):
            self.db = db

        def list_power_for_user(self, user_id: int):
            assert user_id == 123
            return providers

    monkeypatch.setattr(
        scheduler_routes,
        "ProviderRepository",
        DummyProviderRepository,
    )

    response = scheduler_routes.get_power_threshold_units(
        db=object(),
        current_user=SimpleNamespace(id=123),
    )

    assert response.units == []
    assert response.providers == []
