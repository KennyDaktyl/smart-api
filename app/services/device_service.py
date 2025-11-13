# app/services/device_service.py
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.nats_client import NatsClient
from app.models.raspberry import Raspberry
from app.models.user import User
from app.repositories.device_repository import DeviceRepository


class DeviceService:
    def __init__(self, repo: DeviceRepository, nats: NatsClient):
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

    def create_device(self, db: Session, data: dict):
        return self.repo.create(db, data)

    def update_device(self, db: Session, device_id: int, user_id: int, data: dict):
        device = self.repo.update_for_user(db, device_id, user_id, data)
        if not device:
            raise HTTPException(404, "Device not found")
        return device

    async def set_manual_state(self, db: Session, device_id: int, current_user: User, state: int):
        device = self.repo.get_for_user_by_id(db, device_id, current_user.id)
        if not device:
            raise HTTPException(404, "Device not found")

        raspberry: Raspberry = device.raspberry
        if not raspberry or not raspberry.uuid:
            raise HTTPException(400, "Device not assigned to Raspberry")

        serial = raspberry.uuid

        subject = f"raspberry.{serial}.command"
        ack_subject = f"raspberry.{serial}.ack"

        message = {
            "action": "SET_DEVICE_STATE",
            "data": {
                "device_id": device.id,
                "gpio_pin": device.gpio_pin,
                "state": state,
            },
        }

        ack = await self.nats.publish_and_wait_for_ack(
            subject=subject,
            ack_subject=ack_subject,
            message=message,
            match_id=device.id,
            timeout=3.0,
        )

        if not ack.get("ok"):
            raise HTTPException(500, "Raspberry failed to set state")

        updated = self.repo.update_for_user(db, device_id, current_user.id, {"manual_state": state})

        return {"device_id": device.id, "manual_state": state, "ack": ack}
