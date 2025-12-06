import base64
import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure required settings exist before app.core.config.Settings is instantiated
DEFAULT_FERNET_KEY = base64.urlsafe_b64encode(b"0" * 32).decode()
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_NAME", "test_db")
os.environ.setdefault("POSTGRES_USER", "test_user")
os.environ.setdefault("POSTGRES_PASSWORD", "test_password")
os.environ.setdefault("FERNET_KEY", DEFAULT_FERNET_KEY)
os.environ.setdefault("JWT_SECRET", "test-jwt-secret")
os.environ.setdefault("HUAWEI_API_URL", "https://example.com")
os.environ.setdefault("NATS_URL", "nats://localhost:4222")

from app.core.db import Base  # noqa: E402
import app.models  # noqa: F401, E402


@pytest.fixture(scope="session")
def engine():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture()
def db_session(engine, monkeypatch):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    # Replace globally imported SessionLocal so workers use the SQLite session
    monkeypatch.setattr("app.core.db.SessionLocal", session_factory)
    monkeypatch.setattr("app.workers.inverter_worker.SessionLocal", session_factory)

    session = session_factory()
    try:
        yield session
    finally:
        session.close()
