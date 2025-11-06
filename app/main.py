from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging
from fastapi.middleware.cors import CORSMiddleware

from app.core.nats_client import NatsClient
from app.api.routes import auth

logger = logging.getLogger(__name__)

nats_client = NatsClient()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await nats_client.connect()
        logger.info("Connected to NATS.")
    except Exception as e:
        logger.error(f"Failed to connect to NATS: {e}")

    yield

    try:
        await nats_client.close()
        logger.info("Connection to NATS closed.")
    except Exception as e:
        logger.warning(f"Failed to close NATS connection: {e}")


app = FastAPI(
    title="Smart Energy Backend",
    description="Backend systemu Smart Energy z integracją NATS i Huawei API",
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


@app.get("/health", tags=["System"])
def health_check():
    return {"status": "ok", "nats_connected": nats_client.nc is not None}
