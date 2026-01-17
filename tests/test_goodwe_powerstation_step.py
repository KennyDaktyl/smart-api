from pydantic import ValidationError

from smart_common.providers.schemas.wizard.goodwe import GoodWePowerStationStep


def test_powerstation_step_accepts_selection_list():
    payload = {"powerstation_id": [{"value": "ps-123", "label": "ps-123"}]}
    validated = GoodWePowerStationStep.model_validate(payload)
    assert validated.powerstation_id == "ps-123"


def test_powerstation_step_accepts_selection_dict():
    payload = {"powerstation_id": {"value": "ps-456", "label": "ps-456"}}
    validated = GoodWePowerStationStep.model_validate(payload)
    assert validated.powerstation_id == "ps-456"


def test_powerstation_step_rejects_unparseable_value():
    try:
        GoodWePowerStationStep.model_validate({"powerstation_id": []})
    except ValidationError:
        return
    raise AssertionError("Expected ValidationError for empty selection list")
