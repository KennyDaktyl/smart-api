from smart_common.events.device_events import DeviceCreatedPayload, DeviceUpdatedPayload


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
                        "source": "provider_battery_soc",
                        "comparator": "gte",
                        "value": 30.0,
                        "unit": "%",
                    },
                ],
            }
        ],
    }


def test_device_created_payload_serializes_auto_rule() -> None:
    payload = DeviceCreatedPayload(
        device_id=11,
        device_uuid="2f4a3698-8388-43c1-bdba-ae9c402bd69d",
        device_number=1,
        mode="AUTO",
        threshold_value=None,
        threshold_unit="W",
        auto_rule=_nested_auto_rule(),
        scheduler_id=None,
        microcontroller_uuid="6dd3d49d-a919-4208-a6ff-5463afb5c020",
    )

    dumped = payload.model_dump(mode="json")

    assert dumped["auto_rule"]["operator"] == "ANY"
    assert dumped["threshold_value"] is None
    assert dumped["threshold_unit"] == "W"


def test_device_updated_payload_serializes_threshold_and_auto_rule() -> None:
    payload = DeviceUpdatedPayload(
        device_id=11,
        device_uuid="2f4a3698-8388-43c1-bdba-ae9c402bd69d",
        device_number=1,
        mode="AUTO",
        threshold_value=None,
        threshold_unit="W",
        auto_rule=_nested_auto_rule(),
        scheduler_id=7,
    )

    dumped = payload.model_dump(mode="json")

    assert dumped["threshold_value"] is None
    assert dumped["threshold_unit"] == "W"
    assert dumped["auto_rule"]["items"][0]["operator"] == "ALL"
