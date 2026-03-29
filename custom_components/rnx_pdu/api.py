"""API client for RNX PDU devices."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)


class RnxPduError(Exception):
    """Base exception for RNX PDU."""


class RnxPduConnectionError(RnxPduError):
    """Connection error."""


class RnxPduAuthError(RnxPduError):
    """Authentication error."""


class RnxPduApi:
    """Async HTTP client for the RNX PDU API."""

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
        _LOGGER.debug("Logged in to RNX PDU at %s", self._host)
        return data

    async def fetch_live(self) -> dict[str, Any]:
        """Fetch live meter and relay data. Re-authenticates on session expiry."""
        if self._sid is None:
            await self.login()

        try:
            data = await self._fetch_live_once()
        except RnxPduAuthError:
            _LOGGER.debug("Session expired, re-authenticating")
            await self.login()
            data = await self._fetch_live_once()

        return data

    async def _fetch_live_once(self) -> dict[str, Any]:
        """Single attempt to fetch /api/live."""
        try:
            resp = await self._session.post(
                f"{self._base_url}/api/live",
                json={"electricity": True, "relays": True},
                headers={"Cookie": f"sid={self._sid}"},
                ssl=False,
            )
        except (aiohttp.ClientError, TimeoutError) as err:
            raise RnxPduConnectionError(f"Cannot connect to {self._host}") from err

        if resp.status in (401, 403):
            self._sid = None
            raise RnxPduAuthError("Session expired")

        if resp.status != 200:
            raise RnxPduConnectionError(f"Unexpected status {resp.status}")

        data = await resp.json()

        if not data.get("meters") and data.get("authenticated") is False:
            self._sid = None
            raise RnxPduAuthError("Session expired")

        return data
