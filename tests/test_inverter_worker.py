import pytest

from app.repositories.inverter_power_record_repository import InverterPowerRepository
from app.workers import inverter_worker
from tests.factories import (
    create_inverter,
    create_inverter_power_record,
    create_installation,
    create_user,
)
from tests.mocks import FakeHuaweiAdapter, FakeNatsModule


@pytest.fixture()
def fake_nats(monkeypatch):
    module = FakeNatsModule()
    monkeypatch.setattr(inverter_worker, "nats_module", module)
    return module


@pytest.fixture()
def fake_adapter(monkeypatch):
    adapter = FakeHuaweiAdapter()
    monkeypatch.setattr(inverter_worker, "get_adapter_for_user", lambda db, user: adapter)
    return adapter


@pytest.mark.asyncio
async def test_worker_publishes_failed_event_when_power_missing(db_session, fake_adapter, fake_nats):
    user = create_user(db_session, email="missing-power@example.com")
    installation = create_installation(db_session, user)
    inverter = create_inverter(db_session, installation, serial_number="INV-NONE")

    fake_adapter.set_power(inverter.serial_number, None)

    await inverter_worker.fetch_inverter_production_async()

    repo = InverterPowerRepository(db_session)
    latest = repo.get_latest_for_inverter(inverter.id)

    assert latest is not None
    assert latest.active_power is None
    assert fake_nats.client.connected is True
    assert fake_nats.ensure_stream_called is True

    assert len(fake_nats.events.published) == 1
    published = fake_nats.events.published[0]
    assert published["subject"] == (
        f"device_communication.inverter.{inverter.serial_number}.production.update"
    )

    payload = published["event"].payload
    assert payload.status == "failed"
    assert payload.active_power is None
    assert "no 'active_power'" in payload.error_message


@pytest.mark.asyncio
async def test_worker_publishes_update_with_latest_power(db_session, fake_adapter, fake_nats):
    user = create_user(db_session, email="two-kw@example.com")
    installation = create_installation(db_session, user)
    inverter = create_inverter(db_session, installation, serial_number="INV-2KW")

    fake_adapter.set_power(inverter.serial_number, 2000.0)

    await inverter_worker.fetch_inverter_production_async()

    repo = InverterPowerRepository(db_session)
    latest = repo.get_latest_for_inverter(inverter.id)

    assert float(latest.active_power) == 2000.0
    assert len(fake_nats.events.published) == 1

    payload = fake_nats.events.published[0]["event"].payload
    assert payload.status == "updated"
    assert payload.active_power == 2000.0


@pytest.mark.asyncio
async def test_worker_emits_update_when_power_changes(db_session, fake_adapter, fake_nats):
    user = create_user(db_session, email="power-change@example.com")
    installation = create_installation(db_session, user)
    inverter = create_inverter(db_session, installation, serial_number="INV-CHANGE")

    create_inverter_power_record(db_session, inverter, active_power=2000.0)
    fake_adapter.set_power(inverter.serial_number, 5000.0)

    await inverter_worker.fetch_inverter_production_async()

    repo = InverterPowerRepository(db_session)
    latest = repo.get_latest_for_inverter(inverter.id)

    assert float(latest.active_power) == 5000.0
    assert len(fake_nats.events.published) == 1

    payload = fake_nats.events.published[0]["event"].payload
    assert payload.active_power == 5000.0
    assert payload.status == "updated"
