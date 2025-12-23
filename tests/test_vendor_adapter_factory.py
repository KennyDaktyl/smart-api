from typing import Mapping

from smart_common.providers.adapter_factory import VendorAdapterFactory
from smart_common.providers.base import BaseProviderAdapter
from smart_common.providers.enums import ProviderKind, ProviderType, ProviderVendor


class DummyAdapter(BaseProviderAdapter):
    provider_type = ProviderType.API
    vendor = ProviderVendor.HUAWEI
    kind = ProviderKind.POWER

    def __init__(
        self,
        username: str,
        password: str,
        *,
        base_url: str = "http://dummy",
        timeout: float = 1.0,
        max_retries: int = 1,
        optional: str | None = None,
    ):
        super().__init__(
            base_url,
            credentials={"username": username, "password": password},
            timeout=timeout,
            max_retries=max_retries,
        )
        self.optional = optional

    def connect(self) -> None:
        return None

    def list_stations(self) -> list[Mapping[str, object]]:
        return []

    def list_devices(self, station_code: str) -> list[Mapping[str, object]]:
        return []

    def get_current_power(self, device_id: str) -> float:
        return 0.0


def test_vendor_adapter_factory_filters_unknown_args():
    definitions = {
        ProviderVendor.HUAWEI: {
            "adapter": DummyAdapter,
            "adapter_settings": {"base_url": "https://provider", "timeout": 2.5},
        }
    }
    factory = VendorAdapterFactory(definitions)

    adapter = factory.create(
        ProviderVendor.HUAWEI,
        credentials={"username": "user", "password": "secret"},
        overrides={"timeout": 4.0, "unknown_value": 5},
    )

    assert adapter.base_url == "https://provider"
    assert adapter.timeout == 4.0
    assert adapter.optional is None
    assert not hasattr(adapter, "unknown_value")
