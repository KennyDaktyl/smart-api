from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import smart_common.services.auth_service as auth_service_module
from smart_common.schemas.user_schema import UserCreate
from smart_common.services.auth_service import AuthService


class DummyRepo:
    model = SimpleNamespace
    session = SimpleNamespace(
        add=lambda *args, **kwargs: None,
        flush=lambda *args, **kwargs: None,
        commit=lambda *args, **kwargs: None,
        rollback=lambda *args, **kwargs: None,
    )

    def __init__(self, user=None):
        self._user = user
        self.queried_email = None

    def get_by_email(self, email: str):
        self.queried_email = email
        return self._user


def test_register_rejects_invalid_email_when_schema_is_bypassed():
    service = AuthService(DummyRepo())
    payload = SimpleNamespace(email="not-an-email", password="VeryStrong123!")

    with pytest.raises(HTTPException) as exc:
        service.register(payload)  # type: ignore[arg-type]

    assert exc.value.status_code == 422
    assert exc.value.detail == "Invalid email address format"


def test_register_returns_503_when_activation_email_queue_fails(monkeypatch):
    user = SimpleNamespace(id=1, email="inactive@example.com", is_active=False)
    service = AuthService(DummyRepo(user=user))

    monkeypatch.setattr(
        auth_service_module, "create_action_token", lambda *args, **kwargs: "token"
    )
    monkeypatch.setattr(
        auth_service_module.send_confirmation_email_task,
        "delay",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("queue down")),
    )

    with pytest.raises(HTTPException) as exc:
        service.register(
            UserCreate(email="inactive@example.com", password="VeryStrong123!")
        )

    assert exc.value.status_code == 503
    assert (
        exc.value.detail == "Could not send activation email. Please try again later."
    )


def test_password_reset_does_not_raise_when_email_queue_fails(monkeypatch):
    user = SimpleNamespace(id=2, email="active@example.com", is_active=True)
    service = AuthService(DummyRepo(user=user))

    monkeypatch.setattr(
        auth_service_module, "create_action_token", lambda *args, **kwargs: "token"
    )
    monkeypatch.setattr(
        auth_service_module.send_password_reset_email_task,
        "delay",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("queue down")),
    )

    assert service.request_password_reset("active@example.com") is None
