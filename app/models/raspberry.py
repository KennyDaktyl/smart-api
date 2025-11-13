import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.db import Base


class Raspberry(Base):
    __tablename__ = "raspberries"

    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, index=True)
    secret_key = Column(String, nullable=False)

    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    firmware_version = Column(String, nullable=True)
    system_info = Column(JSON, nullable=True)

    max_devices = Column(Integer, default=1)
    gpio_pins = Column(JSON, default=list)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    inverter_id = Column(Integer, ForeignKey("inverters.id", ondelete="SET NULL"), nullable=True)

    user = relationship("User", back_populates="raspberries")
    inverter = relationship("Inverter", back_populates="raspberries")

    is_online = Column(Boolean, default=False)
    last_seen = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))

    devices = relationship("Device", back_populates="raspberry", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Raspberry id={self.id} name={self.name} identifier={self.identifier}>"
