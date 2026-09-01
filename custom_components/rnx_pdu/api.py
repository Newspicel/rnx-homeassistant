"""API client for RNX UPDU devices.

Targets the UPDU Web API (BETA) as documented at ``/apidocs-beta`` on the
device (OpenAPI schema at ``/openapi.json``), firmware 4.4.0.
"""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .const import RelayState

_LOGGER = logging.getLogger(__name__)


class RnxPduError(Exception):
    """Base exception for RNX UPDU."""


class RnxPduConnectionError(RnxPduError):
    """Connection error."""


class RnxPduAuthError(RnxPduError):
    """Authentication error."""


class RnxPduCommandError(RnxPduError):
    """The device accepted the request but rejected the command."""


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

    async def logout(self) -> None:
        """Release the session on the device. Errors are non-fatal."""
        if self._sid is None:
            return
        try:
            await self._request_once("POST", "/api/logout")
        except RnxPduError as err:
            _LOGGER.debug("Logout failed: %s", err)
        finally:
            self._sid = None

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

    async def _request_json(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Perform a request expected to return a JSON body."""
        resp = await self._authenticated_request(method, path, payload)
        if resp.status != 200:
            raise RnxPduConnectionError(f"Unexpected status {resp.status} from {path}")
        return await resp.json()

    async def _request_no_content(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        """Perform a request whose success is signalled by the status alone."""
        resp = await self._authenticated_request(method, path, payload)
        if resp.status not in (200, 204):
            raise RnxPduConnectionError(f"Unexpected status {resp.status} from {path}")

    async def fetch_live(self) -> dict[str, Any]:
        """Fetch live meter, relay, and environment data."""
        return await self._request_json(
            "POST",
            "/api/live",
            {"electricity": True, "relays": True, "environment": True},
        )

    async def fetch_nodes(self) -> list[dict[str, Any]]:
        """Fetch the wiring tree."""
        data = await self._request_json("GET", "/api/nodes")
        return data.get("nodes", [])

    async def switch_relay(self, node_id: str, state: bool) -> list[dict[str, Any]]:
        """Turn a relay on or off. Returns the full relay state list."""
        data = await self._request_json(
            "POST",
            "/api/relay/switch",
            {
                "relays": [
                    {
                        "nodeId": node_id,
                        "state": RelayState.ON if state else RelayState.OFF,
                    }
                ]
            },
        )
        return data.get("relays", [])

    async def cycle_relay(self, node_id: str) -> list[dict[str, Any]]:
        """Power-cycle a relay. Returns the full relay state list."""
        data = await self._request_json(
            "POST",
            "/api/relay/switch",
            {"relays": [{"nodeId": node_id, "cycle": True}]},
        )
        return data.get("relays", [])

    async def reboot(self, delay_minutes: int | None = None) -> None:
        """Reboot the PDU controller, optionally after a delay in minutes."""
        payload: dict[str, Any] = {}
        if delay_minutes is not None:
            payload["delay"] = delay_minutes
        await self._request_no_content("POST", "/api/reboot", payload)

    async def cancel_reboot(self) -> None:
        """Cancel a scheduled reboot."""
        await self._request_no_content("POST", "/api/reboot/cancel")

    async def fetch_info(self) -> dict[str, Any]:
        """Fetch PDU device info."""
        return await self._request_json("GET", "/api/info")

    async def fetch_status(self) -> dict[str, Any]:
        """Fetch PDU status (uptime)."""
        return await self._request_json("GET", "/api/status")

    async def fetch_features(self) -> int:
        """Fetch the device feature flags bitfield."""
        data = await self._request_json("GET", "/api/features")
        return data.get("features", 0)

    async def fetch_conditions(
        self, if_changed_since: int | None = None
    ) -> dict[str, Any]:
        """Fetch monitoring conditions.

        The endpoint is a delta protocol: when ``ifChangedSince`` matches the
        device's current change timestamp it replies ``{"changed": false}``
        with no condition lists, and the caller must keep its previous state.
        """
        payload: dict[str, Any] = {}
        if if_changed_since is not None:
            payload["ifChangedSince"] = if_changed_since
        return await self._request_json("POST", "/api/monitoring/conditions", payload)

    async def identify(self, node_id: str) -> None:
        """Toggle physical identification (LED blink) on a node."""
        await self._request_no_content("POST", "/api/uid/toggle", {"nodeId": node_id})

    async def set_node_config(self, node_id: str, config: dict[str, Any]) -> None:
        """Write a complete node configuration object.

        ``config`` must be the full ``NodeConfig`` — the device rejects partial
        objects with HTTP 200 and ``success: false``, so prefer
        :meth:`update_outlet_config` which merges into the current config.
        """
        data = await self._request_json(
            "PUT", "/api/nodes/config", {"nodeId": node_id, "config": config}
        )
        if not data.get("success"):
            error = data.get("error") or {}
            message = error.get("message") or "Device rejected the configuration"
            raise RnxPduCommandError(f"{message} (node {node_id})")

    async def update_outlet_config(
        self, node_id: str, **overrides: Any
    ) -> dict[str, Any]:
        """Merge ``overrides`` into an outlet's config and write it back.

        Reading the current config first keeps fields this integration does not
        expose -- including the ``sequencingPowerOnOrder`` "excluded" sentinel
        (127) and the ``sequencingPowerOnDelay`` "use default" sentinel (65535)
        -- at whatever the device web UI set them to.

        Returns the outlet settings that were written.
        """
        nodes = await self.fetch_nodes()
        node = next((n for n in nodes if n.get("nodeId") == node_id), None)
        if node is None:
            raise RnxPduCommandError(f"Unknown node {node_id}")

        current = node.get("config") or {}
        outlet = dict(current.get("outlet") or {})
        outlet.update(overrides)

        config = {
            "name": current.get("name", ""),
            "description": current.get("description", ""),
            "outlet": outlet,
        }
        await self.set_node_config(node_id, config)
        return outlet

    async def fetch_settings(self) -> dict[str, Any]:
        """Fetch all device settings."""
        return await self._request_json("GET", "/api/settings")

    async def set_led_brightness(self, brightness: int) -> None:
        """Set the front-panel LED brightness.

        Applied immediately but not persisted across reboots; the device web UI
        likewise leaves persisting to an explicit "save active configuration".
        """
        await self._request_no_content(
            "PUT", "/api/settings/deviceui", {"ledBrightness": brightness}
        )
