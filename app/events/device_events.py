# app/events/device_events.py
from typing import List, Optional

from app.constans.events import EventType
from app.schemas.base import APIModel


class BaseEvent(APIModel):
    event_type: EventType


class DeviceCreatedPayload(APIModel):
    device_id: int
    device_number: int  # 1..3
    mode: str
    threshold_kw: Optional[float] = None
    inverter_serial: Optional[str] = None


class DeviceCreatedEvent(BaseEvent):
    payload: DeviceCreatedPayload


class DeviceUpdatedPayload(APIModel):
    device_id: int
    mode: str
    threshold_kw: Optional[float] = None


class DeviceUpdatedEvent(BaseEvent):
    payload: DeviceUpdatedPayload


class PowerReadingPayload(APIModel):
    inverter_id: int
    power_kw: float
    device_ids: List[int]


class PowerReadingEvent(BaseEvent):
    payload: PowerReadingPayload


class DeviceCommandPayload(APIModel):
    device_id: int
    command: str
    is_on: bool


class DeviceCommandEvent(BaseEvent):
    payload: DeviceCommandPayload


class DeviceDeletePayload(APIModel):
    device_id: int


class DeviceDeletedEvent(BaseEvent):
    payload: DeviceDeletePayload
