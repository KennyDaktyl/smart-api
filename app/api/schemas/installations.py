from typing import Optional

from pydantic import ConfigDict, Field

from smart_common.schemas.base import APIModel, ORMModel


class InstallationBase(APIModel):
    name: str = Field(
        ...,
        description="Friendly name for the installation (home, business, farm).",
        example="North Hill Residence",
    )
    station_code: str = Field(
        ...,
        description="Unique station identifier used for integrations.",
        example="NH-2024",
    )
    station_addr: Optional[str] = Field(
        None,
        description="Physical address of the installation.",
        example="123 Solar Row, Krakow",
    )


class InstallationCreateRequest(InstallationBase):
    pass


class InstallationResponse(InstallationBase, ORMModel):
    id: int = Field(..., description="Unique installation identifier", example=42)

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        schema_extra={
            "example": {
                "id": 42,
                "name": "North Hill Residence",
                "station_code": "NH-2024",
                "station_addr": "123 Solar Row, Krakow",
            }
        },
    )
