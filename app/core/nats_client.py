# app/core/nats_client.py
from nats.aio.client import Client as NATS
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class NatsClient:
    def __init__(self):
        self.nc = NATS()

    async def connect(self):
        await self.nc.connect(servers=[settings.NATS_URL])
        logger.info("Connected to NATS server at %s", settings.NATS_URL)

    async def publish(self, subject: str, message: dict):
        logger.info("Publishing message to subject %s: %s", subject, message)
        await self.nc.publish(subject, str(message).encode())

    async def subscribe(self, subject: str, callback):
        logger.info("Subscribing to subject %s", subject)
        await self.nc.subscribe(subject, cb=callback)

    async def close(self):
        if self.nc and self.nc.is_connected:
            await self.nc.close()
            logger.info("Closed NATS connection")
            self.nc = None
