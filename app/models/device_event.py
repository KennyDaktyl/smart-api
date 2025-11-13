from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String

from app.core.db import Base


class DeviceEvent(Base):
    __tablename__ = "device_events"

    id = Column(Integer, primary_key=True)
    event_name = Column(String, nullable=False)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"))
    state = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.now(timezone.utc))

    active_power = Column(Numeric)

    def __repr__(self):
        return f"<DeviceEvent(event_name={self.event_name}, device_id={self.device_id}, state={self.state}, timestamp={self.timestamp})>"
