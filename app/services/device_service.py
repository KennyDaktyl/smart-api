# app/services/device_service.py
import logging

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.constans.events import EventType
from app.core.db import transactional_session
from app.events.device_events import DeviceCreatedPayload, DeviceUpdatedPayload
from app.events.event_dispatcher import EventDispatcher
from app.models.device import Device
from app.models.raspberry import Raspberry
from app.models.user import User
from app.nats.publisher import NatsPublisher
from app.repositories.device_repository import DeviceRepository
from app.schemas.device_schema import DeviceOut


class DeviceService:

    def __init__(self, repo: DeviceRepository, nats: NatsPublisher):
        self.repo = repo
        self.events = EventDispatcher(nats)
        self.logger = logging.getLogger(__name__)

    def list_all(self, db: Session):
        self.logger.info("Listing all devices")
        return self.repo.get_all(db)

    def list_for_user(self, db: Session, user_id: int):
        self.logger.info("Listing devices for user_id=%s", user_id)
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
            self.logger.info("Device created id=%s user_id=%s", device.id, device.user_id)

            rpi_uuid = device.raspberry.uuid
            inverter_serial = device.raspberry.inverter.serial_number if device.raspberry.inverter else None

            payload = DeviceCreatedPayload(
                device_id=device.id,
                device_number=device.device_number,
                mode=device.mode.value,
                threshold_kw=device.threshold_kw,
                inverter_serial=inverter_serial,
            )

            try:
                ack = await self.events.publish_event_and_wait_for_ack(
                    subject=f"device_communication.raspberry.{rpi_uuid}.events",
                    ack_subject=f"device_communication.raspberry.{rpi_uuid}.events.ack",
                    event_type=EventType.DEVICE_CREATED,
                    payload=payload,
                    predicate=lambda p: p.get("device_id") == device.id,
                    timeout=10.0,
                )
            except Exception as e:
                raise Exception(f"Failed to send device creation event to agent: {e}")

            if not ack.get("ok", False):
                raise Exception("Agent returned negative ACK")

            self.logger.info("Device creation acknowledged by agent device_id=%s", device.id)
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
        self.logger.info("Device updated id=%s user_id=%s", updated_device.id, updated_device.user_id)

        payload = DeviceUpdatedPayload(
            device_id=updated_device.id,
            mode=updated_device.mode.value,
            threshold_kw=updated_device.threshold_kw,
        )

        subject = f"device_communication.raspberry.{rpi_uuid}.events"
        ack_subject = f"device_communication.raspberry.{rpi_uuid}.events.ack"

        try:
            ack = await self.events.publish_event_and_wait_for_ack(
                subject=subject,
                ack_subject=ack_subject,
                event_type=EventType.DEVICE_UPDATED,
                payload=payload,
                predicate=lambda p: p.get("device_id") == updated_device.id,
                timeout=10.0,
            )
        except Exception as e:
            raise HTTPException(504, f"Raspberry not responding: {str(e)}")

        if not ack.get("ok"):
            raise HTTPException(500, "Raspberry failed to process update")

        self.logger.info("Device update acknowledged by agent device_id=%s", updated_device.id)
        return updated_device

    async def delete_device(self, db: Session, device_id: int, current_user: User):
        device: Device = self.get_device(db, device_id, current_user)

        raspberry: Raspberry = device.raspberry
        rpi_uuid = raspberry.uuid

        subject = f"device_communication.raspberry.{rpi_uuid}.events"
        ack_subject = f"device_communication.raspberry.{rpi_uuid}.events.ack"

        try:
            ack = await self.events.publish_event_and_wait_for_ack(
                subject=subject,
                ack_subject=ack_subject,
                event_type=EventType.DEVICE_DELETED,
                payload={"device_id": device.id},
                predicate=lambda p: p.get("device_id") == device.id,
                timeout=10.0,
            )
        except Exception as e:
            raise HTTPException(504, f"Raspberry not responding: {str(e)}")

        if not ack.get("ok"):
            raise HTTPException(500, "Raspberry failed to delete device")

        self.repo.delete(db, device.id)
        self.logger.info("Device deleted id=%s user_id=%s", device.id, device.user_id)

        return True

    async def set_manual_state(self, db: Session, device_id: int, current_user: User, state: int):
        device = self.repo.get_for_user_by_id(db, device_id, current_user.id)
        if not device:
            raise HTTPException(404, "Device not found")

        raspberry: Raspberry = device.raspberry
        serial = raspberry.uuid
        self.logger.info(
            "Manual state change requested device_id=%s user_id=%s state=%s",
            device.id,
            current_user.id,
            state,
        )

        subject = f"device_communication.raspberry.{serial}.events"
        ack_subject = f"device_communication.raspberry.{serial}.events.ack"

        try:
            ack = await self.events.publish_event_and_wait_for_ack(
                subject=subject,
                ack_subject=ack_subject,
                event_type=EventType.DEVICE_COMMAND,
                payload={"device_id": device.id, "command": "SET_STATE", "is_on": bool(state)},
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
        self.logger.info(
            "Manual state updated device_id=%s user_id=%s state=%s",
            updated_device.id,
            current_user.id,
            state,
        )

        return {"device_id": updated_device.id, "manual_state": state, "ack": ack}
