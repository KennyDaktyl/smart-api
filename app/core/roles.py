from fastapi import Depends, HTTPException, status

from app.constans.role import UserRole
from app.core.dependencies import get_current_user


def require_role(*allowed_roles: UserRole):
    """
    @router.get("/", dependencies=[Depends(require_role(UserRole.ADMIN))])
    """

    def role_dependency(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden for role {current_user.role}",
            )
        return current_user

    return role_dependency
