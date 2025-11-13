from app.adapters.huawei_adapter import HuaweiAdapter
from app.core.db import SessionLocal
from app.repositories.inverter_repository import InverterRepository


class HuaweiService:
    def __init__(self):
        self.repo = InverterRepository()

    def sync_user_devices(self, user):
        adapter = HuaweiAdapter(user.huawei_username, user.huawei_password_encrypted)
        devices = adapter.get_devices()
        db = SessionLocal()
        for dev in devices:
            existing = (
                db.query(self.repo.model)
                .filter_by(serial_number=dev["esnCode"], user_id=user.id)
                .first()
            )
            if not existing:
                self.repo.create(
                    db,
                    {
                        "user_id": user.id,
                        "serial_number": dev["esnCode"],
                        "name": dev.get("devName"),
                        "model": dev.get("devTypeName"),
                        "capacity_kw": dev.get("nominalPower"),
                    },
                )
        db.close()
