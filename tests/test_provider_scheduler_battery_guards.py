from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from smart_common.services.microcontroller_service import MicrocontrollerService
from smart_common.services.provider_service import ProviderService


def _scheduler_slot_with_battery_rule():
    return SimpleNamespace(
        activation_rule_json={
            "operator": "ANY",
            "items": [
                {
                    "source": "provider_battery_soc",
                    "comparator": "gte",
                    "value": 30.0,
                    "unit": "%",
                }
            ],
        }
    )


def _device_with_scheduler_battery_rule():
    return SimpleNamespace(
        auto_rule_json=None,
        threshold_value=None,
        scheduler=SimpleNamespace(
            slots=[_scheduler_slot_with_battery_rule()],
        ),
    )


def test_microcontroller_service_blocks_provider_without_storage_for_scheduler_rules():
    service = MicrocontrollerService(
        repo_factory=lambda session: None,  # type: ignore[arg-type]
        provider_repo_factory=lambda session: None,  # type: ignore[arg-type]
    )
    microcontroller = SimpleNamespace(devices=[_device_with_scheduler_battery_rule()])
    provider = SimpleNamespace(has_energy_storage=False, unit=None)

    with pytest.raises(HTTPException) as exc_info:
        service._ensure_provider_supports_existing_device_rules(
            microcontroller=microcontroller,
            provider=provider,
        )

    assert exc_info.value.status_code == 400
    assert "scheduler devices" in str(exc_info.value.detail)


class _FakeQuery:
    def __init__(self, result):
        self._result = result

    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return self._result


class _FakeDb:
    def __init__(self, microcontrollers):
        self._microcontrollers = microcontrollers

    def query(self, model):
        return _FakeQuery(self._microcontrollers)


def test_provider_service_blocks_disabling_storage_for_scheduler_rules():
    service = ProviderService(
        provider_repo_factory=lambda session: None,  # type: ignore[arg-type]
        microcontroller_repo_factory=lambda session: None,  # type: ignore[arg-type]
    )
    provider = SimpleNamespace(id=7, has_energy_storage=True, unit=None)
    db = _FakeDb(
        [SimpleNamespace(devices=[_device_with_scheduler_battery_rule()])]
    )

    with pytest.raises(HTTPException) as exc_info:
        service._ensure_capability_change_is_safe(
            db,
            provider=provider,
            changes={"has_energy_storage": False},
        )

    assert exc_info.value.status_code == 400
    assert "scheduler devices" in str(exc_info.value.detail)
