from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from smart_common.services.scheduler_service import SchedulerService


class _FakeSchedulerRepo:
    def create_for_user(self, **kwargs):
        return SimpleNamespace(**kwargs)


class _FakeDeviceRepo:
    def __init__(self, devices_by_id):
        self._devices_by_id = devices_by_id

    def get_for_user_by_id(self, device_id: int, user_id: int):
        return self._devices_by_id.get(device_id)


def _service_with_devices(devices_by_id):
    return SchedulerService(
        repo_factory=lambda session: _FakeSchedulerRepo(),
        device_repo_factory=lambda session: _FakeDeviceRepo(devices_by_id),
    )


def test_scheduler_slot_dependency_rule_resolves_target_device_number():
    service = _service_with_devices(
        {
            7: SimpleNamespace(id=7, device_number=4),
        }
    )

    normalized = service._normalize_slot_dependency_rules(
        db=None,  # type: ignore[arg-type]
        user_id=1,
        slots=[
            {
                "day_of_week": "MONDAY",
                "start_time": "07:30",
                "end_time": "12:00",
                "device_dependency_rule": {
                    "target_device_id": 7,
                    "when_source_on": "OFF",
                    "when_source_off": "NONE",
                },
            }
        ],
    )

    assert normalized[0]["device_dependency_rule"].target_device_id == 7
    assert normalized[0]["device_dependency_rule"].target_device_number == 4


def test_scheduler_slot_dependency_rule_requires_existing_target_device():
    service = _service_with_devices({})

    with pytest.raises(HTTPException) as exc_info:
        service._normalize_slot_dependency_rules(
            db=None,  # type: ignore[arg-type]
            user_id=1,
            slots=[
                {
                    "day_of_week": "MONDAY",
                    "start_time": "07:30",
                    "end_time": "12:00",
                    "device_dependency_rule": {
                        "target_device_id": 99,
                        "when_source_on": "ON",
                        "when_source_off": "OFF",
                    },
                }
            ],
        )

    assert exc_info.value.status_code == 404
    assert "Dependency target device not found" in str(exc_info.value.detail)
