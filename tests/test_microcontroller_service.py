from uuid import uuid4

import pytest
from fastapi import HTTPException

from smart_common.enums.microcontroller import MicrocontrollerType
from smart_common.models.microcontroller import Microcontroller
from smart_common.models.microcontroller_sensor_capability import (
    MicrocontrollerSensorCapability,
)
from smart_common.services.microcontroller_service import MicrocontrollerService


class _FakeSession:
    def flush(self):
        return None

    def commit(self):
        return None

    def refresh(self, _instance):
        return None


class _FakeRepo:
    USER_UPDATE_FIELDS = {
        "name",
        "description",
        "software_version",
    }
    ADMIN_UPDATE_FIELDS = USER_UPDATE_FIELDS | {"max_devices", "enabled", "user_id"}

    def __init__(self, microcontroller: Microcontroller):
        self.microcontroller = microcontroller

    def get_for_user_by_uuid(self, uuid, user_id):
        if uuid == self.microcontroller.uuid and user_id == self.microcontroller.user_id:
            return self.microcontroller
        return None

    def get_by_id(self, microcontroller_id):
        if microcontroller_id == self.microcontroller.id:
            return self.microcontroller
        return None


def _build_microcontroller() -> Microcontroller:
    return Microcontroller(
        id=7,
        uuid=uuid4(),
        user_id=13,
        type=MicrocontrollerType.RASPBERRY_PI_ZERO,
        name="Main controller",
        description="before",
        software_version="1.0.0",
        max_devices=4,
        enabled=True,
        config={
            "uuid": "legacy",
            "device_uuid": "stale-device-id",
            "device_max": 4,
            "active_low": False,
            "devices_config": [],
            "provider": None,
        },
        sensor_capabilities=[
            MicrocontrollerSensorCapability(sensor_type="dht22"),
        ],
    )


def test_update_microcontroller_for_user_updates_sensors_and_config():
    microcontroller = _build_microcontroller()
    repo = _FakeRepo(microcontroller)
    service = MicrocontrollerService(repo_factory=lambda _db: repo)

    updated = service.update_microcontroller_for_user(
        _FakeSession(),
        microcontroller_uuid=microcontroller.uuid,
        user_id=microcontroller.user_id,
        data={"name": "Boiler room"},
        assigned_sensors=["ds18b20"],
    )

    assert updated.name == "Boiler room"
    assert updated.assigned_sensors == ["ds18b20"]
    assert updated.config["available_sensors"] == ["ds18b20"]
    assert updated.config["device_max"] == 4
    assert "device_uuid" not in updated.config


def test_update_microcontroller_for_user_rejects_duplicate_sensors():
    microcontroller = _build_microcontroller()
    repo = _FakeRepo(microcontroller)
    service = MicrocontrollerService(repo_factory=lambda _db: repo)

    with pytest.raises(HTTPException) as exc:
        service.update_microcontroller_for_user(
            _FakeSession(),
            microcontroller_uuid=microcontroller.uuid,
            user_id=microcontroller.user_id,
            data={},
            assigned_sensors=["ds18b20", "ds18b20"],
        )

    assert exc.value.status_code == 422
    assert exc.value.detail == "assigned_sensors must not contain duplicates"
