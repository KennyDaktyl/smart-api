from datetime import datetime
from typing import List

from pydantic import BaseModel, EmailStr

from app.constans.role import UserRole
from app.schemas.installation_schema import InstallationOut


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    role: UserRole
    is_active: bool
    created_at: datetime
    huawei_username: str | None = None

    model_config = {"from_attributes": True}


class HuaweiCredentialsUpdate(BaseModel):
    huawei_username: str
    huawei_password: str


class UserInstallationsResponse(BaseModel):
    id: int
    email: str
    role: str
    huawei_username: str | None = None
    created_at: datetime
    installations: List[InstallationOut] = []

    model_config = {"from_attributes": True}
