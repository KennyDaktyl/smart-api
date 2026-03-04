from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import app.api.routes.schedulers as scheduler_routes
from smart_common.providers.enums import ProviderKind


def _slots_with_threshold(provider_id: int) -> list[dict]:
    return [
        {
            "use_power_threshold": True,
            "power_provider_id": provider_id,
        }
    ]


def test_validate_slot_providers_rejects_missing_provider(monkeypatch) -> None:
    class DummyProviderRepository:
        def __init__(self, db):
            self.db = db

        def get_for_user(self, provider_id: int, user_id: int):
            assert provider_id == 10
            assert user_id == 123
            return None

    monkeypatch.setattr(
        scheduler_routes,
        "ProviderRepository",
        DummyProviderRepository,
    )

    with pytest.raises(HTTPException) as exc:
        scheduler_routes._validate_slot_providers(
            db=object(),
            user_id=123,
            slots=_slots_with_threshold(10),
        )

    assert exc.value.status_code == 404


def test_validate_slot_providers_rejects_non_power_provider(monkeypatch) -> None:
    class DummyProviderRepository:
        def __init__(self, db):
            self.db = db

        def get_for_user(self, provider_id: int, user_id: int):
            assert provider_id == 11
            assert user_id == 123
            return SimpleNamespace(kind=ProviderKind.SENSOR)

    monkeypatch.setattr(
        scheduler_routes,
        "ProviderRepository",
        DummyProviderRepository,
    )

    with pytest.raises(HTTPException) as exc:
        scheduler_routes._validate_slot_providers(
            db=object(),
            user_id=123,
            slots=_slots_with_threshold(11),
        )

    assert exc.value.status_code == 422

