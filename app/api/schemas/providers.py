from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import ConfigDict, Field

from smart_common.enums.provider import ProviderKind, ProviderType, ProviderVendor
from smart_common.enums.unit import PowerUnit
from smart_common.schemas.base import APIModel, ORMModel


class ProviderCreateRequest(APIModel):
    name: str = Field(..., description="Friendly provider name", example="Huawei API")
    provider_type: ProviderType = Field(
        ...,
        description="Source category of the provider",
        example=ProviderType.API.value,
    )
    kind: ProviderKind = Field(
        ...,
        description="Domain of measurements supplied by the provider",
        example=ProviderKind.POWER.value,
    )
    vendor: ProviderVendor | None = Field(
        None,
        description="Optional vendor identifier for the provider",
        example=ProviderVendor.HUAWEI.value,
    )
    unit: PowerUnit | None = Field(
        None,
        description="Unit used by the provider for measurements",
        example=PowerUnit.KILOWATT.value,
    )
    min_value: float = Field(..., description="Minimum value expected from provider", example=0.0)
    max_value: float = Field(..., description="Maximum value expected from provider", example=10.0)
    polling_interval_sec: int = Field(
        ...,
        gt=0,
        description="Polling interval in seconds",
        example=60,
    )
    enabled: bool = Field(
        True,
        description="Whether the provider actively polls for data",
        example=True,
    )
    config: Dict[str, Any] = Field(
        ...,
        description="Provider-specific configuration payload",
        example={"api_key": "my-api-key", "endpoint": "https://api.example.com"},
    )


class ProviderUpdateRequest(APIModel):
    name: Optional[str] = Field(None, description="Updated provider name")
    provider_type: Optional[ProviderType] = Field(None, description="Updated provider type")
    kind: Optional[ProviderKind] = Field(None, description="Updated provider kind")
    vendor: Optional[ProviderVendor] = Field(None, description="Updated vendor identifier")
    unit: Optional[PowerUnit] = Field(None, description="Updated measurement unit")
    min_value: Optional[float] = Field(None, description="Updated minimum expectation")
    max_value: Optional[float] = Field(None, description="Updated maximum expectation")
    polling_interval_sec: Optional[int] = Field(None, gt=0, description="Updated polling interval")
    enabled: Optional[bool] = Field(None, description="Toggle provider availability")
    config: Optional[Dict[str, Any]] = Field(None, description="Updated provider configuration")


class ProviderResponse(ORMModel):
    id: int = Field(..., description="Provider record ID", example=5)
    uuid: str = Field(..., description="Public UUID of the provider")
    microcontroller_id: int = Field(..., description="Parent microcontroller ID", example=12)
    name: str = Field(..., description="Friendly name", example="Huawei API Power")
    provider_type: ProviderType = Field(
        ...,
        description="Provider source type",
        example=ProviderType.API.value,
    )
    kind: ProviderKind = Field(
        ...,
        description="Sensor category",
        example=ProviderKind.POWER.value,
    )
    vendor: Optional[ProviderVendor] = Field(
        None,
        description="Vendor name",
        example=ProviderVendor.HUAWEI.value,
    )
    model: Optional[str] = Field(None, description="Hardware model")
    unit: Optional[PowerUnit] = Field(
        None,
        description="Measurement unit",
        example=PowerUnit.KILOWATT.value,
    )
    min_value: float = Field(..., description="Minimum value", example=0.0)
    max_value: float = Field(..., description="Maximum value", example=10.0)
    last_value: Optional[float] = Field(None, description="Last observed value")
    last_measurement_at: Optional[datetime] = Field(
        None,
        description="Timestamp of the last measurement",
        example="2024-01-02T12:00:00Z",
    )
    polling_interval_sec: Optional[int] = Field(
        None,
        description="Polling frequency in seconds",
        example=60,
    )
    enabled: bool = Field(..., description="Whether provider is emitting data", example=True)
    config: Dict[str, Any] = Field(..., description="Current configuration for the provider")
    created_at: datetime = Field(..., description="Creation timestamp (UTC)")
    updated_at: datetime = Field(..., description="Last update timestamp (UTC)")

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        schema_extra={
            "example": {
                "id": 5,
                "uuid": "4d7c0f01-2224-4c04-a402-123456789abc",
                "microcontroller_id": 12,
                "name": "Huawei API Power",
                "provider_type": ProviderType.API.value,
                "kind": ProviderKind.POWER.value,
                "vendor": ProviderVendor.HUAWEI.value,
                "model": "SUN2000",
                "unit": PowerUnit.KILOWATT.value,
                "min_value": 0.0,
                "max_value": 10.0,
                "last_value": 4.2,
                "last_measurement_at": "2024-01-02T12:00:00Z",
                "polling_interval_sec": 60,
                "enabled": True,
                "config": {"api_key": "abcd"},
                "created_at": "2024-01-01T10:00:00Z",
                "updated_at": "2024-01-02T10:30:00Z",
            }
        },
    )


class ProviderStatusRequest(APIModel):
    enabled: bool = Field(
        ...,
        description="Enable or disable the provider",
        example=True,
    )
