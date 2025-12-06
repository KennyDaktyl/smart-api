from types import SimpleNamespace
from typing import Any, Dict, List, Optional


class FakeHuaweiAdapter:
    """Lightweight Huawei adapter mock that returns predefined power readings."""

    def __init__(self, power_map: Optional[Dict[str, Optional[float]]] = None):
        self.power_map = power_map or {}
        self.login_calls = 0
        self.logged_in = False

    def _login(self):
        self.login_calls += 1
        self.logged_in = True
        return {"success": True}

    def get_production(self, device_id: str) -> List[Dict[str, Any]]:
        if not self.logged_in:
            self._login()
        return [{"dataItemMap": {"active_power": self.power_map.get(device_id)}}]

    def set_power(self, device_id: str, active_power: Optional[float]):
        self.power_map[device_id] = active_power


class FakeEventDispatcher:
    def __init__(self):
        self.published: list[dict[str, Any]] = []

    async def publish_event(self, subject: str, event: Any):
        self.published.append({"subject": subject, "event": event})


class FakeNatsClient:
    def __init__(self):
        self.connected = False
        self.js = SimpleNamespace()

    async def connect(self):
        self.connected = True

    async def close(self):
        self.connected = False


class FakeNatsModule:
    def __init__(self):
        self.client = FakeNatsClient()
        self.events = FakeEventDispatcher()
        self.ensure_stream_called = False

    async def ensure_stream(self):
        self.ensure_stream_called = True


POWER_NONE = [{"dataItemMap": {"active_power": None}}]
POWER_2KW = [{"dataItemMap": {"active_power": 2000.0}}]
POWER_5KW = [{"dataItemMap": {"active_power": 5000.0}}]


class FakePublisher:
    """Minimal NATS publisher double supporting ACKs and failure injection."""

    def __init__(self):
        self.published = []
        self.next_ack = None
        self.raise_exc: Exception | None = None

    def set_ack(self, ack: dict):
        self.next_ack = ack

    def set_exception(self, exc: Exception):
        self.raise_exc = exc

    async def publish(self, subject: str, payload: dict, retries: int = 3):
        self.published.append({"subject": subject, "payload": payload, "retries": retries})
        if self.raise_exc:
            raise self.raise_exc
        return {"ok": True}

    async def publish_and_wait_for_ack(
        self,
        subject: str,
        ack_subject: str,
        message: dict,
        predicate,
        timeout: float = 3.0,
    ) -> dict:
        self.published.append(
            {
                "subject": subject,
                "ack_subject": ack_subject,
                "message": message,
                "timeout": timeout,
            }
        )

        if self.raise_exc:
            raise self.raise_exc

        ack = self.next_ack or {"ok": True, "device_id": message.get("payload", {}).get("device_id")}

        # Ensure predicate compatibility: if predicate matches, return ack; otherwise still return
        # whatever we have to mimic agent behavior.
        try:
            predicate(ack)
        except Exception:
            # If predicate raises, just pass; we want the caller to deal with the contents.
            pass

        return ack
