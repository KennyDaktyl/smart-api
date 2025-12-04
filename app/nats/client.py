# app/core/nats/client.py
import logging

from nats.aio.client import Client as NATS
from nats.js import JetStreamContext

from app.core.config import settings

logger = logging.getLogger(__name__)


class NatsClient:
    def __init__(self):
        self.nc: NATS | None = None
        self.js: JetStreamContext | None = None

    async def connect(self):
        if self.nc and self.nc.is_connected:
            return

        async def disconnected_cb():
            logger.debug("NATS connection closed")

        async def reconnected_cb():
            logger.warning("NATS reconnected — refreshing JetStream context...")
            if self.nc:
                self.js = self.nc.jetstream()
                logger.info("JetStream context refreshed after reconnect")

        async def error_cb(e):
            logger.error(f"NATS client error: {e}")

        try:
            self.nc = NATS()

            await self.nc.connect(
                servers=[settings.NATS_URL],
                name="smartenergy-backend",
                reconnect_time_wait=2,
                max_reconnect_attempts=60,
                disconnected_cb=disconnected_cb,
                reconnected_cb=reconnected_cb,
                error_cb=error_cb,
            )

            self.js = self.nc.jetstream()

            logger.info("Connected to NATS + JetStream")

        except Exception as e:
            logger.error(f"NATS connection failed: {e}")
            raise e

    @property
    def connected(self) -> bool:
        return self.nc is not None and self.nc.is_connected

    async def ensure_connected(self):
        if not self.nc or not self.nc.is_connected:
            await self.connect()
        else:
            try:
                await self.nc.flush(timeout=1)
            except:
                logger.warning("NATS socket dead — reconnecting...")
                await self.connect()

    async def close(self):
        try:
            if self.nc:
                await self.nc.drain()
                await self.nc.close()
                logger.info("NATS connection closed")
        except Exception as e:
            logger.warning(f"Failed to close NATS: {e}")
