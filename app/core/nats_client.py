import asyncio
import json
import logging
from nats.aio.client import Client as NATS
from nats.js import JetStreamContext
from nats.errors import NoRespondersError, ConnectionClosedError
from nats.js.errors import NoStreamResponseError, NotFoundError

from app.core.config import settings

logger = logging.getLogger(__name__)


class NatsError(Exception):
    """Ogólny wyjątek dotyczący NATS."""
    pass


class NatsClient:
    def __init__(self):
        self.nc = NATS()
        self.js: JetStreamContext | None = None

    # ----------------------------------------------------
    # CONNECT
    # ----------------------------------------------------
    async def connect(self):
        if self.nc.is_connected:
            return

        logger.info(f"Connecting to NATS: {settings.NATS_URL}")
        try:
            await self.nc.connect(servers=[settings.NATS_URL])
        except Exception as e:
            raise NatsError(f"Cannot connect to NATS: {e}")

        self.js = self.nc.jetstream()

        logger.info("Connected to NATS")

    # ----------------------------------------------------
    # CLASSIC PUBLISH
    # ----------------------------------------------------
    async def publish(self, subject: str, message: dict):
        await self.connect()
        try:
            await self.nc.publish(subject, json.dumps(message).encode())
        except Exception as e:
            raise NatsError(f"NATS publish failed: {e}")

    # ----------------------------------------------------
    # JETSTREAM PUBLISH
    # ----------------------------------------------------
    async def publish_js(self, subject: str, message: dict):
        await self.connect()

        if not self.js:
            raise NatsError("JetStream not initialized")

        data = json.dumps(message).encode()

        try:
            ack = await self.js.publish(subject, data)
        except NoRespondersError:
            raise NatsError("No NATS JetStream responders")
        except NoStreamResponseError:
            raise NatsError(f"Stream for subject '{subject}' not found")
        except Exception as e:
            raise NatsError(f"NATS JetStream publish failed: {e}")

        logger.info(f"📤 JS Published to {subject}, seq={ack.seq}")
        return ack

    # ----------------------------------------------------
    # ACK LISTENING
    # ----------------------------------------------------
    async def publish_and_wait_for_ack(
        self,
        subject: str,
        ack_subject: str,
        message: dict,
        match_id: int,
        timeout: float = 3.0,
    ):
        await self.connect()

        loop = asyncio.get_event_loop()
        future = loop.create_future()

        async def _ack_handler(msg):
            try:
                data = json.loads(msg.data.decode())

                if data.get("device_id") == match_id:
                    logger.info(f"ACK received for device={match_id}: {data}")

                    if not future.done():
                        future.set_result(data)
            except Exception as e:
                logger.error(f"ACK parse error: {e}")

        try:
            sub = await self.nc.subscribe(ack_subject, cb=_ack_handler)
        except Exception as e:
            raise NatsError(f"Cannot subscribe to ACK subject '{ack_subject}': {e}")

        # Wyślij event do JetStream
        try:
            await self.js.publish(subject, json.dumps(message).encode())
        except NoStreamResponseError:
            raise NatsError(f"No JetStream stream for subject '{subject}'")
        except Exception as e:
            raise NatsError(f"Failed to publish event: {e}")

        # Czekaj na ACK
        try:
            return await asyncio.wait_for(future, timeout)

        except asyncio.TimeoutError:
            raise NatsError(f"ACK timeout on subject '{ack_subject}'")

        except ConnectionClosedError:
            raise NatsError("NATS connection lost")

        except Exception as e:
            raise NatsError(f"Unknown NATS error: {e}")

        finally:
            try:
                await sub.unsubscribe()
            except Exception:
                pass

    # ----------------------------------------------------
    # CLOSE
    # ----------------------------------------------------
    async def close(self):
        if self.nc.is_connected:
            try:
                await self.nc.flush()
                await self.nc.close()
            except Exception:
                pass
            logger.info("Closed NATS connection")


# GLOBAL INSTANCE
nats_client = NatsClient()
