import pytest

from smart_common.schemas.scheduler_schema import SchedulerSlotIn


def _base_slot_payload() -> dict:
    return {
        "day_of_week": "MONDAY",
        "start_local_time": "04:30",
        "end_local_time": "07:00",
        "start_utc_time": "03:30",
        "end_utc_time": "06:00",
        "start_time": "03:30",
        "end_time": "06:00",
    }


def test_scheduler_slot_requires_policy_for_policy_control_mode() -> None:
    payload = {
        **_base_slot_payload(),
        "control_mode": "POLICY",
    }

    with pytest.raises(ValueError, match="control_policy is required"):
        SchedulerSlotIn(**payload)


def test_scheduler_slot_accepts_temperature_policy() -> None:
    payload = {
        **_base_slot_payload(),
        "control_mode": "POLICY",
        "control_policy": {
            "policy_type": "TEMPERATURE_HYSTERESIS",
            "sensor_id": "tank-top",
            "target_temperature_c": 65,
            "stop_above_target_delta_c": 0,
            "start_below_target_delta_c": 10,
            "heat_up_on_activate": True,
            "end_behavior": "FORCE_OFF",
        },
    }

    slot = SchedulerSlotIn(**payload)

    assert slot.control_mode.value == "POLICY"
    assert slot.control_policy is not None
    assert slot.control_policy.sensor_id == "tank-top"
