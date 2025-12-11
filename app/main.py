# app/main.py
import logging
import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis

from app.api.routes import (auth, device_event_routes, device_routes, device_schedule_routes,
                            huawei_routes, installation_routes, inverter_power_routes,
                            inverter_routes, raspberry_routes, user_routes)
from app.core.config import settings
from app.core.logging import root_logger
from app.nats.module import nats_module
from app.workers.inverter_worker import scheduler, start_inverter_scheduler

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

sys.stdout.reconfigure(line_buffering=True)
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

    try:
        # start_inverter_scheduler()
        logger.info("Inverter scheduler started successfully.")
    except Exception as e:
        logger.exception(f"Failed to start inverter scheduler: {e}")

    yield

    logger.info("Shutting down Smart Energy Backend...")

    try:
        if scheduler.running:
            scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped successfully.")
    except Exception as e:
        logger.warning(f"Failed to stop scheduler: {e}")

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
app.include_router(user_routes.router, prefix="/api")
app.include_router(huawei_routes.router, prefix="/api")
app.include_router(installation_routes.router, prefix="/api")
app.include_router(inverter_routes.router, prefix="/api")
app.include_router(inverter_power_routes.router, prefix="/api")
app.include_router(raspberry_routes.router, prefix="/api")
app.include_router(device_routes.router, prefix="/api")
app.include_router(device_schedule_routes.router, prefix="/api")
app.include_router(device_event_routes.router, prefix="/api")


@app.get("/health", tags=["System"])
def health_check():
    return {"status": "ok", "nats_connected": app.state.nats.client.nc is not None}
