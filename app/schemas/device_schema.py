from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.constans.device_mode import DeviceMode


class DeviceBase(BaseModel):
    name: str = Field(..., description="Nazwa urządzenia")
    gpio_pin: int = Field(..., description="Numer pinu GPIO")
    mode: DeviceMode = Field(default=DeviceMode.MANUAL, description="Tryb pracy")
    rated_power_w: Optional[float] = Field(None, description="Deklarowana moc urządzenia (W)")
    threshold_w: Optional[float] = None
    hysteresis_w: Optional[float] = 100
    schedule: Optional[Any] = None


class DeviceCreate(DeviceBase):
    raspberry_id: int = Field(
        ..., description="ID Raspberry, do którego przypisane jest urządzenie"
    )
    # user_id nie podawane przez frontend — zostanie przypisane automatycznie


class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    gpio_pin: Optional[int] = None
    mode: Optional[DeviceMode] = None
    rated_power_w: Optional[float] = None
    threshold_w: Optional[float] = None
    hysteresis_w: Optional[float] = None
    schedule: Optional[Any] = None
    is_on: Optional[bool] = None
    raspberry_id: Optional[int] = None
    user_id: Optional[int] = None


class DeviceOut(DeviceBase):
    id: int
    uuid: UUID
    user_id: Optional[int]
    raspberry_id: Optional[int]
    is_on: bool
    last_update: datetime

    class Config:
        from_attributes = True
