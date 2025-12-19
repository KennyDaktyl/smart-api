from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from smart_common.core.db import get_db
from smart_common.core.dependencies import (
    get_current_active_user,
    require_role,
)
from smart_common.enums.user import UserRole
from smart_common.models.user import User
from smart_common.repositories.user import UserRepository
from smart_common.schemas.installations import InstallationResponse
from smart_common.schemas.pagination_schema import (
    PaginatedResponse,
    PaginationMeta,
)
from smart_common.schemas.user_profile_schema import UserProfileResponse, UserProfileUpdate
from smart_common.schemas.user_schema import (
    AdminUserUpdate,
    MessageResponse,
    UserDetailsResponse,
    UserListQuery,
    UserResponse,
    UserUpdate,
)

router = APIRouter(prefix="/users", tags=["Users"])


# ======================================================
# ADMIN
# ======================================================

@router.get(
    "/list",
    response_model=PaginatedResponse[UserResponse],
    summary="List platform users (admin)",
)
def list_users(
    query: UserListQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    repo = UserRepository(db)

    filters = {
        "email": query.email,
        "is_active": query.is_active,
        "role": query.role,
    }

    users = repo.list(
        limit=query.limit,
        offset=query.offset,
        filters=filters,
        order_by=repo.model.created_at.desc(),
    )

    total = repo.count(filters=filters)

    return PaginatedResponse(
        meta=PaginationMeta(
            total=total,
            limit=query.limit,
            offset=query.offset,
        ),
        items=[UserResponse.model_validate(u) for u in users],
    )

@router.get(
    "/me/details",
    response_model=UserDetailsResponse,
    summary="Get current user full details",
)
def get_my_details(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> UserDetailsResponse:
    repo: UserRepository = UserRepository(db)

    user = repo.get_with_installations_details(current_user.id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserDetailsResponse.model_validate(user)


@router.get(
    "/{user_id}/details",
    response_model=UserDetailsResponse,
    summary="Get user full details (admin)",
)
def get_user_details_by_id(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> UserDetailsResponse:
    repo: UserRepository = UserRepository(db)

    user = repo.get_with_installations_details(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserDetailsResponse.model_validate(user)


# ======================================================
# AUTHENTICATED USER (ME)
# ======================================================

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
def get_me(
    current_user: User = Depends(get_current_active_user),
) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.get(
    "/me/installations",
    response_model=list[InstallationResponse],
    summary="Get current user installations",
)
def get_my_installations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[InstallationResponse]:
    """
    Endpoint roboczy pod UI:
    - lista instalacji
    - bez devices / providers
    """
    repo = UserRepository(db)

    user = repo.get_with_installations(current_user.id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return [
        InstallationResponse.model_validate(inst)
        for inst in user.installations
    ]


@router.get(
    "/me/profile",
    response_model=UserProfileResponse,
    summary="Get current user profile",
)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    repo = UserRepository(db)
    user = repo.get_with_profile(current_user.id)

    if not user or not user.profile:
         raise HTTPException(
            status_code=404,
            detail="User profile not found"
        )

    return UserProfileResponse.model_validate(user.profile)


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update user (admin)",
)
def admin_update_user(
    user_id: int,
    payload: AdminUserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> UserResponse:
    repo: UserRepository = UserRepository(db)

    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user = repo.update_user_admin(
        user,
        email=payload.email,
        role=payload.role,
        is_active=payload.is_active,
    )

    return UserResponse.model_validate(user)


@router.patch(
    "/me/profile",
    response_model=UserProfileResponse,
    summary="Update current user profile",
)
def update_my_profile(
    payload: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    repo = UserRepository(db)

    profile = repo.upsert_profile(
        current_user,
        payload.model_dump(exclude_unset=True),
    )

    return UserProfileResponse.model_validate(profile)


@router.delete(
    "/{user_id}",
    response_model=MessageResponse,
    summary="Deactivate user (admin)",
)
def admin_deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> MessageResponse:
    repo: UserRepository = UserRepository(db)

    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    repo.deactivate_user(user)

    return MessageResponse(message="User deactivated successfully")


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update own profile",
)
def update_me(
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> UserResponse:
    repo: UserRepository = UserRepository(db)

    user = repo.update_user_self(
        current_user,
        email=payload.email,
    )

    return UserResponse.model_validate(user)

