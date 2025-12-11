from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.dependencies import get_current_user
from app.core.security import decrypt_password, encrypt_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user_schema import HuaweiCredentialsUpdate, UserInstallationsResponse, UserResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/list", response_model=list[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to access this resource")

    user_repo = UserRepository()
    users = user_repo.get_all(db)
    return users


@router.get("/details/{user_id}", response_model=UserInstallationsResponse)
def get_user_details_by_id(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to access this resource")

    user_repo = UserRepository()
    user = user_repo.get_user_installations_details(db, user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@router.get("/me/details", response_model=UserInstallationsResponse)
def get_user_details(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_repo = UserRepository()
    user = user_repo.get_user_installations_details(db, current_user.id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@router.put("/huawei-credentials", response_model=UserResponse)
def update_huawei_credentials(
    credentials: HuaweiCredentialsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = current_user
    user.huawei_username = credentials.huawei_username
    user.huawei_password_encrypted = encrypt_password(credentials.huawei_password)

    db.commit()
    db.refresh(user)
    return user


@router.get("/me/huawei-credentials", response_model=HuaweiCredentialsUpdate)
def get_huawei_credentials(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user or not user.huawei_username:
        raise HTTPException(status_code=404, detail="Huawei credentials not found")

    return HuaweiCredentialsUpdate(
        huawei_username=user.huawei_username,
        huawei_password=decrypt_password(user.huawei_password_encrypted),
    )


@router.get("/me/installations", response_model=UserInstallationsResponse)
def get_user_installations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_repo = UserRepository()
    user = user_repo.get_user_installations_details(db, current_user.id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user
