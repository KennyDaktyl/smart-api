# app/core/nats/module.py

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.nats.client import NatsClient
from app.nats.listener import NatsListener
from app.nats.publisher import NatsPublisher

logger = logging.getLogger(__name__)


class NatsModule:

    def __init__(self, create_stream: bool = False):
        self.client = NatsClient()
        self.publisher = NatsPublisher(self.client)
        self.listener = NatsListener(self.client)
        self.create_stream = create_stream

    async def _ensure_stream(self):
        js = self.client.js

        try:
            await js.stream_info("device_communication")
            logger.info("[NATS] Stream device_communication already exists.")
        except Exception:
            logger.warning("[NATS] Stream missing — creating device_communication...")
            await js.add_stream(
                name="device_communication",
                subjects=["device_communication.>"],
                storage="file",
                retention="limits",
            )
            logger.info("[NATS] Stream device_communication created.")

    async def ensure_stream(self):
        await self._ensure_stream()

    def init_app(self, app: FastAPI):

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            logger.info("[NATS] Connecting...")

            await self.client.connect()

            if self.create_stream:
                await self._ensure_stream()

            await self.listener.subscribe()

            logger.info("[NATS] Ready.")

            app.state.nats = self

            yield

            logger.info("[NATS] Closing...")
            await self.client.close()

        app.router.lifespan_context = lifespan
        logger.info("[NATS] Lifespan enabled.")


nats_module = NatsModule(create_stream=False)
