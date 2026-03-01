import pytest
from pydantic import ValidationError

from smart_common.enums.scheduler import SchedulerDayOfWeek
from smart_common.schemas.scheduler_schema import SchedulerSlotIn


def _base_slot_payload() -> dict:
    return {
        "day_of_week": SchedulerDayOfWeek.MONDAY,
        "start_utc_time": "09:00",
        "end_utc_time": "10:00",
    }


def test_scheduler_slot_requires_power_provider_id_for_threshold() -> None:
    payload = _base_slot_payload()
    payload.update(
        {
            "use_power_threshold": True,
            "power_threshold_value": 1.5,
            "power_threshold_unit": "kW",
        }
    )

    with pytest.raises(ValidationError):
        SchedulerSlotIn(**payload)


def test_scheduler_slot_clears_threshold_fields_when_disabled() -> None:
    payload = _base_slot_payload()
    payload.update(
        {
            "use_power_threshold": False,
            "power_provider_id": 11,
            "power_threshold_value": 2.2,
            "power_threshold_unit": "kW",
        }
    )

    slot = SchedulerSlotIn(**payload)

    assert slot.power_provider_id is None
    assert slot.power_threshold_value is None
    assert slot.power_threshold_unit is None

