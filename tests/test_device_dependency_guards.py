from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from smart_common.services.device_service import DeviceService


class _FakeDeviceRepo:
    def __init__(self, devices_by_id):
        self._devices_by_id = devices_by_id

    def get_for_user_by_id(self, device_id: int, user_id: int):
        return self._devices_by_id.get(device_id)


def _service_with_devices(devices_by_id):
    return DeviceService(
        repo_factory=lambda session: _FakeDeviceRepo(devices_by_id),
        microcontroller_repo_factory=lambda session: None,  # type: ignore[arg-type]
        scheduler_repo_factory=lambda session: None,  # type: ignore[arg-type]
    )


def test_dependency_rule_requires_same_microcontroller():
    source_microcontroller = SimpleNamespace(id=1)
    target_device = SimpleNamespace(id=7, microcontroller_id=2, device_number=4)
    service = _service_with_devices({7: target_device})

    with pytest.raises(HTTPException) as exc_info:
        service._normalize_dependency_rule(
            db=None,  # type: ignore[arg-type]
            user_id=1,
            raw_rule={
                "target_device_id": 7,
                "when_source_on": "OFF",
                "when_source_off": "NONE",
            },
            source_microcontroller=source_microcontroller,
            source_device=None,
        )

    assert exc_info.value.status_code == 400
    assert "same microcontroller" in str(exc_info.value.detail)


def test_dependency_rule_blocks_second_source_for_same_target():
    target_device = SimpleNamespace(id=9, microcontroller_id=1, device_number=3)
    other_source = SimpleNamespace(
        id=2,
        mode="AUTO",
        device_dependency_rule_json={
            "target_device_id": 9,
            "target_device_number": 3,
            "when_source_on": "OFF",
            "when_source_off": "NONE",
        },
        scheduler=None,
    )
    microcontroller = SimpleNamespace(devices=[other_source])
    service = _service_with_devices({9: target_device})

    normalized = service._normalize_dependency_rule(
        db=None,  # type: ignore[arg-type]
        user_id=1,
        raw_rule={
            "target_device_id": 9,
            "when_source_on": "ON",
            "when_source_off": "OFF",
        },
        source_microcontroller=SimpleNamespace(id=1),
        source_device=SimpleNamespace(id=1),
    )

    with pytest.raises(HTTPException) as exc_info:
        service._ensure_dependency_target_is_available(
            microcontroller=microcontroller,
            candidate_rules=[normalized],
            exclude_source_device_id=1,
        )

    assert exc_info.value.status_code == 400
    assert "already controlled" in str(exc_info.value.detail)
