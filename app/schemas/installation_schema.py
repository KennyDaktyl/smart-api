from typing import List, Optional

from pydantic import BaseModel

from app.schemas.inverter_schema import InverterOut


class InstallationLite(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class InstallationBase(BaseModel):
    name: str
    station_code: str
    station_addr: Optional[str] = None


class InstallationCreate(InstallationBase):
    pass


class InstallationUpdate(BaseModel):
    name: Optional[str] = None
    station_addr: Optional[str] = None


class InstallationOut(InstallationBase):
    id: int
    user_id: int
    inverters: List[InverterOut] = []

    model_config = {"from_attributes": True}
