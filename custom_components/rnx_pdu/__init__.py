"""The RNX PDU integration."""

from __future__ import annotations

from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import RnxPduApi, RnxPduAuthError, RnxPduConnectionError
from .coordinator import RnxPduConfigEntry, RnxPduCoordinator, parse_node_tree

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.SWITCH, Platform.BUTTON]


async def async_setup_entry(
    hass, entry: RnxPduConfigEntry
) -> bool:
    """Set up RNX PDU from a config entry."""
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

    outlets, modules = parse_node_tree(data.get("nodes", []))
    coordinator = RnxPduCoordinator(hass, entry, api, outlets, modules)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass, entry: RnxPduConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
