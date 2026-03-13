import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from smart_common.enums.device import DeviceMode
from smart_common.services.device_service import DeviceService


class _FakeDeviceRepo:
    def __init__(self, devices):
        self._devices = devices

    def list_for_scheduler(self, *, scheduler_id: int, user_id: int):
        return list(self._devices)


def test_disable_scheduler_devices_switches_devices_to_manual_and_off():
    devices = [
        SimpleNamespace(id=11),
        SimpleNamespace(id=12),
    ]
    repo = _FakeDeviceRepo(devices)
    service = DeviceService(
        repo_factory=lambda _db: repo,
        microcontroller_repo_factory=lambda _db: None,
        scheduler_repo_factory=lambda _db: None,
    )
    service.update_device = AsyncMock(return_value=None)
    service.set_manual_state = AsyncMock(return_value=(None, True))

    result = asyncio.run(
        service.disable_scheduler_devices(
            db=object(),
            user_id=7,
            scheduler_id=99,
        )
    )

    assert result == devices
    assert service.update_device.await_count == 2
    assert service.set_manual_state.await_count == 2

    first_update = service.update_device.await_args_list[0]
    assert first_update.args[1] == 7
    assert first_update.args[2] == 11
    assert first_update.args[3] == {
        "mode": DeviceMode.MANUAL,
        "scheduler_id": None,
    }

    second_update = service.update_device.await_args_list[1]
    assert second_update.args[2] == 12
    assert second_update.args[3] == {
        "mode": DeviceMode.MANUAL,
        "scheduler_id": None,
    }

    first_manual = service.set_manual_state.await_args_list[0]
    assert first_manual.kwargs["device_id"] == 11
    assert first_manual.kwargs["state"] is False

    second_manual = service.set_manual_state.await_args_list[1]
    assert second_manual.kwargs["device_id"] == 12
    assert second_manual.kwargs["state"] is False
