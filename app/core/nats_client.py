import asyncio
import json
import logging

from nats.aio.client import Client as NATS
from nats.errors import ConnectionClosedError, NoServersError, TimeoutError

from app.core.config import settings

logger = logging.getLogger(__name__)


class NatsClient:
    """
    Klient NATS do publikowania i subskrybowania wiadomości.
    - Używa JSON do komunikacji
    - Bezpiecznie otwiera i zamyka połączenie
    - Może być używany zarówno przez backend, jak i workery
    """

    def __init__(self):
        self.nc = NATS()

    async def connect(self):
        """Łączy się z serwerem NATS."""
        try:
            if not self.nc.is_connected:
                await self.nc.connect(servers=[settings.NATS_URL])
                logger.info(f"✅ Connected to NATS server at {settings.NATS_URL}")
        except NoServersError:
            logger.error(f"❌ Unable to connect to NATS server at {settings.NATS_URL}")
            raise
        except Exception as e:
            logger.exception(f"❌ Error connecting to NATS: {e}")
            raise

    async def publish(self, subject: str, message: dict):
        """Publikuje wiadomość JSON do NATS."""
        try:
            if not self.nc.is_connected:
                await self.connect()
            data = json.dumps(message).encode()
            await self.nc.publish(subject, data)
            logger.debug(f"📤 Published to {subject}: {message}")
        except (ConnectionClosedError, TimeoutError) as e:
            logger.warning(f"⚠️ NATS connection issue during publish: {e}")
        except Exception as e:
            logger.exception(f"❌ Error publishing to NATS: {e}")

    async def subscribe(self, subject: str, callback):
        """Subskrybuje wiadomości na dany temat."""
        try:
            if not self.nc.is_connected:
                await self.connect()
            await self.nc.subscribe(subject, cb=callback)
            logger.info(f"📡 Subscribed to NATS subject: {subject}")
        except Exception as e:
            logger.exception(f"❌ Error subscribing to NATS: {e}")

    async def close(self):
        """Bezpieczne zamknięcie połączenia."""
        try:
            if self.nc and self.nc.is_connected:
                await self.nc.flush()
                await self.nc.close()
                logger.info("🔌 Closed NATS connection")
        except Exception as e:
            logger.warning(f"⚠️ Error closing NATS connection: {e}")

    async def publish_and_wait_for_ack(
        self,
        subject: str,
        ack_subject: str,
        message: dict,
        match_id: int,
        timeout: float = 3.0,
    ) -> dict:
        """
        Publikuje wiadomość i czeka na ACK z podanego tematu.
        `match_id` służy do dopasowania odpowiedzi dla konkretnego urządzenia.
        """
        await self.connect()
        loop = asyncio.get_event_loop()
        future = loop.create_future()

        async def _ack_handler(msg):
            try:
                data = json.loads(msg.data.decode())
                if data.get("device_id") == match_id:
                    logger.info(f"✅ ACK received for device {match_id}: {data}")
                    if not future.done():
                        future.set_result(data)
            except Exception as e:
                logger.error(f"❌ ACK parse error: {e}")

        # Tymczasowa subskrypcja na ACK
        sub = await self.nc.subscribe(ack_subject, cb=_ack_handler)

        # Wyślij komendę
        await self.nc.publish(subject, json.dumps(message).encode())
        logger.info(f"📤 Sent NATS command to {subject}: {message}")

        try:
            result = await asyncio.wait_for(future, timeout)
            return result
        except asyncio.TimeoutError:
            logger.warning(f"⚠️ Timeout waiting for ACK on {ack_subject}")
            raise
        finally:
            # Usuń subskrypcję po zakończeniu
            await sub.unsubscribe()
