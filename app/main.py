# app/main.py
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis

from app.api.routes import (
    auth,
    device_auto_config,
    device_events,
    device_schedules,
    devices,
    installations,
    microcontrollers,
    providers,
)

from smart-common.config import settings

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):

    logger.info("Starting Smart Energy Backend...")

    try:
        redis = aioredis.from_url(f"redis://{settings.REDIS_HOST}:6379")
        FastAPICache.init(RedisBackend(redis), prefix="smartenergy-cache")
        logger.info("Redis cache initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize Redis cache: {e}")

    nats_module.init_app(app)

    yield

    logger.info("Shutting down Smart Energy Backend...")

    logger.info("Backend shutdown complete.")


app = FastAPI(
    title="Smart Energy Backend",
    description="Backend system for Smart Energy with NATS and Huawei integration",
    version="1.0.0",
    lifespan=lifespan,
)


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


app.include_router(auth.router, prefix="/api")
app.include_router(installations.router, prefix="/api")
app.include_router(microcontrollers.router, prefix="/api")
app.include_router(providers.router, prefix="/api")
app.include_router(devices.router, prefix="/api")
app.include_router(device_auto_config.router, prefix="/api")
app.include_router(device_schedules.router, prefix="/api")
app.include_router(device_events.router, prefix="/api")


@app.get("/health", tags=["System"])
def health_check():
    return {"status": "ok", "nats_connected": app.state.nats.client.nc is not None}
