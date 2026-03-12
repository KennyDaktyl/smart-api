from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from smart_common.services.device_service import DeviceService


class _FakeSchedulerRepo:
    def __init__(self, scheduler):
        self._scheduler = scheduler

    def get_for_user_by_id(self, scheduler_id: int, user_id: int):
        return self._scheduler


def _build_temperature_policy_scheduler():
    return SimpleNamespace(
        slots=[
            SimpleNamespace(
                control_mode="POLICY",
                control_policy_json={
                    "policy_type": "TEMPERATURE_HYSTERESIS",
                    "sensor_id": "temperature",
                    "target_temperature_c": 65.0,
                    "stop_above_target_delta_c": 0.0,
                    "start_below_target_delta_c": 10.0,
                    "heat_up_on_activate": True,
                    "end_behavior": "FORCE_OFF",
                },
                activation_rule_json=None,
            )
        ]
    )


def _build_service(scheduler):
    return DeviceService(
        repo_factory=lambda session: None,  # type: ignore[arg-type]
        microcontroller_repo_factory=lambda session: None,  # type: ignore[arg-type]
        scheduler_repo_factory=lambda session: _FakeSchedulerRepo(scheduler),
    )


def test_scheduler_temperature_policy_requires_temperature_sensor():
    service = _build_service(_build_temperature_policy_scheduler())
    microcontroller = SimpleNamespace(
        assigned_sensors=[],
        power_provider=SimpleNamespace(has_energy_storage=True),
    )

    with pytest.raises(HTTPException) as exc_info:
        service._ensure_scheduler_for_mode(
            db=None,  # type: ignore[arg-type]
            user_id=7,
            microcontroller=microcontroller,
            new_mode="SCHEDULE",
            scheduler_in_payload=True,
            new_scheduler_id=5,
            current_device=None,
        )

    assert exc_info.value.status_code == 400
    assert "temperature sensor" in str(exc_info.value.detail)


def test_scheduler_temperature_policy_accepts_microcontroller_with_temperature_sensor():
    service = _build_service(_build_temperature_policy_scheduler())
    microcontroller = SimpleNamespace(
        assigned_sensors=["ds18b20"],
        power_provider=SimpleNamespace(has_energy_storage=True),
    )

    service._ensure_scheduler_for_mode(
        db=None,  # type: ignore[arg-type]
        user_id=7,
        microcontroller=microcontroller,
        new_mode="SCHEDULE",
        scheduler_in_payload=True,
        new_scheduler_id=5,
        current_device=None,
    )
