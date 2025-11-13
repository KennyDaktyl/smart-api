# app/adapters/huawei_adapter.py
import json
import logging
from datetime import datetime, timedelta, timezone

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)


class HuaweiAdapter:

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.base_url = settings.HUAWEI_API_URL
        self.session = requests.Session()
        self.logged_in = False
        self.token_expiration: datetime | None = None

    def _login(self):
        url = f"{self.base_url}/login"
        payload = {"userName": self.username, "systemCode": self.password}
        headers = {"Content-Type": "application/json"}

        logger.info(f"Logging in to Huawei API as {self.username}")

        try:
            response = self.session.post(url, data=json.dumps(payload), headers=headers, timeout=10)
        except Exception as e:
            logger.error(f"Login request failed: {e}")
            raise Exception(f"Network error during Huawei login: {e}")

        if not response.ok:
            logger.error(f"Login failed: {response.status_code} {response.text}")
            raise Exception(f"Login failed: {response.status_code}")

        try:
            result = response.json()
        except Exception:
            logger.error(f"Invalid JSON in login response: {response.text}")
            raise Exception("Huawei login failed: invalid response")

        if not result.get("success", False):
            msg = result.get("message") or result.get("failCode") or "Unknown login error"
            logger.error(f"Huawei login failed: {msg}")
            raise Exception(f"Huawei login failed: {msg}")

        xsrf_token = self.session.cookies.get("XSRF-TOKEN")
        if not xsrf_token:
            logger.error(
                f"Missing XSRF-TOKEN after login, cookies: {self.session.cookies.get_dict()}"
            )
            raise Exception("Huawei login failed: no XSRF-TOKEN in cookies")

        self.session.headers.update({"XSRF-TOKEN": xsrf_token, "Content-Type": "application/json"})

        self.token_expiration = datetime.now(timezone.utc) + timedelta(minutes=25)
        self.logged_in = True

        logger.info(f"Huawei login successful. Token valid until {self.token_expiration}.")

    def _ensure_login(self):
        logger.info(f"Login status: {self.logged_in}, Token expiration: {self.token_expiration}")
        if not self.logged_in:
            logger.info("No login detected — logging in now.")
            self._login()
            return

        if self.token_expiration and datetime.now(timezone.utc) >= self.token_expiration:
            logger.info("Huawei session expired — renewing login.")
            self._login()
            return

        logger.debug("Huawei session still valid, skipping login.")

    def _post(self, endpoint: str, payload: dict | None = None) -> dict:
        self._ensure_login()

        url = f"{self.base_url}/{endpoint}"
        logger.info(f"Sending POST to {url} | Payload: {json.dumps(payload or {}, indent=2)}")

        try:
            response = self.session.post(url, data=json.dumps(payload or {}), timeout=10)
            logger.info(f"Received response: {response.status_code} | Body: {response.text}")
        except Exception as e:
            logger.error(f"Request failed: {e}")
            raise Exception(f"Network error while calling Huawei API: {e}")

        if response.status_code == 401:
            logger.warning("Huawei returned 401 Unauthorized. Re-logging in...")
            self._login()
            response = self.session.post(url, data=json.dumps(payload or {}), timeout=10)

        if not response.ok:
            raise Exception(f"Huawei API HTTP error: {response.status_code} {response.text}")

        try:
            result = response.json()
        except Exception:
            raise Exception(f"Invalid JSON response from Huawei API: {response.text}")

        if result.get("message") == "USER_MUST_RELOGIN" or result.get("failCode") == 20010:
            logger.warning(
                "Huawei session expired or invalid (USER_MUST_RELOGIN / 20010). Re-logging in..."
            )
            self._login()
            response = self.session.post(url, data=json.dumps(payload or {}), timeout=10)
            result = response.json()

        if not result.get("success", False):
            msg = result.get("message") or f"Huawei API error code: {result.get('failCode')}"
            raise Exception(f"Huawei API request failed: {msg}")

        self.token_expiration = datetime.now(timezone.utc) + timedelta(minutes=25)
        return result

    def get_stations(self) -> list[dict]:
        logger.info("Fetching Huawei station list...")
        result = self._post("getStationList")
        return result.get("data", [])

    def get_devices_for_station(self, station_code: str) -> list[dict]:
        logger.info(f"Fetching devices for station {station_code}")
        payload = {"stationCodes": station_code}
        result = self._post("getDevList", payload)
        return result.get("data", [])

    def get_production(self, device_id: str) -> dict:
        """Get real-time production."""
        payload = {"devTypeId": "1", "devIds": device_id}
        logger.debug(f"Fetching real-time data for device {device_id}")
        result = self._post("getDevRealKpi", payload)
        return result.get("data", [])
