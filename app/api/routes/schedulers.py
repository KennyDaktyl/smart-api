import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from smart_common.core.db import get_db
from smart_common.core.dependencies import get_current_user
from smart_common.models.user import User
from smart_common.providers.enums import ProviderKind
from smart_common.repositories.device import DeviceRepository
from smart_common.repositories.provider import ProviderRepository
from smart_common.repositories.scheduler import SchedulerRepository
from smart_common.schemas.scheduler_schema import (
    SchedulerCreateRequest,
    SchedulerPowerThresholdProvider,
    SchedulerPowerThresholdUnitsResponse,
    SchedulerResponse,
    SchedulerUpdateRequest,
)
from smart_common.services.scheduler_service import SchedulerService

logger = logging.getLogger(__name__)

scheduler_router = APIRouter(
    prefix="/schedulers",
    tags=["Schedulers"],
)


def _validate_slot_providers(*, db: Session, user_id: int, slots: list[dict]) -> None:
    provider_ids = sorted(
        {
            slot.get("power_provider_id")
            for slot in slots
            if slot.get("use_power_threshold")
            and slot.get("power_provider_id") is not None
        }
    )
    if not provider_ids:
        return

    provider_repo = ProviderRepository(db)

    for provider_id in provider_ids:
        provider = provider_repo.get_for_user(provider_id=provider_id, user_id=user_id)
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Power provider {provider_id} not found",
            )
        if provider.kind != ProviderKind.POWER:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Provider {provider_id} is not a POWER provider",
            )


@scheduler_router.get("", response_model=list[SchedulerResponse])
def list_schedulers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = SchedulerService(SchedulerRepository, DeviceRepository)
    schedulers = service.list_for_user(db=db, user_id=current_user.id)
    return [
        SchedulerResponse.model_validate(item, from_attributes=True)
        for item in schedulers
    ]


@scheduler_router.post(
    "", response_model=SchedulerResponse, status_code=status.HTTP_201_CREATED
)
def create_scheduler(
    payload: SchedulerCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = SchedulerService(SchedulerRepository, DeviceRepository)
    payload_data = payload.model_dump()
    _validate_slot_providers(
        db=db,
        user_id=current_user.id,
        slots=payload_data["slots"],
    )
    scheduler = service.create_scheduler(
        db=db,
        user_id=current_user.id,
        payload=payload_data,
    )
    return SchedulerResponse.model_validate(scheduler, from_attributes=True)


@scheduler_router.get(
    "/power-threshold/units",
    response_model=SchedulerPowerThresholdUnitsResponse,
)
def get_power_threshold_units(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SchedulerPowerThresholdUnitsResponse:
    provider_repo = ProviderRepository(db)
    providers = provider_repo.list_power_for_user(user_id=current_user.id)

    units: list[str] = []
    units_seen = set(units)
    response_providers: list[SchedulerPowerThresholdProvider] = []

    for provider in providers:
        if provider.unit is None:
            continue

        unit_value = provider.unit.value
        if unit_value not in units_seen:
            units_seen.add(unit_value)
            units.append(unit_value)

        response_providers.append(
            SchedulerPowerThresholdProvider(
                id=provider.id,
                uuid=provider.uuid,
                name=provider.name,
                unit=unit_value,
            )
        )

    return SchedulerPowerThresholdUnitsResponse(
        units=units,
        providers=response_providers,
    )


@scheduler_router.put("/{scheduler_id}", response_model=SchedulerResponse)
def update_scheduler(
    scheduler_id: int,
    payload: SchedulerUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = SchedulerService(SchedulerRepository, DeviceRepository)
    payload_data = payload.model_dump()
    _validate_slot_providers(
        db=db,
        user_id=current_user.id,
        slots=payload_data["slots"],
    )
    scheduler = service.update_scheduler(
        db=db,
        user_id=current_user.id,
        scheduler_id=scheduler_id,
        payload=payload_data,
    )
    return SchedulerResponse.model_validate(scheduler, from_attributes=True)


@scheduler_router.delete("/{scheduler_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scheduler(
    scheduler_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = SchedulerService(SchedulerRepository, DeviceRepository)
    service.delete_scheduler(
        db=db,
        user_id=current_user.id,
        scheduler_id=scheduler_id,
    )
