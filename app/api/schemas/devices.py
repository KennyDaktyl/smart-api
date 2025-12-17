from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import ConfigDict, Field

from smart_common.enums.device import DeviceMode
from smart_common.schemas.base import APIModel, ORMModel


class DeviceCreateRequest(APIModel):
    name: str = Field(..., description="Friendly device name", example="Living Room Heater")
    device_number: int = Field(..., ge=0, description="GPIO pin number", example=3)
    mode: DeviceMode = Field(
        DeviceMode.MANUAL,
        description="Default operation mode",
        example=DeviceMode.MANUAL.value,
    )
    provider_id: Optional[int] = Field(
        None,
        description="Optional provider that supplies AUTO decision data",
        example=12,
    )
    rated_power_w: Optional[float] = Field(
        None,
        gt=0,
        description="Declared device power in watts",
        example=1200.0,
    )


class DeviceUpdateRequest(APIModel):
    name: Optional[str] = Field(None, description="Updated friendly name")
    device_number: Optional[int] = Field(None, ge=0, description="Updated GPIO pin")
    mode: Optional[DeviceMode] = Field(None, description="Updated operation mode")
    provider_id: Optional[int] = Field(None, description="Provider used for AUTO decisions")
    rated_power_w: Optional[float] = Field(None, gt=0, description="Updated power rating")
    manual_state: Optional[bool] = Field(None, description="Manual override state")


class DeviceResponse(ORMModel):
    id: int = Field(..., description="Device ID", example=101)
    uuid: UUID = Field(..., description="Device UUID")
    microcontroller_id: int = Field(..., description="Owning microcontroller ID", example=12)
    provider_id: Optional[int] = Field(None, description="Linked provider ID", example=5)
    name: str = Field(..., description="Friendly name", example="Living Room Heater")
    device_number: int = Field(..., description="GPIO pin number", example=3)
    mode: DeviceMode = Field(..., description="Device mode", example=DeviceMode.MANUAL.value)
    rated_power_w: Optional[float] = Field(
        None,
        description="Rated power in watts",
        example=1200.0,
    )
    manual_state: Optional[bool] = Field(
        None,
        description="Manual override state if set",
        example=False,
    )
    last_state_change_at: Optional[datetime] = Field(
        None,
        description="Timestamp of the last manual state change",
        example="2024-01-02T12:00:00Z",
    )
    created_at: datetime = Field(..., description="Creation timestamp (UTC)")
    updated_at: datetime = Field(..., description="Last update timestamp (UTC)")

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        schema_extra={
            "example": {
                "id": 101,
                "uuid": "1b4e28ba-2fa1-11d2-883f-0016d3cca427",
                "microcontroller_id": 12,
                "provider_id": 5,
                "name": "Living Room Heater",
                "device_number": 3,
                "mode": DeviceMode.MANUAL.value,
                "rated_power_w": 1200.0,
                "manual_state": False,
                "last_state_change_at": "2024-01-02T12:00:00Z",
                "created_at": "2024-01-01T10:00:00Z",
                "updated_at": "2024-01-02T10:30:00Z",
            }
        },
    )
