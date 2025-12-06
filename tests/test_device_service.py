import pytest
from fastapi import HTTPException

from app.constans.device_mode import DeviceMode
from app.constans.events import EventType
from app.repositories.device_repository import DeviceRepository
from app.services.device_service import DeviceService
from tests.factories import (
    create_installation,
    create_inverter,
    create_raspberry,
    create_user,
)
from tests.mocks import FakePublisher


@pytest.fixture()
def fake_publisher():
    return FakePublisher()


@pytest.fixture()
def device_service(fake_publisher):
    return DeviceService(DeviceRepository(), fake_publisher)


def build_device_payload(user, raspberry, *, mode=DeviceMode.MANUAL, number=1):
    return {
        "name": "Test Device",
        "device_number": number,
        "mode": mode,
        "raspberry_id": raspberry.id,
        "user_id": user.id,
    }


def setup_user_with_hardware(db_session):
    user = create_user(db_session, email="rest-user@example.com")
    installation = create_installation(db_session, user)
    inverter = create_inverter(db_session, installation, serial_number="INV-REST-001")
    raspberry = create_raspberry(db_session, user, inverter=inverter, name="RPI")
    return user, inverter, raspberry


@pytest.mark.asyncio
async def test_create_device_publishes_payload_with_inverter_serial(
    db_session, device_service, fake_publisher
):
    user, inverter, raspberry = setup_user_with_hardware(db_session)
    payload = build_device_payload(user, raspberry, number=2)

    created = await device_service.create_device(db_session, payload)

    message = fake_publisher.published[-1]["message"]
    assert message["event_type"] == EventType.DEVICE_CREATED.value
    assert message["payload"]["device_number"] == 2
    assert message["payload"]["inverter_serial"] == inverter.serial_number
    assert created.device_number == 2


@pytest.mark.asyncio
async def test_create_device_agent_negative_ack_raises(db_session, device_service, fake_publisher):
    user, _, raspberry = setup_user_with_hardware(db_session)
    payload = build_device_payload(user, raspberry, number=3)

    fake_publisher.set_ack({"ok": False, "device_id": 0})

    with pytest.raises(Exception, match="negative ACK"):
        await device_service.create_device(db_session, payload)


@pytest.mark.asyncio
async def test_create_device_agent_timeout_raises(db_session, device_service, fake_publisher):
    user, _, raspberry = setup_user_with_hardware(db_session)
    payload = build_device_payload(user, raspberry, number=4)

    fake_publisher.set_exception(TimeoutError("no ack"))

    with pytest.raises(Exception, match="Failed to send device creation event"):
        await device_service.create_device(db_session, payload)


@pytest.mark.asyncio
async def test_update_device_sends_event(db_session, device_service, fake_publisher):
    user, _, raspberry = setup_user_with_hardware(db_session)
    payload = build_device_payload(user, raspberry, number=5)
    device = await device_service.create_device(db_session, payload)

    updated = await device_service.update_device(
        db_session, device.id, user.id, {"mode": DeviceMode.AUTO_POWER}
    )

    message = fake_publisher.published[-1]["message"]
    assert message["event_type"] == EventType.DEVICE_UPDATED.value
    assert updated.mode == DeviceMode.AUTO_POWER


@pytest.mark.asyncio
async def test_update_device_negative_ack_raises_http(db_session, device_service, fake_publisher):
    user, _, raspberry = setup_user_with_hardware(db_session)
    device = await device_service.create_device(db_session, build_device_payload(user, raspberry))

    fake_publisher.set_ack({"ok": False, "device_id": device.id})

    with pytest.raises(HTTPException) as exc:
        await device_service.update_device(
            db_session, device.id, user.id, {"mode": DeviceMode.AUTO_POWER}
        )
    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_update_device_timeout_returns_504(db_session, device_service, fake_publisher):
    user, _, raspberry = setup_user_with_hardware(db_session)
    device = await device_service.create_device(db_session, build_device_payload(user, raspberry))

    fake_publisher.set_exception(TimeoutError("no response"))

    with pytest.raises(HTTPException) as exc:
        await device_service.update_device(
            db_session, device.id, user.id, {"mode": DeviceMode.AUTO_POWER}
        )
    assert exc.value.status_code == 504


@pytest.mark.asyncio
async def test_set_manual_state_updates_db_and_sends_event(
    db_session, device_service, fake_publisher
):
    user, _, raspberry = setup_user_with_hardware(db_session)
    device = await device_service.create_device(db_session, build_device_payload(user, raspberry))

    response = await device_service.set_manual_state(db_session, device.id, user, state=1)

    message = fake_publisher.published[-1]["message"]
    assert message["event_type"] == EventType.DEVICE_COMMAND.value
    assert message["payload"]["is_on"] is True
    assert response["manual_state"] == 1


@pytest.mark.asyncio
async def test_set_manual_state_negative_ack_raises(db_session, device_service, fake_publisher):
    user, _, raspberry = setup_user_with_hardware(db_session)
    device = await device_service.create_device(db_session, build_device_payload(user, raspberry))

    fake_publisher.set_ack({"ok": False, "device_id": device.id})

    with pytest.raises(HTTPException) as exc:
        await device_service.set_manual_state(db_session, device.id, user, state=0)
    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_delete_device_publishes_and_removes(db_session, device_service, fake_publisher):
    user, _, raspberry = setup_user_with_hardware(db_session)
    device = await device_service.create_device(db_session, build_device_payload(user, raspberry))

    result = await device_service.delete_device(db_session, device.id, user)

    assert result is True
    repo = DeviceRepository()
    assert repo.get_by_id(db_session, device.id) is None
    message = fake_publisher.published[-1]["message"]
    assert message["event_type"] == EventType.DEVICE_DELETED.value
