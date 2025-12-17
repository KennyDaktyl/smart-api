from typing import Callable

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from smart_common.models.device import Device
from smart_common.models.device_auto_config import DeviceAutoConfig
from smart_common.models.provider import Provider
from smart_common.repositories.device import DeviceRepository
from smart_common.repositories.device_auto_config import DeviceAutoConfigRepository
from smart_common.repositories.provider import ProviderRepository


class DeviceAutoConfigService:
    def __init__(
        self,
        config_repo_factory: Callable[[Session], DeviceAutoConfigRepository],
        device_repo_factory: Callable[[Session], DeviceRepository],
        provider_repo_factory: Callable[[Session], ProviderRepository],
    ):
        self._config_repo_factory = config_repo_factory
        self._device_repo_factory = device_repo_factory
        self._provider_repo_factory = provider_repo_factory

    def _config_repo(self, db: Session) -> DeviceAutoConfigRepository:
        return self._config_repo_factory(db)

    def _device_repo(self, db: Session) -> DeviceRepository:
        return self._device_repo_factory(db)

    def _provider_repo(self, db: Session) -> ProviderRepository:
        return self._provider_repo_factory(db)

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

    def _get_provider(self, db: Session, provider_id: int) -> Provider:
        provider = self._provider_repo(db).get_by_id(provider_id)
        if not provider:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
        return provider

    def get_config(
        self, db: Session, user_id: int, device_id: int, microcontroller_id: int
    ) -> DeviceAutoConfig | None:
        self._get_device(
            db, user_id, device_id, expected_microcontroller_id=microcontroller_id
        )
        return self._config_repo(db).get_by_device(device_id)

    def create_or_update(
        self,
        db: Session,
        user_id: int,
        device_id: int,
        microcontroller_id: int,
        payload: dict,
    ) -> DeviceAutoConfig:
        device = self._get_device(
            db, user_id, device_id, expected_microcontroller_id=microcontroller_id
        )
        provider = self._get_provider(db, payload["provider_id"])

        if provider.microcontroller_id != device.microcontroller_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provider must belong to the same microcontroller as the device",
            )

        config = self._config_repo(db).get_by_device(device.id)
        if config:
            for attr, value in payload.items():
                setattr(config, attr, value)
        else:
            config = DeviceAutoConfig(device_id=device.id, **payload)
            self._config_repo(db).create(config)

        db.commit()
        db.refresh(config)
        return config

    def set_enabled(
        self, db: Session, user_id: int, device_id: int, microcontroller_id: int, enabled: bool
    ) -> DeviceAutoConfig:
        config = self.get_config(db, user_id, device_id, microcontroller_id)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="AUTO configuration not found"
            )

        config.enabled = enabled
        db.commit()
        db.refresh(config)
        return config
