import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from smart_common.core.db import get_db
from smart_common.core.dependencies import require_role
from smart_common.enums.user import UserRole
from smart_common.models.user import User
from smart_common.repositories.user import UserRepository
from smart_common.schemas.pagination_schema import PaginatedResponse, PaginationMeta
from smart_common.schemas.user_schema import (
    AdminUserCreate,
    AdminUserUpdate,
    MessageResponse,
    UserDetailsResponse,
    UserFullDetailsResponse,
    UserListQuery,
    UserResponse,
)

admin_router = APIRouter(
    prefix="/admin/users",
    tags=["Admin Users"],
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)

logger = logging.getLogger(__name__)


@admin_router.get(
    "/list",
    response_model=PaginatedResponse[UserResponse],
    summary="List users (admin)",
)
def list_users(
    query: UserListQuery = Depends(),
    db: Session = Depends(get_db),
):
    repo = UserRepository(db)

    users = repo.list_admin(
        limit=query.limit,
        offset=query.offset,
        search=query.search,
        order_by=User.created_at.desc(),
    )

    total = repo.count_admin(search=query.search)

    logger.info(
        "Admin listed users total=%s limit=%s offset=%s search=%s",
        total,
        query.limit,
        query.offset,
        query.search,
    )

    return PaginatedResponse(
        meta=PaginationMeta(
            total=total,
            limit=query.limit,
            offset=query.offset,
        ),
        items=[UserResponse.model_validate(u) for u in users],
    )


@admin_router.post(
    "",
    response_model=UserResponse,
    summary="Create user (admin)",
)
def create_user_admin(
    payload: AdminUserCreate,
    db: Session = Depends(get_db),
) -> UserResponse:
    repo = UserRepository(db)

    existing = repo.get_by_email(payload.email)
    if existing:
        raise HTTPException(
            status_code=400,
            detail="User with this email already exists",
        )

    user = repo.create_user_admin(
        email=payload.email,
        password=payload.password,
        role=payload.role,
        is_active=payload.is_active,
    )

    logger.info(
        "Admin created user id=%s email=%s",
        user.id,
        user.email,
    )

    return UserResponse.model_validate(user)


@admin_router.get(
    "/{user_id}/details",
    response_model=UserDetailsResponse,
    summary="Get user full details (admin)",
)
def get_user_details(
    user_id: int,
    db: Session = Depends(get_db),
) -> UserDetailsResponse:
    repo = UserRepository(db)

    user = repo.get_user_details(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    logger.info("Admin fetched details for user id=%s", user_id)

    return UserFullDetailsResponse.model_validate(user, from_attributes=True)


@admin_router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update user account (admin)",
)
def update_user_admin(
    user_id: int,
    payload: AdminUserUpdate,
    db: Session = Depends(get_db),
) -> UserResponse:
    repo = UserRepository(db)

    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = payload.model_dump(exclude_unset=True)
    user = repo.update_user_admin(
        user,
        data=update_data,
    )

    logger.info(
        "Admin updated user id=%s payload=%s",
        user_id,
        update_data,
    )

    return UserResponse.model_validate(user)


@admin_router.delete(
    "/{user_id}",
    response_model=MessageResponse,
    summary="Deactivate user (admin)",
)
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
) -> MessageResponse:
    repo = UserRepository(db)

    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    repo.deactivate_user(user)

    logger.info("Admin deactivated user id=%s", user_id)

    return MessageResponse(message="User deactivated successfully")
