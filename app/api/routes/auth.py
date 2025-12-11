from datetime import timedelta

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import (create_access_token, create_refresh_token, decode_token,
                               verify_password)
from app.repositories import raspberry_repository
from app.repositories.user_repository import UserRepository
from app.schemas.user_schema import (
    EmailTokenRequest,
    MessageResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    service = AuthService(UserRepository())
    user = service.register(db, user_in)
    return user


@router.post("/login", response_model=TokenResponse)
def login(user_in: UserLogin, db: Session = Depends(get_db)):
    service = AuthService(UserRepository())
    access, refresh = service.login(db, user_in)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/confirm", response_model=MessageResponse)
def confirm_email(request: EmailTokenRequest, db: Session = Depends(get_db)):
    service = AuthService(UserRepository())
    service.confirm_email(db, request.token)
    return MessageResponse(message="Adres e-mail został potwierdzony")


@router.post("/password-reset/request", response_model=MessageResponse)
def request_password_reset(request: PasswordResetRequest, db: Session = Depends(get_db)):
    service = AuthService(UserRepository())
    success = service.request_password_reset(db, request.email)
    if not success:
        raise HTTPException(status_code=404, detail="Konto nie istnieje lub nie zostało aktywowane")
    return MessageResponse(message="Wysłano wiadomość z instrukcjami zmiany hasła")


@router.post("/password-reset/confirm", response_model=MessageResponse)
def confirm_password_reset(request: PasswordResetConfirm, db: Session = Depends(get_db)):
    service = AuthService(UserRepository())
    service.reset_password(db, request.token, request.new_password)
    return MessageResponse(message="Hasło zostało zaktualizowane")


@router.post("/raspberry", response_model=TokenResponse)
def raspberry_auth(data: dict, db: Session = Depends(get_db)):
    uuid = data.get("uuid")
    secret_key = data.get("secret_key")

    if not uuid or not secret_key:
        raise HTTPException(status_code=400, detail="Missing uuid or secret_key")

    raspberry = raspberry_repository.get_by_uuid(db, uuid)
    if not raspberry:
        raise HTTPException(status_code=404, detail="Raspberry not found")

    if not verify_password(secret_key, raspberry.secret_key):
        raise HTTPException(status_code=401, detail="Invalid Raspberry secret")

    access_token = create_access_token(
        {"sub": str(raspberry.uuid), "scope": "device"},
        expires_delta=timedelta(days=30),
    )

    refresh_token = create_refresh_token({"sub": str(raspberry.uuid), "scope": "device"})

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    refresh_token_body: str | None = Body(None, embed=True),
    refresh_token_query: str | None = Query(None),
):
    refresh_token = refresh_token_body or refresh_token_query
    if not refresh_token:
        raise HTTPException(status_code=400, detail="Refresh token is required")

    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    service = AuthService(UserRepository())
    access, refresh = service.refresh(payload)

    return TokenResponse(access_token=access, refresh_token=refresh)
