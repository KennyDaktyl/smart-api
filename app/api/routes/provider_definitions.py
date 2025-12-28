from fastapi import APIRouter, HTTPException

from smart_common.providers.definitions.registry import PROVIDER_DEFINITION_REGISTRY
from smart_common.providers.enums import ProviderVendor
from smart_common.schemas.provider_definitions_schema import (
    ProviderDefinitionDetail,
    ProviderDefinitionsResponse,
    ProviderTypeDefinition,
    ProviderVendorSummary,
)
from smart_common.providers.enums import ProviderType

provider_definition_router = APIRouter(
    prefix="/providers/definitions",
    tags=["Provider Definitions"],
)


@provider_definition_router.get(
    "/list",
    response_model=ProviderDefinitionsResponse,
    summary="List available provider types and vendors",
)
def list_provider_definitions():
    grouped: dict[
        ProviderType,
        list[ProviderVendorSummary],
    ] = {}

    for vendor, definition in PROVIDER_DEFINITION_REGISTRY.items():
        ptype = definition.provider_type

        grouped.setdefault(ptype, []).append(
            ProviderVendorSummary(
                vendor=vendor,
                label=definition.label,
                kind=definition.kind,
                default_unit=definition.default_unit,
                requires_wizard=definition.requires_wizard,
            )
        )

    provider_types = [
        ProviderTypeDefinition(type=ptype, vendors=vendors)
        for ptype, vendors in grouped.items()
    ]

    return ProviderDefinitionsResponse(provider_types=provider_types)


@provider_definition_router.get(
    "/{vendor}",
    response_model=ProviderDefinitionDetail,
    summary="Get provider definition and config schema",
)
def get_provider_definition(vendor: ProviderVendor):
    definition = PROVIDER_DEFINITION_REGISTRY.get(vendor)
    if not definition:
        raise HTTPException(status_code=404, detail="Unknown provider vendor")

    return ProviderDefinitionDetail(
        vendor=vendor,
        label=definition.label,
        provider_type=definition.provider_type,
        kind=definition.kind,
        default_unit=definition.default_unit,
        requires_wizard=definition.requires_wizard,
        config_schema=definition.config_schema.model_json_schema(),
    )


@provider_definition_router.get("/{vendor}/config")
def get_provider_config(vendor: ProviderVendor):
    definition = PROVIDER_DEFINITION_REGISTRY.get(vendor)
    if not definition:
        raise HTTPException(status_code=404, detail="Unknown provider vendor")

    config_schema_cls = definition.config_schema

    return {
        "vendor": vendor.value,
        "label": definition.label,
        "requires_wizard": definition.requires_wizard,
        "config_schema": config_schema_cls.model_json_schema(),
    }
