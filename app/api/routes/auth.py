from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from smart_common.core.db import get_db
from smart_common.models.user import User
from smart_common.repositories.user import UserRepository

from app.api.schemas.auth import (
    CurrentUserResponse,
    LoginRequest,
    RefreshTokenRequest,
    TokenResponse,
)
from app.core.dependencies import get_current_user
from app.services.auth_service import AuthService

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
    "/refresh",
    response_model=TokenResponse,
    status_code=200,
    summary="Refresh tokens",
    description="Rotates the refresh token and issues a new access token for an authenticated session.",
)
def refresh_token(
    payload: RefreshTokenRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    access, refresh = _get_auth_service(db).refresh(payload.refresh_token)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.get(
    "/me",
    response_model=CurrentUserResponse,
    status_code=200,
    summary="Get current user",
    description="Returns the authenticated user's profile, including assigned role and activity status.",
)
def current_user(current_user: User = Depends(get_current_user)) -> CurrentUserResponse:
    return CurrentUserResponse.model_validate(current_user)
