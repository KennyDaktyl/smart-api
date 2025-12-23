from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from smart_common.core.db import get_db
from smart_common.core.dependencies import get_current_user
from smart_common.models.microcontroller import Microcontroller
from smart_common.models.user import User
from smart_common.repositories.microcontroller import MicrocontrollerRepository


def get_owned_microcontroller(
    microcontroller_uuid: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Microcontroller:
    """Ensure the requested microcontroller is owned by the current user."""
    microcontroller = MicrocontrollerRepository(db).get_for_user_by_uuid(
        microcontroller_uuid, current_user.id
    )
    if not microcontroller:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Microcontroller not found",
        )
    return microcontroller
