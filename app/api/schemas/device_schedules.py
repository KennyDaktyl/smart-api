from pydantic import ConfigDict, Field

from smart_common.schemas.base import APIModel, ORMModel


class DeviceScheduleCreateRequest(APIModel):
    device_id: int = Field(..., description="Device receiving the schedule", example=101)
    day_of_week: int = Field(
        ...,
        ge=0,
        le=6,
        description="Day index (0=Monday, 6=Sunday)",
        example=0,
    )
    start_time: str = Field(
        ...,
        regex=r"^\d{2}:\d{2}$",
        description="Start time in HH:MM",
        example="07:00",
    )
    end_time: str = Field(
        ...,
        regex=r"^\d{2}:\d{2}$",
        description="End time in HH:MM",
        example="18:00",
    )
    enabled: bool = Field(True, description="Whether the schedule is active", example=True)


class DeviceScheduleUpdateRequest(APIModel):
    day_of_week: int | None = Field(None, ge=0, le=6, description="Updated day index")
    start_time: str | None = Field(None, regex=r"^\d{2}:\d{2}$", description="Updated start time")
    end_time: str | None = Field(None, regex=r"^\d{2}:\d{2}$", description="Updated end time")
    enabled: bool | None = Field(None, description="Updated enabled flag")


class DeviceScheduleResponse(ORMModel):
    id: int = Field(..., description="Schedule ID", example=12)
    device_id: int = Field(..., description="Device covered by the schedule", example=101)
    day_of_week: int = Field(..., description="Day index (0=Mon)", example=0)
    start_time: str = Field(..., description="Start time (HH:MM)", example="07:00")
    end_time: str = Field(..., description="End time (HH:MM)", example="18:00")
    enabled: bool = Field(..., description="Schedule is active", example=True)

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        schema_extra={
            "example": {
                "id": 12,
                "device_id": 101,
                "day_of_week": 0,
                "start_time": "07:00",
                "end_time": "18:00",
                "enabled": True,
            }
        },
    )
