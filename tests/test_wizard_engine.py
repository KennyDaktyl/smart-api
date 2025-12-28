from pydantic import ValidationError

from smart_common.enums.unit import PowerUnit
from smart_common.providers.definitions.base import ProviderDefinition
from smart_common.providers.enums import ProviderKind, ProviderType, ProviderVendor
from smart_common.providers.provider_config.huawei.final import HuaweiProviderConfig
from smart_common.providers.services.wizard_service import WizardService
from smart_common.providers.wizard.base import ProviderWizard, WizardStep, WizardStepResult
from smart_common.providers.wizard.exceptions import WizardResultError
from smart_common.providers.wizard.session import WizardSessionStore
from smart_common.schemas.base import APIModel


class AuthPayload(APIModel):
    username: str
    password: str


class DevicePayload(APIModel):
    station_code: str
    device_id: str


class FinalOnlyPayload(APIModel):
    value: str


class AuthStep(WizardStep):
    name = "auth"
    schema = AuthPayload

    def process(self, payload: AuthPayload, session_data):
        return WizardStepResult(
            next_step="device",
            session_updates={"credentials": {"username": payload.username}},
        )


class DeviceStep(WizardStep):
    name = "device"
    schema = DevicePayload

    def process(self, payload: DevicePayload, session_data):
        final_config = {
            "station_code": payload.station_code,
            "device_id": payload.device_id,
            "max_power_kw": 50.0,
            "min_power_kw": 0.0,
        }
        return WizardStepResult(
            is_complete=True,
            final_config=final_config,
            session_updates={"device_id": payload.device_id},
        )


class BadFinalStep(WizardStep):
    name = "bad-final"
    schema = FinalOnlyPayload

    def process(self, payload: FinalOnlyPayload, session_data):
        return WizardStepResult(next_step="next", is_complete=True)


class TestWizard(ProviderWizard):
    vendor = ProviderVendor.HUAWEI

    def __init__(self):
        super().__init__(steps=[AuthStep(), DeviceStep(), BadFinalStep()])


DEFINITIONS = {
    ProviderVendor.HUAWEI: ProviderDefinition(
        vendor=ProviderVendor.HUAWEI,
        label="Test Huawei",
        provider_type=ProviderType.API,
        kind=ProviderKind.POWER,
        default_unit=PowerUnit.KILOWATT,
        requires_wizard=True,
        config_schema=HuaweiProviderConfig,
        wizard_cls=TestWizard,
    )
}


def _create_service():
    return WizardService(definitions=DEFINITIONS, session_store=WizardSessionStore())


def test_wizard_service_validates_final_config_flow():
    service = _create_service()
    auth_result = service.run_step(
        ProviderVendor.HUAWEI,
        "auth",
        payload={"username": "u", "password": "p"},
    )

    device_result = service.run_step(
        ProviderVendor.HUAWEI,
        "device",
        payload={"device_id": "dev", "station_code": "st"},
        context=auth_result["context"],
    )

    assert device_result["is_complete"] is True
    assert device_result["final_config"]["station_code"] == "st"


def test_wizard_service_detects_final_config_schema_errors():
    service = _create_service()
    auth_result = service.run_step(
        ProviderVendor.HUAWEI,
        "auth",
        payload={"username": "u", "password": "p"},
    )

    try:
        service.run_step(
            ProviderVendor.HUAWEI,
            "device",
            payload={"device_id": "dev"},
            context=auth_result["context"],
        )
    except ValidationError:
        return
    raise AssertionError("Expected ValidationError for missing station_code")


def test_wizard_service_detects_result_inconsistencies():
    service = _create_service()

    auth_result = service.run_step(
        ProviderVendor.HUAWEI,
        "auth",
        payload={"username": "u", "password": "p"},
    )

    try:
        service.run_step(
            ProviderVendor.HUAWEI,
            "bad-final",
            payload={"value": "x"},
            context=auth_result["context"],
        )
    except WizardResultError:
        return
    raise AssertionError("Expected WizardResultError while reporting completion with next_step")
