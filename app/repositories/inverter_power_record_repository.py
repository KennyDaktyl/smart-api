from sqlalchemy.orm import Session

from app.models.inverter_power_record import InverterPowerRecord


class InverterPowerRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_record(self, inverter_id: int, active_power: float):
        record = InverterPowerRecord(
            inverter_id=inverter_id,
            active_power=active_power,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_latest_for_inverter(self, inverter_id: int):
        return (
            self.db.query(InverterPowerRecord)
            .filter(InverterPowerRecord.inverter_id == inverter_id)
            .order_by(InverterPowerRecord.timestamp.desc())
            .first()
        )

    def get_recent_for_inverter(self, inverter_id: int, limit: int = 10):
        return (
            self.db.query(InverterPowerRecord)
            .filter(InverterPowerRecord.inverter_id == inverter_id)
            .order_by(InverterPowerRecord.timestamp.desc())
            .limit(limit)
            .all()
        )
