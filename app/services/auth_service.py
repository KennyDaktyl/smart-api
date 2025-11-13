# app/services/auth_service.py

from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.constans.role import UserRole
from app.core.security import (create_access_token, create_refresh_token, get_password_hash,
                               verify_password)
from app.repositories.user_repository import UserRepository
from app.schemas.user_schema import UserCreate, UserLogin


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
        }

        return self.user_repo.create(db, user_data)

    def login(self, db: Session, user_in: UserLogin):
        user = self.user_repo.get_by_email(db, user_in.email)
        if not user or not verify_password(user_in.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        access_token = create_access_token({"sub": str(user.id), "role": user.role})
        refresh_token = create_refresh_token({"sub": str(user.id)})

        return access_token, refresh_token

    def refresh(self, payload: dict):
        new_access = create_access_token(
            {"sub": payload["sub"]}, expires_delta=timedelta(minutes=60)
        )
        new_refresh = create_refresh_token({"sub": payload["sub"]})
        return new_access, new_refresh
