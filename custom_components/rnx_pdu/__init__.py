"""The RNX UPDU integration."""

from __future__ import annotations

import logging

from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import RnxPduApi, RnxPduAuthError, RnxPduConnectionError
from .coordinator import (
    PduDeviceInfo,
    RnxPduConfigEntry,
    RnxPduCoordinator,
    parse_node_tree,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.BUTTON,
    Platform.NUMBER,
]


async def async_setup_entry(
    hass, entry: RnxPduConfigEntry
) -> bool:
    """Set up RNX UPDU from a config entry."""
    session = async_get_clientsession(hass, verify_ssl=False)
    api = RnxPduApi(
        entry.data[CONF_HOST],
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        session,
    )

    try:
        data = await api.login()
    except RnxPduAuthError as err:
        raise ConfigEntryAuthFailed from err
    except RnxPduConnectionError as err:
        raise ConfigEntryNotReady from err

    outlets, modules, sensor_nodes = parse_node_tree(data.get("nodes", []))

    # Fetch device info for richer device registry entries
    pdu_info: PduDeviceInfo | None = None
    try:
        info = await api.fetch_info()
        icm = info.get("icm", {})
        pdu_info = PduDeviceInfo(
            product_number=info.get("productNumber", ""),
            serial_number=info.get("serialNumber", ""),
            device_name=info.get("deviceName", ""),
            revision=info.get("revision", 0),
            icm_firmware=icm.get("runningFirmware", {}).get("version", ""),
        )
    except (RnxPduConnectionError, RnxPduAuthError):
        _LOGGER.debug("Could not fetch device info, using defaults")

    # Fetch initial LED brightness
    led_brightness: int | None = None
    try:
        settings = await api.fetch_settings()
        led_brightness = settings.get("deviceUi", {}).get("ledBrightness")
    except (RnxPduConnectionError, RnxPduAuthError):
        _LOGGER.debug("Could not fetch settings")

    coordinator = RnxPduCoordinator(
        hass, entry, api, outlets, modules, sensor_nodes, pdu_info, led_brightness
    )
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass, entry: RnxPduConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
