from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.raspberry_schema import RaspberryFullOut


class InstallationLite(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class InverterLite(BaseModel):
    id: int
    name: str | None
    serial_number: str
    installation: InstallationLite | None = None

    model_config = {"from_attributes": True}


class InverterBase(BaseModel):
    name: Optional[str] = Field(None, description="Nazwa inwertera (Huawei devName)")
    serial_number: str = Field(..., description="Numer seryjny inwertera (esnCode)")
    model: Optional[str] = Field(None, description="Model urządzenia (invType / model)")
    capacity_kw: Optional[float] = Field(None, description="Moc nominalna [kW]")
    dev_type_id: Optional[int] = Field(None, description="Typ urządzenia (Huawei devTypeId)")
    latitude: Optional[float] = Field(None, description="Szerokość geograficzna")
    longitude: Optional[float] = Field(None, description="Długość geograficzna")


class InverterCreate(InverterBase):
    installation_id: int


class InverterUpdate(BaseModel):
    name: Optional[str] = None
    model: Optional[str] = None
    capacity_kw: Optional[float] = None
    dev_type_id: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class InverterOut(InverterBase):
    id: int
    installation_id: int
    last_updated: datetime
    raspberries: list[RaspberryFullOut]

    model_config = {"from_attributes": True}
