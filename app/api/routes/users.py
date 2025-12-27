import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from smart_common.core.db import get_db
from smart_common.core.dependencies import get_current_active_user
from smart_common.core.security import hash_password, verify_password
from smart_common.models.user import User
from smart_common.repositories.user import UserRepository
from smart_common.schemas.user_profile_schema import (
    UserProfileResponse,
    UserProfileUpdate,
)
from smart_common.schemas.user_schema import (
    ChangePasswordRequest,
    MessageResponse,
    UserDetailsResponse,
    UserResponse,
    UserSelfUpdate,
)

user_router = APIRouter(prefix="/users/me", tags=["Users"])
password_router = APIRouter(prefix="/users", tags=["Users"])

logger = logging.getLogger(__name__)


@user_router.get(
    "",
    response_model=UserResponse,
    summary="Get current user account",
)
def get_me(
    current_user: User = Depends(get_current_active_user),
) -> UserResponse:
    logger.info("User %s requested own account", current_user.email)
    return UserResponse.model_validate(current_user)


@user_router.get(
    "/details",
    response_model=UserDetailsResponse,
    summary="Get current user full details",
)
def get_my_details(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> UserDetailsResponse:
    repo = UserRepository(db)

    user = repo.get_me_details(current_user.id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    logger.info("User %s fetched own details", current_user.email)
    return UserDetailsResponse.model_validate(user, from_attributes=True)


@user_router.get(
    "/profile",
    response_model=UserProfileResponse,
    summary="Get current user profile",
)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> UserProfileResponse:
    repo = UserRepository(db)

    profile = repo.get_profile(current_user)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    logger.info("User %s fetched own profile", current_user.email)
    return UserProfileResponse.model_validate(profile, from_attributes=True)


@user_router.patch(
    "",
    response_model=UserResponse,
    summary="Update own account",
)
def update_me(
    payload: UserSelfUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> UserResponse:
    repo = UserRepository(db)

    update_data = payload.model_dump(exclude_unset=True)
    user = repo.update_user_self(
        current_user,
        data=update_data,
    )

    logger.info(
        "User %s updated own account payload=%s",
        current_user.email,
        update_data,
    )
    return UserResponse.model_validate(user)


@user_router.patch(
    "/profile",
    response_model=UserProfileResponse,
    summary="Update own profile",
)
def update_my_profile(
    payload: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> UserProfileResponse:
    repo = UserRepository(db)

    profile_data = payload.model_dump(exclude_unset=True)
    profile = repo.upsert_profile(
        current_user,
        profile_data,
    )

    logger.info(
        "User %s updated own profile payload=%s",
        current_user.email,
        profile_data,
    )
    return UserProfileResponse.model_validate(profile)


@password_router.post(
    "/change-password",
    response_model=MessageResponse,
    summary="Change own password",
)
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> MessageResponse:
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    repo = UserRepository(db)
    repo.update_password(current_user, hash_password(payload.new_password))

    logger.info("User %s changed password", current_user.email)

    return MessageResponse(message="Password updated successfully")
