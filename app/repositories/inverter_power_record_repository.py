from datetime import datetime, timezone
from typing import Optional
import logging

from sqlalchemy.orm import Session

from app.models.inverter_power_record import InverterPowerRecord

logger = logging.getLogger(__name__)


class InverterPowerRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_record(
        self, inverter_id: int, active_power: Optional[float], timestamp: Optional[datetime] = None
    ):
        record = InverterPowerRecord(
            inverter_id=inverter_id,
            active_power=active_power,
            timestamp=timestamp or datetime.now(timezone.utc),
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        logger.info(
            "Inverter power record saved inverter_id=%s active_power=%s timestamp=%s",
            inverter_id,
            active_power,
            record.timestamp.isoformat(),
        )
        return record

    def get_latest_for_inverter(self, inverter_id: int):
        return (
            self.db.query(InverterPowerRecord)
            .filter(InverterPowerRecord.inverter_id == inverter_id)
            .order_by(
                InverterPowerRecord.timestamp.desc(),
                InverterPowerRecord.id.desc(),
            )
            .first()
        )

    def get_recent_for_inverter(self, inverter_id: int, limit: int = 10):
        return (
            self.db.query(InverterPowerRecord)
            .filter(InverterPowerRecord.inverter_id == inverter_id)
            .order_by(
                InverterPowerRecord.timestamp.desc(),
                InverterPowerRecord.id.desc(),
            )
            .limit(limit)
            .all()
        )
