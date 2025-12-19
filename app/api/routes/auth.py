import logging

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from smart_common.core.db import get_db
from smart_common.models.user import User
from smart_common.repositories.user import UserRepository
from smart_common.schemas.auth import (
    CurrentUserResponse,
    EmailTokenRequest,
    LoginRequest,
    MessageResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    TokenResponse,
)
from smart_common.schemas.user_schema import UserCreate, UserResponse
from smart_common.core.dependencies import get_current_user
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])


def _get_auth_service(db: Session) -> AuthService:
    return AuthService(UserRepository(db))


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=200,
    summary="Authenticate with email and password",
    description="Validates user credentials and returns access + refresh tokens for the client.",
)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    access, refresh = _get_auth_service(db).login(payload.email, payload.password)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=201,
    summary="Register a new user",
    description="Creates a new user account and emits an email activation token.",
)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> UserResponse:
    user = _get_auth_service(db).register(payload)
    logger.info("Activation token issued for %s", user.email)
    return UserResponse.model_validate(user)


@router.post(
    "/confirm",
    response_model=MessageResponse,
    summary="Confirm email address",
    description="Activates the user account once the email token is verified.",
)
def confirm_email(payload: EmailTokenRequest, db: Session = Depends(get_db)) -> MessageResponse:
    _get_auth_service(db).confirm_email(payload.token)
    return MessageResponse(message="Email confirmed successfully", token=payload.token)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=200,
    summary="Refresh tokens",
    description="Rotates the refresh token and issues a new access token for an authenticated session.",
)
def refresh_token(
    refresh_token_body: str | None = Body(None, embed=True),
    refresh_token_query: str | None = Query(None),
    db: Session = Depends(get_db),
) -> TokenResponse:
    refresh_token = refresh_token_body or refresh_token_query
    if not refresh_token:
        raise HTTPException(status_code=400, detail="Refresh token is required")

    access, refresh = _get_auth_service(db).refresh(refresh_token)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/password-reset/request", response_model=MessageResponse)
def request_password_reset(
    payload: PasswordResetRequest,
    db: Session = Depends(get_db),
) -> MessageResponse:
    _get_auth_service(db).request_password_reset(payload.email)

    return MessageResponse(
        message="If an account exists, password reset email has been sent"
    )


@router.post(
    "/password-reset/confirm",
    response_model=MessageResponse,
    summary="Confirm password reset",
    description="Consumes a reset token and updates the user's password.",
)
def confirm_password_reset(
    payload: PasswordResetConfirm, db: Session = Depends(get_db)
) -> MessageResponse:
    _get_auth_service(db).reset_password(payload.token, payload.new_password)
    return MessageResponse(message="Password has been updated")


@router.get(
    "/me",
    response_model=CurrentUserResponse,
    status_code=200,
    summary="Get current user",
    description="Returns the authenticated user's profile, including assigned role and activity status.",
)
def current_user(current_user: User = Depends(get_current_user)) -> CurrentUserResponse:
    return CurrentUserResponse.model_validate(current_user)
