# app/services/device_service.py
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.constans.events import EventType
from app.core.db import transactional_session
from app.models.device import Device
from app.models.raspberry import Raspberry
from app.models.user import User
from app.nats.publisher import NatsPublisher
from app.repositories.device_repository import DeviceRepository
from app.schemas.device_schema import DeviceOut
from app.schemas.event_shemas import (DeviceCreatedEvent, DeviceCreatedPayload, DeviceUpdatedEvent,
                                      DeviceUpdatedPayload)


class DeviceService:

    def __init__(self, repo: DeviceRepository, nats: NatsPublisher):
        self.repo = repo
        self.nats = nats

    def list_all(self, db: Session):
        return self.repo.get_all(db)

    def list_for_user(self, db: Session, user_id: int):
        return self.repo.get_for_user(db, user_id)

    def get_device(self, db: Session, device_id: int, current_user: User):
        device = self.repo.get_for_user_by_id(db, device_id, current_user.id)

        if not device and current_user.role == "ADMIN":
            device = self.repo.get_by_id(db, device_id)

        if not device:
            raise HTTPException(404, "Device not found")

        if current_user.role != "ADMIN" and device.user_id != current_user.id:
            raise HTTPException(403, "Access denied")

        return device

    async def create_device(self, db: Session, data: dict):
        async with transactional_session(db):

            device: Device = self.repo.create(db, data)

            rpi_uuid = device.raspberry.uuid

            payload = DeviceCreatedPayload(
                device_id=device.id,
                device_number=device.device_number,
                mode=device.mode.value,
                threshold_kw=device.threshold_kw,
            )

            event = DeviceCreatedEvent(event_type=EventType.DEVICE_CREATED, payload=payload)
            try:
                ack = await self.nats.publish_and_wait_for_ack(
                    subject=f"device_communication.raspberry.{rpi_uuid}.events",
                    ack_subject=f"device_communication.raspberry.{rpi_uuid}.events.ack",
                    message=event.model_dump(),
                    predicate=lambda p: p.get("device_id") == device.id,
                    timeout=10.0,
                )
            except Exception as e:
                raise Exception(f"Failed to send device creation event to agent: {e}")

            if not ack.get("ok", False):
                raise Exception("Agent returned negative ACK")

            return DeviceOut.model_validate(device)

    async def update_device(self, db: Session, device_id: int, user_id: int, data: dict):
        device = self.repo.get_for_user_by_id(db, device_id, user_id)
        if not device:
            raise HTTPException(404, "Device not found")

        raspberry = device.raspberry
        rpi_uuid = raspberry.uuid

        updated_device = self.repo.update_for_user(db, device_id, user_id, data)
        if not updated_device:
            raise HTTPException(404, "Device not found after update")

        payload = DeviceUpdatedPayload(
            device_id=updated_device.id,
            mode=updated_device.mode.value,
            threshold_kw=updated_device.threshold_kw,
        )

        event = DeviceUpdatedEvent(event_type=EventType.DEVICE_UPDATED, payload=payload)

        subject = f"device_communication.raspberry.{rpi_uuid}.events"
        ack_subject = f"device_communication.raspberry.{rpi_uuid}.events.ack"

        try:
            ack = await self.nats.publish_and_wait_for_ack(
                subject=subject,
                ack_subject=ack_subject,
                message=event.model_dump(),
                predicate=lambda p: p.get("device_id") == updated_device.id,
                timeout=10.0,
            )
        except Exception as e:
            raise HTTPException(504, f"Raspberry not responding: {str(e)}")

        if not ack.get("ok"):
            raise HTTPException(500, "Raspberry failed to process update")

        return updated_device

    async def delete_device(self, db: Session, device_id: int, current_user: User):
        device: Device = self.get_device(db, device_id, current_user)

        raspberry: Raspberry = device.raspberry
        rpi_uuid = raspberry.uuid

        subject = f"device_communication.raspberry.{rpi_uuid}.events"
        ack_subject = f"device_communication.raspberry.{rpi_uuid}.events.ack"

        message = {"event_type": EventType.DEVICE_DELETED, "payload": {"device_id": device.id}}

        try:
            ack = await self.nats.publish_and_wait_for_ack(
                subject=subject,
                ack_subject=ack_subject,
                message=message,
                predicate=lambda p: p.get("device_id") == device.id,
                timeout=10.0,
            )
        except Exception as e:
            raise HTTPException(504, f"Raspberry not responding: {str(e)}")

        if not ack.get("ok"):
            raise HTTPException(500, "Raspberry failed to delete device")

        self.repo.delete(db, device.id)

        return True

    async def set_manual_state(self, db: Session, device_id: int, current_user: User, state: int):
        device = self.repo.get_for_user_by_id(db, device_id, current_user.id)
        if not device:
            raise HTTPException(404, "Device not found")

        raspberry: Raspberry = device.raspberry
        serial = raspberry.uuid

        subject = f"device_communication.raspberry.{serial}.events"
        ack_subject = f"device_communication.raspberry.{serial}.events.ack"

        message = {
            "event_type": "DEVICE_COMMAND",
            "payload": {"device_id": device.id, "command": "SET_STATE", "is_on": bool(state)},
        }

        try:
            ack = await self.nats.publish_and_wait_for_ack(
                subject=subject,
                ack_subject=ack_subject,
                message=message,
                predicate=lambda p: p.get("device_id") == device.id,
                timeout=4.0,
            )
        except Exception as e:
            raise HTTPException(status_code=504, detail=str(e))

        if not ack.get("ok"):
            raise HTTPException(500, "Raspberry failed to set state")

        updated_device = self.repo.update_for_user(
            db, device_id, current_user.id, {"manual_state": state}
        )

        return {"device_id": updated_device.id, "manual_state": state, "ack": ack}
