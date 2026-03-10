from types import SimpleNamespace
from uuid import uuid4

import app.api.routes.providers as provider_routes
from smart_common.providers.enums import (
    ProviderKind,
    ProviderPowerSource,
    ProviderType,
    ProviderVendor,
)
from smart_common.schemas.provider_schema import (
    ProviderCreateRequest,
    ProviderUpdateRequest,
)
from smart_common.services.provider_service import ProviderService


def test_create_provider_passes_capability_flags_to_service(monkeypatch) -> None:
    captured: dict[str, object] = {}
    provider = SimpleNamespace(uuid=uuid4())

    class DummyProviderService:
        def __init__(self, provider_repo_factory, microcontroller_repo_factory):
            pass

        def create_for_user(self, db, user_id, payload):
            captured["payload"] = payload
            captured["user_id"] = user_id
            return provider

        def create_provider_from_wizard(self, db, user_id, wizard_session_id, payload):
            raise AssertionError("Wizard path should not be used")

    monkeypatch.setattr(provider_routes, "ProviderService", DummyProviderService)

    payload = ProviderCreateRequest(
        name="GoodWe garage",
        provider_type=ProviderType.API,
        kind=ProviderKind.POWER,
        vendor=ProviderVendor.GOODWE,
        power_source=ProviderPowerSource.METER,
        value_min=-5000,
        value_max=10000,
        has_power_meter=True,
        has_energy_storage=True,
    )

    result = provider_routes.create_provider(
        payload=payload,
        db=object(),
        current_user=SimpleNamespace(id=17),
    )

    assert result is provider
    assert captured["user_id"] == 17
    assert captured["payload"]["has_power_meter"] is True
    assert captured["payload"]["has_energy_storage"] is True


def test_update_provider_passes_capability_flags_to_service(monkeypatch) -> None:
    provider = SimpleNamespace(uuid=uuid4())
    captured: dict[str, object] = {}

    class DummyProviderService:
        def __init__(self, provider_repo_factory, microcontroller_repo_factory):
            pass

        def update_by_uuid(self, db, user_id, provider_uuid, payload):
            captured["payload"] = payload
            captured["provider_uuid"] = provider_uuid
            captured["user_id"] = user_id
            return provider

    monkeypatch.setattr(provider_routes, "ProviderService", DummyProviderService)

    target_uuid = uuid4()
    payload = ProviderUpdateRequest(
        has_power_meter=True,
        has_energy_storage=False,
    )

    result = provider_routes.update_provider(
        provider_uuid=target_uuid,
        payload=payload,
        db=object(),
        current_user=SimpleNamespace(id=21),
    )

    assert result is provider
    assert captured["provider_uuid"] == target_uuid
    assert captured["user_id"] == 21
    assert captured["payload"] == {
        "has_power_meter": True,
        "has_energy_storage": False,
    }


def test_provider_service_update_applies_capability_flags() -> None:
    service = ProviderService(
        provider_repo_factory=lambda session: None,  # type: ignore[arg-type]
        microcontroller_repo_factory=None,
    )
    provider = SimpleNamespace(
        id=1,
        value_min=0.0,
        value_max=10.0,
        has_power_meter=False,
        has_energy_storage=False,
        enabled=False,
        config={},
    )

    class DummyDb:
        def commit(self):
            return None

        def refresh(self, obj):
            return None

    service._ensure_provider = lambda db, user_id, provider_id: provider  # type: ignore[method-assign]
    service._is_provider_attached = lambda db, provider_obj: True  # type: ignore[method-assign]

    result = service.update(
        db=DummyDb(),
        user_id=99,
        provider_id=1,
        payload={
            "has_power_meter": True,
            "has_energy_storage": True,
        },
    )

    assert result is provider
    assert provider.has_power_meter is True
    assert provider.has_energy_storage is True
