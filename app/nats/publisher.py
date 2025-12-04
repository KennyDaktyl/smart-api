# app/core/nats/publisher.py
import asyncio
import json
import logging
from typing import Any, Callable, Dict

from app.nats.client import NatsClient

logger = logging.getLogger(__name__)


class NatsPublisher:
    def __init__(self, client: NatsClient):
        self.client = client

    async def publish(self, subject: str, payload: Dict[str, Any], retries=3):
        data = json.dumps(payload).encode("utf-8")

        for attempt in range(1, retries + 1):
            try:
                await self.client.connect()

                if not self.client.js:
                    raise RuntimeError("JetStream not initialized")

                ack = await self.client.js.publish(
                    subject=subject,
                    payload=data,
                    timeout=5.0,
                )

                logger.info(f"[NATS] Published {subject}, seq={ack.seq}")

                await self.client.nc.drain()
                await self.client.nc.close()

                return ack

            except Exception as e:
                logger.error(f"[NATS] Publish failed (attempt {attempt}/{retries}): {e}")
                await asyncio.sleep(0.5 * attempt)

        raise Exception(f"NATS publish failed after {retries} attempts")

    async def publish_and_wait_for_ack(
        self,
        subject: str,
        ack_subject: str,
        message: dict,
        predicate: Callable[[dict], bool],
        timeout: float = 3.0,
    ) -> dict:
        await self.client.ensure_connected()

        js = self.client.js
        if not js:
            raise RuntimeError("JetStream not initialized")

        data = json.dumps(message).encode("utf-8")
        future = asyncio.get_event_loop().create_future()

        async def ack_handler(msg):
            try:
                payload = json.loads(msg.data.decode())

                if predicate(payload):
                    if not future.done():
                        future.set_result(payload)

            except Exception as e:
                if not future.done():
                    future.set_exception(e)

        sub = await self.client.nc.subscribe(ack_subject, cb=ack_handler)

        await js.publish(subject=subject, payload=data)

        try:
            result = await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            raise Exception("Timeout waiting for ACK")
        finally:
            await sub.unsubscribe()

        return result
