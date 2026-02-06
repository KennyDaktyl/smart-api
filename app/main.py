from smart_common.smart_logging.logger import setup_logging

setup_logging()

import logging
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes.provider_definitions import provider_definition_router
from app.api.routes.providers import provider_router
from app.api.routes.users import user_router, password_router
from app.api.routes.auth import auth_router
from app.api.routes.enums import enums_router
from app.api.routes.provider_wizard import wizard_router
from app.api.routes.admin import microcontrollers, users
from app.api.routes.microcontrollers import microcontroller_router
from app.api.routes.devices import device_router
from app.api.routes.device_events import device_events_router
from app.api.routes.provider_measurements import provider_measurements_router

from smart_common.core.config import settings

# ------------------------------------------------------------------
# LOGGING INIT (MUST BE FIRST)
# ------------------------------------------------------------------

logger = logging.getLogger(__name__)
logger.info("Starting Smart Energy Backend application")

# ------------------------------------------------------------------
# FASTAPI APP
# ------------------------------------------------------------------

app = FastAPI(
    title="Smart Energy Backend",
    description="Backend system for Smart Energy with NATS and Huawei integration",
    version="1.0.0",
)

# ------------------------------------------------------------------
# MIDDLEWARE
# ------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------
# ROUTERS
# ------------------------------------------------------------------

app.include_router(auth_router, prefix="/api")
app.include_router(user_router, prefix="/api")
app.include_router(password_router, prefix="/api")
app.include_router(users.admin_router, prefix="/api")
app.include_router(microcontrollers.admin_router, prefix="/api")
app.include_router(provider_definition_router, prefix="/api")
app.include_router(provider_router, prefix="/api")
app.include_router(enums_router, prefix="/api")
app.include_router(wizard_router, prefix="/api")
app.include_router(microcontroller_router, prefix="/api")
app.include_router(device_router, prefix="/api")
app.include_router(device_events_router, prefix="/api")
app.include_router(provider_measurements_router, prefix="/api")
# ------------------------------------------------------------------
# HEALTHCHECK
# ------------------------------------------------------------------


@app.get("/health", tags=["System"])
def health_check():
    nats_connected = False

    # zabezpieczenie: health nie może wywalać 500
    try:
        nats = getattr(app.state, "nats", None)
        if nats and getattr(nats, "client", None):
            nats_connected = bool(nats.client.nc)
    except Exception:
        logger.warning("Healthcheck: failed to determine NATS connection")

    return {
        "status": "ok",
        "nats_connected": nats_connected,
        "env": settings.ENV,
    }


# ------------------------------------------------------------------
# EXCEPTION HANDLERS
# ------------------------------------------------------------------


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(
        "Validation error on %s %s | errors=%s",
        request.method,
        request.url.path,
        exc.errors(),
    )
    return JSONResponse(
        status_code=422,
        content=jsonable_encoder({"detail": exc.errors()}),
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.warning(
        "HTTPException %s on %s %s | detail=%s",
        exc.status_code,
        request.method,
        request.url.path,
        exc.detail,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(
        "🔥 Unhandled exception on %s %s",
        request.method,
        request.url.path,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# ------------------------------------------------------------------
# LOCAL RUN
# ------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=settings.BACKEND_PORT,
        reload=True,
        log_level="info",
    )
