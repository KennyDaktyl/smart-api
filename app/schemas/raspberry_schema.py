from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# ====== BASE ======
class RaspberryBase(BaseModel):
    name: str
    description: Optional[str] = None
    firmware_version: Optional[str] = None
    system_info: Optional[Any] = None
    max_devices: int = 1
    gpio_pins: List[int] = []


# ====== CREATE ======
class RaspberryCreate(RaspberryBase):
    user_id: Optional[int] = None
    inverter_id: Optional[int] = None


# ====== UPDATE ======
class RaspberryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    firmware_version: Optional[str] = None
    system_info: Optional[Any] = None
    max_devices: Optional[int] = None
    gpio_pins: Optional[List[int]] = None
    inverter_id: Optional[int] = None
    user_id: Optional[int] = None
    is_online: Optional[bool] = None


# ====== OUTPUT ======
class RaspberryOut(RaspberryBase):
    uuid: UUID
    id: int
    user_id: Optional[int]
    inverter_id: Optional[int]
    is_online: bool
    last_seen: datetime

    model_config = ConfigDict(from_attributes=True)


# ====== OUTPUT ======
class RaspberryCreateOut(RaspberryBase):
    uuid: UUID
    id: int
    secret_plain: str
    user_id: Optional[int]
    inverter_id: Optional[int]
    is_online: bool
    last_seen: datetime

    model_config = ConfigDict(from_attributes=True)
