import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from smart_common.core.db import get_db
from smart_common.models.microcontroller import Microcontroller
from smart_common.repositories.microcontroller import MicrocontrollerRepository
from smart_common.schemas.pagination_schema import PaginatedResponse, PaginationMeta
from smart_common.schemas.microcontroller_schema import (
    MicrocontrollerAdminUpdateRequest,
    MicrocontrollerConfigUpdateRequest,
    MicrocontrollerCreateRequest,
    MicrocontrollerListQuery,
    MicrocontrollerResponse,
    MicrocontrollerSensorsResponse,
    MicrocontrollerSensorsUpdateRequest,
    MicrocontrollerUpdateRequest,
)
from smart_common.core.dependencies import require_role
from smart_common.enums.user import UserRole
from smart_common.services.microcontroller_service import MicrocontrollerService


admin_router = APIRouter(
    prefix="/admin/microcontrollers",
    tags=["Admin Microcontrollers"],
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)

logger = logging.getLogger(__name__)


@admin_router.get(
    "/list",
    response_model=PaginatedResponse[MicrocontrollerResponse],
    summary="List microcontrollers (admin)",
)
def list_microcontrollers(
    query: MicrocontrollerListQuery = Depends(),
    db: Session = Depends(get_db),
):
    repo = MicrocontrollerRepository(db)

    microcontrollers = repo.list_admin(
        limit=query.limit,
        offset=query.offset,
        search=query.search,
        order_by=Microcontroller.created_at.desc(),
    )

    total = repo.count_admin(search=query.search)

    logger.info(
        "Admin listed microcontrollers total=%s limit=%s offset=%s search=%s",
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
        items=[
            MicrocontrollerResponse.model_validate(m, from_attributes=True)
            for m in microcontrollers
        ],
    )


@admin_router.post(
    "",
    response_model=MicrocontrollerResponse,
    status_code=201,
    summary="Create microcontroller (admin)",
)
def admin_register_microcontroller(
    payload: MicrocontrollerCreateRequest,
    db: Session = Depends(get_db),
):
    microcontroller_service = MicrocontrollerService(
        repo_factory=MicrocontrollerRepository
    )
    microcontroller = microcontroller_service.register_microcontroller_admin(
        db,
        payload=payload.model_dump(),
    )

    return MicrocontrollerResponse.model_validate(
        microcontroller,
        from_attributes=True,
    )


@admin_router.get(
    "/{microcontroller_id}",
    response_model=MicrocontrollerResponse,
    summary="Get microcontroller by id (admin)",
)
def admin_get_microcontroller(
    microcontroller_id: int,
    db: Session = Depends(get_db),
):
    microcontroller = MicrocontrollerRepository(db).get_full_by_id(microcontroller_id)

    return MicrocontrollerResponse.model_validate(
        microcontroller,
        from_attributes=True,
    )


@admin_router.patch(
    "/{microcontroller_id}",
    response_model=MicrocontrollerResponse,
    summary="Update microcontroller by id (admin)",
)
def admin_update_microcontroller(
    microcontroller_id: int,
    payload: MicrocontrollerAdminUpdateRequest,
    db: Session = Depends(get_db),
):
    service = MicrocontrollerService(repo_factory=MicrocontrollerRepository)

    data = payload.model_dump(exclude_unset=True)
    assigned_sensors = data.pop("assigned_sensors", None)

    microcontroller = service.update_microcontroller_admin(
        db,
        microcontroller_id=microcontroller_id,
        data=data,
        assigned_sensors=assigned_sensors,
    )

    return MicrocontrollerResponse.model_validate(
        microcontroller,
        from_attributes=True,
    )


@admin_router.patch(
    "/{microcontroller_id}/config",
    response_model=MicrocontrollerResponse,
    summary="Update microcontroller config (admin)",
)
def admin_update_microcontroller_config(
    microcontroller_id: int,
    payload: MicrocontrollerConfigUpdateRequest,
    db: Session = Depends(get_db),
):
    service = MicrocontrollerService(repo_factory=MicrocontrollerRepository)

    microcontroller = service.update_microcontroller_config(
        db,
        microcontroller_id=microcontroller_id,
        payload=payload,
    )

    return MicrocontrollerResponse.model_validate(
        microcontroller,
        from_attributes=True,
    )


@admin_router.delete(
    "/{microcontroller_id}",
    status_code=204,
    summary="Delete microcontroller (admin)",
)
def admin_delete_microcontroller(
    microcontroller_id: int,
    db: Session = Depends(get_db),
) -> None:
    MicrocontrollerRepository(db).delete_by_id(microcontroller_id)
