from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import ConfigDict, Field

from smart_common.enums.microcontroller import MicrocontrollerType
from smart_common.schemas.base import APIModel, ORMModel


class MicrocontrollerCreateRequest(APIModel):
    name: str = Field(..., description="Display name for the microcontroller", example="Gateway Alpha")
    description: Optional[str] = Field(
        None,
        description="Additional notes or location details",
        example="Installed on rooftop, north side",
    )
    software_version: Optional[str] = Field(
        None,
        description="Firmware version running on the controller",
        example="1.4.2",
    )
    type: MicrocontrollerType = Field(
        MicrocontrollerType.RASPBERRY_PI_ZERO,
        description="Hardware type of the microcontroller",
        example=MicrocontrollerType.RASPBERRY_PI_ZERO.value,
    )
    max_devices: int = Field(
        4,
        gt=0,
        description="Maximum number of devices that can be attached",
        example=4,
    )


class MicrocontrollerUpdateRequest(APIModel):
    name: Optional[str] = Field(None, description="Updated display name", example="Gateway Beta")
    description: Optional[str] = Field(None, description="Updated installation notes")
    software_version: Optional[str] = Field(None, description="Firmware version")
    max_devices: Optional[int] = Field(None, gt=0, description="Updated device capacity")
    enabled: Optional[bool] = Field(None, description="Toggle controller availability")


class MicrocontrollerStatusRequest(APIModel):
    enabled: bool = Field(
        ...,
        description="True to allow communication, false to pause the controller",
        example=True,
    )


class MicrocontrollerResponse(ORMModel):
    id: int = Field(..., description="Internal ID", example=10)
    uuid: UUID = Field(..., description="Public UUID of the controller")
    installation_id: int = Field(..., description="Installation that owns the controller", example=3)
    name: str = Field(..., description="Display name for the controller", example="Gateway Alpha")
    description: Optional[str] = Field(
        None,
        description="Optional notes about the controller",
        example="Mounted in utility room",
    )
    software_version: Optional[str] = Field(
        None,
        description="Firmware version",
        example="1.4.2",
    )
    type: MicrocontrollerType = Field(
        MicrocontrollerType.RASPBERRY_PI_ZERO,
        description="Hardware family",
        example=MicrocontrollerType.RASPBERRY_PI_ZERO.value,
    )
    max_devices: int = Field(..., description="Maximum attached devices", example=4)
    enabled: bool = Field(..., description="Whether controller accepts new commands", example=True)
    created_at: datetime = Field(..., description="Creation timestamp (UTC)")
    updated_at: datetime = Field(..., description="Last update timestamp (UTC)")

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        schema_extra={
            "example": {
                "id": 10,
                "uuid": "9f8d8e42-0aa1-4b7c-8cda-1cb8f7123456",
                "installation_id": 3,
                "name": "Gateway Alpha",
                "description": "Mounted in utility room",
                "software_version": "1.4.2",
                "type": MicrocontrollerType.RASPBERRY_PI_ZERO.value,
                "max_devices": 4,
                "enabled": True,
                "created_at": "2024-01-01T12:00:00Z",
                "updated_at": "2024-01-02T12:00:00Z",
            }
        },
    )
