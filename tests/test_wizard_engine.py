from pydantic import ValidationError

from smart_common.providers.enums import ProviderVendor
from smart_common.providers.wizard.engine import WizardEngine
from smart_common.providers.wizard.exceptions import WizardResultError
from smart_common.providers.wizard.steps import WizardStep
from smart_common.providers.wizard.store import WizardSessionStore
from smart_common.schemas.base import APIModel
from smart_common.providers.provider_config.huawei import HuaweiProviderConfig


class AuthPayload(APIModel):
    username: str
    password: str


class DevicePayload(APIModel):
    device_id: str
    station_code: str


class FinalOnlyPayload(APIModel):
    value: str


def _auth_handler(payload: AuthPayload, session_data: dict):
    return {
        "next_step": "device",
        "session_updates": {
            "credentials": {"username": payload.username, "password": payload.password},
        },
    }


def _device_handler(payload: DevicePayload, session_data: dict):
    credentials = session_data.get("credentials", {})
    return {
        "next_step": None,
        "is_complete": True,
        "final_config": {
            "username": credentials.get("username"),
            "password": credentials.get("password"),
            "station_code": payload.station_code,
            "device_id": payload.device_id,
        },
    }


def _bad_final_handler(payload: FinalOnlyPayload, session_data: dict):
    return {"next_step": "next", "is_complete": True}


TEST_WIZARD = {
    ProviderVendor.HUAWEI: {
        "wizard": {
            "auth": WizardStep(schema=AuthPayload, handler=_auth_handler),
            "device": WizardStep(schema=DevicePayload, handler=_device_handler),
            "bad-final": WizardStep(schema=FinalOnlyPayload, handler=_bad_final_handler),
        },
        "config_schema": HuaweiProviderConfig,
    }
}


def test_wizard_engine_validates_final_config_flow():
    engine = WizardEngine(TEST_WIZARD, session_store=WizardSessionStore())
    auth_result = engine.run_step(
        ProviderVendor.HUAWEI,
        "auth",
        payload={"username": "u", "password": "p"},
    )

    device_result = engine.run_step(
        ProviderVendor.HUAWEI,
        "device",
        payload={"device_id": "dev", "station_code": "st"},
        context=auth_result["context"],
    )

    assert device_result["is_complete"] is True
    assert device_result["final_config"]["station_code"] == "st"


def test_wizard_engine_detects_final_config_schema_errors():
    engine = WizardEngine(TEST_WIZARD, session_store=WizardSessionStore())
    auth_result = engine.run_step(
        ProviderVendor.HUAWEI,
        "auth",
        payload={"username": "u", "password": "p"},
    )

    try:
        engine.run_step(
            ProviderVendor.HUAWEI,
            "device",
            payload={"device_id": "dev"},
            context=auth_result["context"],
        )
    except ValidationError:
        return
    raise AssertionError("Expected ValidationError for missing station_code")


def test_wizard_engine_detects_result_inconsistencies():
    engine = WizardEngine(TEST_WIZARD, session_store=WizardSessionStore())

    try:
        engine.run_step(
            ProviderVendor.HUAWEI,
            "bad-final",
            payload={"value": "x"},
        )
    except WizardResultError:
        return
    raise AssertionError("Expected WizardResultError while reporting completion with next_step")
