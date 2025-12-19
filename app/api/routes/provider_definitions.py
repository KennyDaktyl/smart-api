from fastapi import APIRouter, HTTPException

from smart_common.providers.enums import ProviderVendor
from smart_common.providers.registry import PROVIDER_DEFINITIONS
from smart_common.schemas.provider_definitions_schema import (
    ProviderDefinitionDetail,
    ProviderDefinitionsResponse,
    ProviderTypeDefinition,
    ProviderVendorSummary,
)
from smart_common.providers.enums import ProviderType

router = APIRouter(
    prefix="/providers/definitions",
    tags=["Provider Definitions"],
)


@router.get(
    "/",
    response_model=ProviderDefinitionsResponse,
    summary="List available provider types and vendors",
)
def list_provider_definitions():
    grouped: dict[
        ProviderType,
        list[ProviderVendorSummary],
    ] = {}

    for vendor, meta in PROVIDER_DEFINITIONS.items():
        ptype = meta["provider_type"]

        grouped.setdefault(ptype, []).append(
            ProviderVendorSummary(
                vendor=vendor,
                label=meta["label"],
                kind=meta["kind"],
                default_unit=meta["default_unit"],
                requires_wizard=meta["requires_wizard"],
            )
        )

    provider_types = [
        ProviderTypeDefinition(type=ptype, vendors=vendors)
        for ptype, vendors in grouped.items()
    ]

    return ProviderDefinitionsResponse(provider_types=provider_types)


# ---------------------------------------
# GET /providers/definitions/{vendor}
# ---------------------------------------


@router.get(
    "/{vendor}",
    response_model=ProviderDefinitionDetail,
    summary="Get provider definition and config schema",
)
def get_provider_definition(vendor: ProviderVendor):
    meta = PROVIDER_DEFINITIONS.get(vendor)
    if not meta:
        raise HTTPException(status_code=404, detail="Unknown provider vendor")

    return ProviderDefinitionDetail(
        vendor=vendor,
        label=meta["label"],
        provider_type=meta["provider_type"],
        kind=meta["kind"],
        default_unit=meta["default_unit"],
        requires_wizard=meta["requires_wizard"],
        config_schema=meta["config_schema"].model_json_schema(),
    )


@router.get("/{vendor}/config")
def get_provider_config(vendor: ProviderVendor):
    meta = PROVIDER_DEFINITIONS.get(vendor)
    if not meta:
        raise HTTPException(status_code=404, detail="Unknown provider vendor")

    config_schema_cls = meta["config_schema"]

    return {
        "vendor": vendor.value,
        "label": meta["label"],
        "requires_wizard": meta["requires_wizard"],
        "config_schema": config_schema_cls.model_json_schema(),
    }
