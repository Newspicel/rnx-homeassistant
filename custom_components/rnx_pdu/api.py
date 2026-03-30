"""API client for RNX UPDU devices."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)


class RnxPduError(Exception):
    """Base exception for RNX UPDU."""


class RnxPduConnectionError(RnxPduError):
    """Connection error."""


class RnxPduAuthError(RnxPduError):
    """Authentication error."""


class RnxPduApi:
    """Async HTTP client for the RNX UPDU API."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        session: aiohttp.ClientSession,
    ) -> None:
        self._host = host
        self._username = username
        self._password = password
        self._session = session
        self._sid: str | None = None

    @property
    def host(self) -> str:
        """Return the PDU host address."""
        return self._host

    @property
    def _base_url(self) -> str:
        return f"https://{self._host}"

    async def login(self) -> dict[str, Any]:
        """Authenticate and return the full login response including node tree."""
        try:
            resp = await self._session.post(
                f"{self._base_url}/api/login",
                json={
                    "username": self._username,
                    "password": self._password,
                    "nodes": True,
                },
                ssl=False,
            )
        except (aiohttp.ClientError, TimeoutError) as err:
            raise RnxPduConnectionError(f"Cannot connect to {self._host}") from err

        if resp.status in (401, 403):
            raise RnxPduAuthError("Invalid credentials")

        if resp.status != 200:
            raise RnxPduConnectionError(f"Unexpected status {resp.status}")

        data = await resp.json()

        session_info = data.get("session", {})
        sid = session_info.get("id")
        if not sid:
            raise RnxPduAuthError("No session ID in login response")

        self._sid = sid
        _LOGGER.debug("Logged in to RNX UPDU at %s", self._host)
        return data

    async def _request_once(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> aiohttp.ClientResponse:
        """Single authenticated request attempt."""
        kwargs: dict[str, Any] = {
            "headers": {"Cookie": f"sid={self._sid}"},
            "ssl": False,
        }
        if payload is not None:
            kwargs["json"] = payload

        try:
            resp = await self._session.request(
                method, f"{self._base_url}{path}", **kwargs
            )
        except (aiohttp.ClientError, TimeoutError) as err:
            raise RnxPduConnectionError(f"Cannot connect to {self._host}") from err

        if resp.status in (401, 403):
            self._sid = None
            raise RnxPduAuthError("Session expired")

        return resp

    async def _authenticated_request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> aiohttp.ClientResponse:
        """Request with auth, auto-re-auth on 401/403."""
        if self._sid is None:
            await self.login()

        try:
            return await self._request_once(method, path, payload)
        except RnxPduAuthError:
            _LOGGER.debug("Session expired, re-authenticating")
            await self.login()
            return await self._request_once(method, path, payload)

    async def fetch_live(self) -> dict[str, Any]:
        """Fetch live meter, relay, and environment data."""
        resp = await self._authenticated_request(
            "POST",
            "/api/live",
            {"electricity": True, "relays": True, "environment": True},
        )

        if resp.status != 200:
            raise RnxPduConnectionError(f"Unexpected status {resp.status}")

        data = await resp.json()

        if not data.get("meters") and data.get("authenticated") is False:
            self._sid = None
            raise RnxPduAuthError("Session expired")

        return data

    async def switch_relay(
        self, node_id: str, state: bool
    ) -> list[dict[str, Any]]:
        """Turn a relay on or off. Returns the full relay state list."""
        resp = await self._authenticated_request(
            "POST",
            "/api/relay/switch",
            {"relays": [{"nodeId": node_id, "state": 1 if state else 0}]},
        )
        if resp.status != 200:
            raise RnxPduConnectionError(
                f"Unexpected status {resp.status} from relay switch"
            )
        data = await resp.json()
        return data.get("relays", [])

    async def cycle_relay(self, node_id: str) -> list[dict[str, Any]]:
        """Power-cycle a relay. Returns the full relay state list."""
        resp = await self._authenticated_request(
            "POST",
            "/api/relay/switch",
            {"relays": [{"nodeId": node_id, "cycle": True}]},
        )
        if resp.status != 200:
            raise RnxPduConnectionError(
                f"Unexpected status {resp.status} from relay cycle"
            )
        data = await resp.json()
        return data.get("relays", [])

    async def reboot(self, delay_minutes: int | None = None) -> None:
        """Reboot the PDU controller, optionally after a delay in minutes."""
        payload: dict[str, Any] = {}
        if delay_minutes is not None:
            payload["delay"] = delay_minutes
        resp = await self._authenticated_request("POST", "/api/reboot", payload)
        if resp.status not in (200, 204):
            raise RnxPduConnectionError(
                f"Unexpected status {resp.status} from reboot"
            )

    async def cancel_reboot(self) -> None:
        """Cancel a scheduled reboot."""
        resp = await self._authenticated_request("POST", "/api/reboot/cancel")
        if resp.status not in (200, 204):
            raise RnxPduConnectionError(
                f"Unexpected status {resp.status} from cancel reboot"
            )

    async def fetch_info(self) -> dict[str, Any]:
        """Fetch PDU device info."""
        resp = await self._authenticated_request("GET", "/api/info")
        if resp.status != 200:
            raise RnxPduConnectionError(f"Unexpected status {resp.status}")
        return await resp.json()

    async def fetch_status(self) -> dict[str, Any]:
        """Fetch PDU status (uptime)."""
        resp = await self._authenticated_request("GET", "/api/status")
        if resp.status != 200:
            raise RnxPduConnectionError(f"Unexpected status {resp.status}")
        return await resp.json()

    async def fetch_conditions(self) -> dict[str, Any]:
        """Fetch active monitoring conditions/alarms."""
        resp = await self._authenticated_request("POST", "/api/monitoring/conditions", {})
        if resp.status != 200:
            raise RnxPduConnectionError(f"Unexpected status {resp.status}")
        return await resp.json()

    async def identify(self, node_id: str) -> None:
        """Toggle physical identification (LED blink) on a node."""
        resp = await self._authenticated_request(
            "POST", "/api/uid/toggle", {"nodeId": node_id}
        )
        if resp.status not in (200, 204):
            raise RnxPduConnectionError(
                f"Unexpected status {resp.status} from identify"
            )

    async def set_node_config(
        self, node_id: str, config: dict[str, Any]
    ) -> None:
        """Update node configuration (name, outlet settings)."""
        resp = await self._authenticated_request(
            "PUT", "/api/nodes/config", {"nodeId": node_id, "config": config}
        )
        if resp.status != 200:
            raise RnxPduConnectionError(
                f"Unexpected status {resp.status} from set_node_config"
            )

    async def fetch_settings(self) -> dict[str, Any]:
        """Fetch all device settings."""
        resp = await self._authenticated_request("GET", "/api/settings")
        if resp.status != 200:
            raise RnxPduConnectionError(f"Unexpected status {resp.status}")
        return await resp.json()

    async def set_led_brightness(self, brightness: int) -> None:
        """Set the front-panel LED brightness."""
        resp = await self._authenticated_request(
            "PUT", "/api/settings/deviceui", {"ledBrightness": brightness}
        )
        if resp.status not in (200, 204):
            raise RnxPduConnectionError(
                f"Unexpected status {resp.status} from set_led_brightness"
            )
