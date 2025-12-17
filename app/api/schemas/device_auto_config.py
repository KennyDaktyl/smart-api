from pydantic import ConfigDict, Field

from smart_common.schemas.base import APIModel, ORMModel


class DeviceAutoConfigRequest(APIModel):
    provider_id: int = Field(..., description="Provider that drives AUTO logic", example=5)
    comparison: str = Field(
        ...,
        description="Comparison operator used by the AUTO rule",
        regex=r"^[<>]=?$",
        example=">=",
    )
    threshold_value: float = Field(
        ...,
        description="Threshold value triggering the AUTO decision",
        example=500.0,
    )
    hysteresis_value: float | None = Field(
        None,
        description="Optional hysteresis gap to prevent chattering",
        example=25.0,
    )
    enabled: bool = Field(True, description="Whether AUTO mode is active", example=True)


class DeviceAutoConfigUpdateRequest(APIModel):
    provider_id: int | None = Field(None, description="Updated provider ID")
    comparison: str | None = Field(
        None,
        regex=r"^[<>]=?$",
        description="Updated comparison operator",
        example="<",
    )
    threshold_value: float | None = Field(None, description="Updated threshold value")
    hysteresis_value: float | None = Field(None, description="Updated hysteresis")
    enabled: bool | None = Field(None, description="Toggle AUTO mode")


class DeviceAutoConfigResponse(ORMModel):
    id: int = Field(..., description="AUTO configuration ID", example=7)
    device_id: int = Field(..., description="Target device ID", example=101)
    provider_id: int = Field(..., description="Provider driving the decision", example=5)
    comparison: str = Field(
        ...,
        description="Comparison operator",
        example=">=",
    )
    threshold_value: float = Field(..., description="Threshold", example=500.0)
    hysteresis_value: float | None = Field(None, description="Hysteresis offset", example=15.0)
    enabled: bool = Field(..., description="AUTO mode enabled flag", example=True)

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        schema_extra={
            "example": {
                "id": 7,
                "device_id": 101,
                "provider_id": 5,
                "comparison": ">=",
                "threshold_value": 500.0,
                "hysteresis_value": 25.0,
                "enabled": True,
            }
        },
    )


class DeviceAutoConfigStatusRequest(APIModel):
    enabled: bool = Field(
        ...,
        description="Enable or disable the AUTO configuration",
        example=True,
    )
