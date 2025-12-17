from typing import Callable

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from smart_common.models.device import Device
from smart_common.models.device_schedule import DeviceSchedule
from smart_common.repositories.device import DeviceRepository
from smart_common.repositories.device_schedule import DeviceScheduleRepository


class DeviceScheduleService:
    def __init__(
        self,
        schedule_repo_factory: Callable[[Session], DeviceScheduleRepository],
        device_repo_factory: Callable[[Session], DeviceRepository],
    ):
        self._schedule_repo_factory = schedule_repo_factory
        self._device_repo_factory = device_repo_factory

    def _schedule_repo(self, db: Session) -> DeviceScheduleRepository:
        return self._schedule_repo_factory(db)

    def _device_repo(self, db: Session) -> DeviceRepository:
        return self._device_repo_factory(db)

    def _get_device(
        self,
        db: Session,
        user_id: int,
        device_id: int,
        expected_microcontroller_id: int | None = None,
    ) -> Device:
        device = self._device_repo(db).get_for_user_by_id(device_id, user_id)
        if not device:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
        if expected_microcontroller_id is not None and device.microcontroller_id != expected_microcontroller_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found for the requested microcontroller",
            )
        return device

    def list_for_device(
        self, db: Session, user_id: int, device_id: int, microcontroller_id: int
    ) -> list[DeviceSchedule]:
        self._get_device(db, user_id, device_id, expected_microcontroller_id=microcontroller_id)
        return self._schedule_repo(db).list_for_device(device_id)

    def create_schedule(
        self, db: Session, user_id: int, microcontroller_id: int, payload: dict
    ) -> DeviceSchedule:
        self._get_device(
            db,
            user_id,
            payload["device_id"],
            expected_microcontroller_id=microcontroller_id,
        )

        schedule = DeviceSchedule(**payload)
        self._schedule_repo(db).create(schedule)
        db.commit()
        db.refresh(schedule)
        return schedule

    def update_schedule(
        self,
        db: Session,
        user_id: int,
        microcontroller_id: int,
        schedule_id: int,
        payload: dict,
    ) -> DeviceSchedule:
        schedule = self._schedule_repo(db).get_by_id(schedule_id)
        if not schedule:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")

        self._get_device(
            db,
            user_id,
            schedule.device_id,
            expected_microcontroller_id=microcontroller_id,
        )
        for attr, value in payload.items():
            setattr(schedule, attr, value)

        self._schedule_repo(db).update(schedule)
        db.commit()
        db.refresh(schedule)
        return schedule

    def delete_schedule(
        self, db: Session, user_id: int, microcontroller_id: int, schedule_id: int
    ) -> None:
        schedule = self._schedule_repo(db).get_by_id(schedule_id)
        if not schedule:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")

        self._get_device(
            db,
            user_id,
            schedule.device_id,
            expected_microcontroller_id=microcontroller_id,
        )
        self._schedule_repo(db).delete(schedule)
        db.commit()
