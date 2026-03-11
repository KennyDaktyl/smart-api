from types import SimpleNamespace
from uuid import uuid4

from smart_common.enums.device import DeviceMode
from smart_common.schemas.device_schema import (
    DeviceCreateRequest,
    DeviceResponse,
    DeviceUpdateRequest,
)


def _nested_auto_rule() -> dict:
    return {
        "operator": "ANY",
        "items": [
            {
                "operator": "ALL",
                "items": [
                    {
                        "source": "provider_primary_power",
                        "comparator": "gte",
                        "value": 2.0,
                        "unit": "W",
                    },
                    {
                        "source": "provider_primary_power",
                        "comparator": "gte",
                        "value": 2.0,
                        "unit": "W",
                    },
                ],
            },
            {
                "operator": "ANY",
                "items": [
                    {
                        "source": "provider_battery_soc",
                        "comparator": "gte",
                        "value": 30.0,
                        "unit": "%",
                    }
                ],
            },
        ],
    }


def test_device_create_request_accepts_nested_auto_rule() -> None:
    request = DeviceCreateRequest(
        name="Pompa",
        device_number=1,
        mode=DeviceMode.AUTO_POWER,
        auto_rule=_nested_auto_rule(),
    )

    assert request.auto_rule is not None
    assert request.auto_rule.operator == "ANY"
    assert request.threshold_value is None


def test_device_update_request_accepts_nested_auto_rule() -> None:
    request = DeviceUpdateRequest(
        mode=DeviceMode.AUTO_POWER,
        auto_rule=_nested_auto_rule(),
    )

    assert request.auto_rule is not None
    assert request.auto_rule.operator == "ANY"
    assert request.threshold_value is None


def test_device_response_exposes_auto_rule_from_auto_rule_json() -> None:
    response = DeviceResponse.model_validate(
        SimpleNamespace(
            id=7,
            uuid=uuid4(),
            microcontroller_id=3,
            name="Pompa",
            device_number=1,
            mode=DeviceMode.AUTO_POWER,
            scheduler_id=None,
            rated_power=1200.0,
            threshold_value=None,
            auto_rule_json=_nested_auto_rule(),
            manual_state=False,
            last_state_change_at=None,
            created_at="2026-03-11T10:00:00Z",
            updated_at="2026-03-11T10:00:00Z",
        ),
        from_attributes=True,
    )

    assert response.auto_rule is not None
    assert response.auto_rule.operator == "ANY"
    assert response.threshold_value is None
