from fastapi import APIRouter
from smart_common.enums.sensor import SensorType
from smart_common.enums.unit import PowerUnit

enums_router = APIRouter(
    prefix="/enums",
    tags=["Enums"],
)


@enums_router.get("/units", summary="List available measurement units")
def list_units():
    return [
        {
            "key": unit.name,
            "value": unit.value,
            "label": unit.value,
        }
        for unit in PowerUnit
    ]


@enums_router.get("/sensor-types", summary="List supported sensor types")
def list_sensor_types():
    return [
        {
            "key": sensor.name,
            "value": sensor.value,
            "label": sensor.value.upper(),
        }
        for sensor in SensorType
    ]
