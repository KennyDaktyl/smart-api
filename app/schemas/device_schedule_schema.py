from typing import Optional

from pydantic import BaseModel


class DeviceScheduleBase(BaseModel):
    day_of_week: str
    start_time: str
    end_time: str
    enabled: bool = True


class DeviceScheduleCreate(DeviceScheduleBase):
    device_id: int


class DeviceScheduleUpdate(BaseModel):
    day_of_week: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    enabled: Optional[bool] = None


class DeviceScheduleOut(DeviceScheduleBase):
    id: int
    device_id: int

    class Config:
        from_attributes = True
