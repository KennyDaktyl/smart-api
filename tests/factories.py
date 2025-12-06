import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from app.constans.device_mode import DeviceMode
from app.constans.role import UserRole
from app.core.security import encrypt_password, get_password_hash
from app.models import Device, Installation, Inverter, InverterPowerRecord, Raspberry, User


def create_user(
    db,
    email: str = "user@example.com",
    password: str = "password",
    role: UserRole = UserRole.CLIENT,
    huawei_username: Optional[str] = "huawei@example.com",
    huawei_password: Optional[str] = "huawei-password",
) -> User:
    user = User(
        email=email,
        password_hash=get_password_hash(password),
        role=role,
        huawei_username=huawei_username,
        huawei_password_encrypted=encrypt_password(huawei_password) if huawei_password else None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_installation(
    db,
    user: User,
    name: str = "Test Installation",
    station_code: Optional[str] = None,
    station_addr: Optional[str] = "Test address",
) -> Installation:
    installation = Installation(
        name=name,
        station_code=station_code or f"station-{uuid.uuid4().hex[:8]}",
        station_addr=station_addr,
        user_id=user.id,
    )
    db.add(installation)
    db.commit()
    db.refresh(installation)
    return installation


def create_inverter(
    db,
    installation: Installation,
    serial_number: Optional[str] = None,
    name: str = "Test inverter",
    capacity_kw: Optional[Decimal] = None,
) -> Inverter:
    inverter = Inverter(
        installation_id=installation.id,
        serial_number=serial_number or f"INV-{uuid.uuid4().hex[:8]}",
        name=name,
        capacity_kw=capacity_kw,
    )
    db.add(inverter)
    db.commit()
    db.refresh(inverter)
    return inverter


def create_inverter_power_record(
    db, inverter: Inverter, active_power: Optional[float], timestamp: Optional[datetime] = None
) -> InverterPowerRecord:
    record = InverterPowerRecord(
        inverter_id=inverter.id,
        active_power=active_power,
        timestamp=timestamp or datetime.now(timezone.utc),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def create_raspberry(
    db,
    user: Optional[User],
    inverter: Optional[Inverter] = None,
    name: str = "Raspberry",
    secret_key: str = "secret-key",
) -> Raspberry:
    raspberry = Raspberry(
        user_id=user.id if user else None,
        inverter_id=inverter.id if inverter else None,
        name=name,
        secret_key=secret_key,
    )
    db.add(raspberry)
    db.commit()
    db.refresh(raspberry)
    return raspberry


def create_device(
    db,
    user: User,
    raspberry: Raspberry,
    device_number: int = 1,
    rated_power_kw: Decimal | float | None = Decimal("2.0"),
    mode: DeviceMode = DeviceMode.MANUAL,
    is_on: bool = False,
) -> Device:
    device = Device(
        name=f"Device {device_number}",
        user_id=user.id,
        raspberry_id=raspberry.id,
        device_number=device_number,
        rated_power_kw=rated_power_kw,
        mode=mode,
        is_on=is_on,
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    return device
