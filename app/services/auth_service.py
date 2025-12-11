# app/services/auth_service.py

from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.constans.role import UserRole
from app.core.config import settings
from app.core.email_client import send_email
from app.core.security import (
    create_action_token,
    create_access_token,
    create_refresh_token,
    decode_action_token,
    get_password_hash,
    verify_password,
)
from app.repositories.user_repository import UserRepository
from app.schemas.user_schema import UserCreate, UserLogin

CONFIRMATION_TOKEN_EXPIRATION = timedelta(hours=24)
PASSWORD_RESET_TOKEN_EXPIRATION = timedelta(hours=2)


class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def register(self, db: Session, user_in: UserCreate):
        existing = self.user_repo.get_by_email(db, user_in.email)
        if existing:
            raise HTTPException(status_code=400, detail="User with this email already exists")

        user_data = {
            "email": user_in.email,
            "password_hash": get_password_hash(user_in.password),
            "role": UserRole.CLIENT,
            "is_active": False,
        }

        user = self.user_repo.create(db, user_data)
        self._send_confirmation_email(user)
        return user

    def login(self, db: Session, user_in: UserLogin):
        user = self.user_repo.get_by_email(db, user_in.email)
        if not user or not verify_password(user_in.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        if not user.is_active:
            raise HTTPException(status_code=401, detail="Email not confirmed")

        access_token = create_access_token(
            {
                "sub": str(user.id),
                "role": user.role,
            }
        )
        refresh_token = create_refresh_token({"sub": str(user.id)})

        return access_token, refresh_token

    def refresh(self, payload: dict):
        new_access = create_access_token(
            {"sub": payload["sub"]}, expires_delta=timedelta(minutes=60)
        )
        new_refresh = create_refresh_token({"sub": payload["sub"]})
        return new_access, new_refresh

    def confirm_email(self, db: Session, token: str):
        payload = decode_action_token(token, "email_confirmation")
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid or expired confirmation token")

        user = self.user_repo.get_by_id(db, int(payload["sub"]))
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user.is_active:
            return user

        return self.user_repo.activate_user(db, user)

    def request_password_reset(self, db: Session, email: str):
        user = self.user_repo.get_by_email(db, email)
        if not user or not user.is_active:
            return False

        token = create_action_token(
            {"sub": str(user.id)}, "password_reset", PASSWORD_RESET_TOKEN_EXPIRATION
        )
        self._send_password_reset_email(user.email, token)
        return True

    def reset_password(self, db: Session, token: str, new_password: str):
        payload = decode_action_token(token, "password_reset")
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid or expired password reset token")

        user = self.user_repo.get_by_id(db, int(payload["sub"]))
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        hashed = get_password_hash(new_password)
        return self.user_repo.update_password(db, user, hashed)

    def _send_confirmation_email(self, user):
        token = create_action_token(
            {"sub": str(user.id)},
            "email_confirmation",
            CONFIRMATION_TOKEN_EXPIRATION,
        )
        try:
            send_email(
                subject="Potwierdź e-mail w Smart Energy",
                html_body=self._build_confirmation_body(token),
                recipient=user.email,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail="Nie udało się wysłać wiadomości potwierdzającej e-mail",
            ) from exc

    def _send_password_reset_email(self, to_email: str, token: str):
        try:
            send_email(
                subject="Reset hasła w Smart Energy",
                html_body=self._build_password_reset_body(token),
                recipient=to_email,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=500, detail="Nie udało się wysłać linku resetującego hasło"
            ) from exc

    def _build_confirmation_body(self, token: str) -> str:
        base_url = settings.FRONTEND_URL.rstrip("/")
        confirm_link = f"{base_url}/confirm-email?token={token}"
        return (
            "<p>Dziękujemy za rejestrację w Smart Energy.</p>"
            f"<p>Kliknij <a href=\"{confirm_link}\">tutaj</a>, aby potwierdzić swój adres e-mail.</p>"
            "<p>Możesz też przesłać ten token do `/api/auth/confirm` w ciele żądania.</p>"
            f"<p><strong>Token:</strong> {token}</p>"
        )

    def _build_password_reset_body(self, token: str) -> str:
        base_url = settings.FRONTEND_URL.rstrip("/")
        reset_link = f"{base_url}/reset-password?token={token}"
        return (
            "<p>Otrzymaliśmy prośbę o zresetowanie hasła.</p>"
            f"<p>Kliknij <a href=\"{reset_link}\">tutaj</a>, aby ustawić nowe hasło.</p>"
            "<p>Możesz też przesłać token do `/api/auth/password-reset/confirm`.</p>"
            f"<p><strong>Token:</strong> {token}</p>"
        )
