import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis

import app.core.logging
from app.api.routes import (auth, device_routes, device_schedule_routes, huawei_routes,
                            installation_routes, inverter_power_routes, inverter_routes,
                            raspberry_routes, user_routes)
from app.core.config import settings
from app.core.logging import LOG_FILE_PATH
from app.core.nats_client import NatsClient
from app.workers.inverter_worker import scheduler, start_inverter_scheduler

sys.stdout.reconfigure(line_buffering=True)
logger = logging.getLogger(__name__)
nats_client = NatsClient()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await nats_client.connect()
        logger.info("Connected to NATS.")
    except Exception as e:
        logger.error(f"Failed to connect to NATS: {e}")

    try:
        redis = aioredis.from_url(
            f"redis://{settings.REDIS_HOST}:6379", encoding="utf8", decode_responses=True
        )
        FastAPICache.init(RedisBackend(redis), prefix="smartenergy-cache")
        logger.info("Redis cache initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize Redis cache: {e}")

    try:
        start_inverter_scheduler()
        logger.info("Inverter scheduler started at application startup.")
    except Exception as e:
        logger.exception(f"Failed to start inverter scheduler: {e}")

    yield

    try:
        if scheduler.running:
            scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped successfully.")
    except Exception as e:
        logger.warning(f"Failed to stop scheduler: {e}")

    try:
        await nats_client.close()
        logger.info("Connection to NATS closed.")
    except Exception as e:
        logger.warning(f"Failed to close NATS connection: {e}")


app = FastAPI(
    title="Smart Energy Backend",
    description="Backend system for Smart Energy with NATS and Huawei integration",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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


@app.get("/health", tags=["System"])
def health_check():
    logger.info("Health check called.")
    return {"status": "ok", "nats_connected": nats_client.nc is not None}
