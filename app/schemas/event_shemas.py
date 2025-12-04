#  app/schemas/event_shemas.py
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel

from app.constans.events import EventType


class BaseEvent(BaseModel):
    event_type: EventType


class DeviceCreatedPayload(BaseModel):
    device_id: int
    device_number: int  # 1..3
    mode: str
    threshold_kw: Optional[float] = None


class DeviceCreatedEvent(BaseEvent):
    payload: DeviceCreatedPayload


class DeviceUpdatedPayload(BaseModel):
    device_id: int
    mode: str
    threshold_kw: Optional[float] = None


class DeviceUpdatedEvent(BaseEvent):
    payload: DeviceUpdatedPayload


class PowerReadingPayload(BaseModel):
    inverter_id: int
    power_kw: float
    device_ids: List[int]


class PowerReadingEvent(BaseEvent):
    payload: PowerReadingPayload


class DeviceCommandPayload(BaseModel):
    device_id: int
    command: str
    is_on: bool


class DeviceCommandEvent(BaseEvent):
    payload: DeviceCommandPayload


class DeviceDeletePayload(BaseModel):
    device_id: int


class DeviceDeletedEvent(BaseEvent):
    payload: DeviceDeletePayload
