from fastapi import HTTPException

from smart_common.core.security import (
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_and_validate_token,
    verify_password,
)
from smart_common.enums.user import UserRole
from smart_common.repositories.user import UserRepository


class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def login(self, email: str, password: str) -> tuple[str, str]:
        user = self.user_repo.get_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account is not active")

        return self._build_tokens(user)

    def refresh(self, refresh_token: str) -> tuple[str, str]:
        payload = decode_and_validate_token(refresh_token, TokenType.REFRESH)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Refresh token is malformed")

        user = self.user_repo.get_by_id(int(user_id))
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User not found or inactive")

        return self._build_tokens(user)

    def _build_tokens(self, user) -> tuple[str, str]:
        access_token = create_access_token(
            {
                "sub": str(user.id),
                "role": user.role.value if isinstance(user.role, UserRole) else str(user.role),
            }
        )
        refresh_token = create_refresh_token({"sub": str(user.id)})
        return access_token, refresh_token
