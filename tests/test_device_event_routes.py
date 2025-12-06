from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.device_event_routes import router as device_event_router
from app.core.db import get_db
from app.models.device import Device
from tests.factories import (
    create_device,
    create_installation,
    create_inverter,
    create_raspberry,
    create_user,
)


@pytest.fixture()
def api_client(db_session):
    app = FastAPI()
    app.include_router(device_event_router)

    def _get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _get_db
    return TestClient(app)


def create_device_with_hardware(db_session) -> Device:
    user = create_user(db_session, email="device-events@example.com")
    installation = create_installation(db_session, user)
    inverter = create_inverter(db_session, installation, serial_number="INV-DEVICE-1")
    raspberry = create_raspberry(db_session, user, inverter=inverter)
    device = create_device(db_session, user, raspberry, device_number=1, rated_power_kw=0.7)
    return device


def test_post_device_event_off_to_on_and_fetch_summary(api_client, db_session):
    device = create_device_with_hardware(db_session)

    t0 = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(minutes=15)
    date_end = t0 + timedelta(minutes=30)

    # OFF event
    resp_off = api_client.post(
        "/device-events/",
        json={
            "device_id": device.id,
            "pin_state": False,
            "trigger_reason": "BOOT",
            "power_kw": 0.0,
            "timestamp": t0.isoformat(),
        },
    )
    assert resp_off.status_code == 200
    assert resp_off.json()["state"] == "OFF"

    # ON event with inverter power that triggered the change
    resp_on = api_client.post(
        "/device-events/",
        json={
            "device_id": device.id,
            "pin_state": True,
            "trigger_reason": "AUTO_POWER",
            "power_kw": None,
            "timestamp": t1.isoformat(),
        },
    )
    assert resp_on.status_code == 200
    body_on = resp_on.json()
    assert body_on["state"] == "ON"
    assert body_on["power_kw"] is None

    # Fetch range and summary
    resp_get = api_client.get(
        f"/device-events/device/{device.id}",
        params={
            "date_start": t0.isoformat(),
            "date_end": date_end.isoformat(),
        },
    )
    assert resp_get.status_code == 200
    payload = resp_get.json()

    assert payload["rated_power_kw"] == 0.7
    assert payload["total_minutes_on"] == 15
    assert abs(payload["average_power_kw"] - 0.7) < 1e-6
    # 0.7 kW * 0.25 h = 0.175 kWh
    assert abs(payload["energy_kwh"] - 0.175) < 1e-6
    assert payload["events"][0]["state"] in ("ON", "OFF")
    assert any(e["state"] == "ON" for e in payload["events"])
    assert any(e["state"] == "OFF" for e in payload["events"])
