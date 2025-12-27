from __future__ import annotations

import logging
from fastapi import APIRouter, Body, HTTPException

from smart_common.providers.enums import ProviderType, ProviderVendor
from smart_common.providers.exceptions import ProviderError
from smart_common.providers.registry import PROVIDER_DEFINITIONS
from smart_common.providers.wizard.engine import WizardEngine
from smart_common.providers.wizard.exceptions import (
    WizardNotConfiguredError,
    WizardResultError,
    WizardSessionExpiredError,
    WizardSessionStateError,
    WizardStepNotFoundError,
)
from smart_common.schemas.provider_wizard import WizardRuntimeResponse


logger = logging.getLogger(__name__)

wizard_router = APIRouter(prefix="/providers/wizard", tags=["Provider Wizard"])

wizard_engine = WizardEngine(PROVIDER_DEFINITIONS)


@wizard_router.get(
    "/{vendor}",
    response_model=WizardRuntimeResponse,
    summary="Start provider wizard (get first step)",
)
def get_wizard_start(vendor: ProviderVendor) -> WizardRuntimeResponse:
    meta = PROVIDER_DEFINITIONS.get(vendor)
    if (
        not meta
        or meta.get("provider_type") != ProviderType.API
        or not meta.get("wizard")
    ):
        raise HTTPException(status_code=404, detail="Wizard not available")

    wizard = meta["wizard"]

    if "auth" not in wizard:
        raise HTTPException(
            status_code=500,
            detail="Wizard must define 'auth' as the first step",
        )

    auth_step = wizard["auth"]

    return WizardRuntimeResponse(
        vendor=vendor,
        step="auth",
        schema=auth_step.schema.model_json_schema(),
        options={},
        context={},
        is_complete=False,
        final_config=None,
    )


@wizard_router.post(
    "/{vendor}/{step}",
    response_model=WizardRuntimeResponse,
    summary="Execute provider wizard step",
)
def run_wizard_step(
    vendor: ProviderVendor,
    step: str,
    payload: dict = Body(...),
) -> WizardRuntimeResponse:
    meta = PROVIDER_DEFINITIONS.get(vendor)
    if (
        not meta
        or meta.get("provider_type") != ProviderType.API
        or not meta.get("wizard")
    ):
        raise HTTPException(status_code=404, detail="Wizard not available")

    logger.info(
        "Wizard API call",
        extra={"vendor": vendor.value, "step": step},
    )

    payload_data = dict(payload)
    context = payload_data.pop("context", {}) or {}

    try:
        result = wizard_engine.run_step(
            vendor=vendor,
            step_name=step,
            payload=payload_data,
            context=context,
        )
        return WizardRuntimeResponse(**result)
    # -----------------------------
    # PROVIDER / ADAPTER ERRORS
    # -----------------------------
    except ProviderError as exc:
        logger.warning(
            "Provider error during wizard",
            extra={
                "vendor": vendor.value,
                "step": step,
                "code": exc.code,
                "status": exc.status_code,
            },
        )

        status_code = exc.status_code
        if status_code == 401:
            status_code = 400

            raise HTTPException(
                status_code=status_code,
                detail={
                    "message": exc.message,
                    "code": exc.code,
                    "details": exc.details,
                },
            )

    except HTTPException as exc:
        raise exc

    # -----------------------------
    # WIZARD ERRORS (EXPECTED)
    # -----------------------------
    except WizardSessionExpiredError as exc:
        logger.info("Wizard session expired", extra={"vendor": vendor.value})
        raise HTTPException(status_code=410, detail=str(exc))

    except WizardSessionStateError as exc:
        logger.warning("Wizard invalid state", extra={"vendor": vendor.value})
        raise HTTPException(status_code=400, detail=str(exc))

    except WizardStepNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    except WizardNotConfiguredError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    except WizardResultError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # -----------------------------
    # UNKNOWN (BUG)
    # -----------------------------
    except Exception:
        logger.exception("Unhandled wizard error")
        raise HTTPException(
            status_code=500,
            detail="Internal wizard error",
        )
