from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from datetime import datetime, timezone

from app.constans import UserRole
from app.core.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    huawei_username = Column(String, nullable=True)
    huawei_password_encrypted = Column(String, nullable=True)

    role = Column(Enum(UserRole), nullable=False, default=UserRole.CLIENT)
