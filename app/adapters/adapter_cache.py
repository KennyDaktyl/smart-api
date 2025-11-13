# app/adapters/adapter_cache.py
import logging

from sqlalchemy.orm import Session

from app.adapters.huawei_adapter import HuaweiAdapter
from app.core.security import decrypt_password
from app.models import User

logger = logging.getLogger(__name__)

_adapter_cache: dict[str, HuaweiAdapter] = {}


def get_adapter_for_user(db: Session, user: User) -> HuaweiAdapter:
    if not user:
        raise ValueError("User object is required.")

    if not user.huawei_username or not user.huawei_password_encrypted:
        raise ValueError("Huawei credentials not configured for this user.")

    key = user.huawei_username

    adapter = _adapter_cache.get(key)
    if adapter:
        logger.debug(f"Using cached HuaweiAdapter for {key}")
        return adapter

    try:
        huawei_password = decrypt_password(user.huawei_password_encrypted)
    except Exception as e:
        logger.exception("Failed to decrypt Huawei password")
        raise ValueError(f"Failed to decrypt Huawei password: {e}")

    adapter = HuaweiAdapter(user.huawei_username, huawei_password)
    _adapter_cache[key] = adapter

    logger.info(f"Created new HuaweiAdapter for {key}")
    return adapter


def clear_adapter_for_user(username: str):
    if username in _adapter_cache:
        del _adapter_cache[username]
        logger.info(f"Cleared HuaweiAdapter cache for {username}")
