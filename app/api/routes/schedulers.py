import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from smart_common.core.db import get_db
from smart_common.core.dependencies import get_current_user
from smart_common.models.user import User
from smart_common.repositories.scheduler import SchedulerRepository
from smart_common.schemas.scheduler_schema import (
    SchedulerCreateRequest,
    SchedulerResponse,
    SchedulerUpdateRequest,
)
from smart_common.services.scheduler_service import SchedulerService

logger = logging.getLogger(__name__)

scheduler_router = APIRouter(
    prefix="/schedulers",
    tags=["Schedulers"],
)


@scheduler_router.get("", response_model=list[SchedulerResponse])
def list_schedulers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = SchedulerService(SchedulerRepository)
    schedulers = service.list_for_user(db=db, user_id=current_user.id)
    return [SchedulerResponse.model_validate(item, from_attributes=True) for item in schedulers]


@scheduler_router.post("", response_model=SchedulerResponse, status_code=status.HTTP_201_CREATED)
def create_scheduler(
    payload: SchedulerCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = SchedulerService(SchedulerRepository)
    scheduler = service.create_scheduler(
        db=db,
        user_id=current_user.id,
        payload=payload.model_dump(),
    )
    return SchedulerResponse.model_validate(scheduler, from_attributes=True)


@scheduler_router.put("/{scheduler_id}", response_model=SchedulerResponse)
def update_scheduler(
    scheduler_id: int,
    payload: SchedulerUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = SchedulerService(SchedulerRepository)
    scheduler = service.update_scheduler(
        db=db,
        user_id=current_user.id,
        scheduler_id=scheduler_id,
        payload=payload.model_dump(),
    )
    return SchedulerResponse.model_validate(scheduler, from_attributes=True)


@scheduler_router.delete("/{scheduler_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scheduler(
    scheduler_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = SchedulerService(SchedulerRepository)
    service.delete_scheduler(
        db=db,
        user_id=current_user.id,
        scheduler_id=scheduler_id,
    )
