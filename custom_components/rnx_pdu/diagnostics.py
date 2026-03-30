"""Diagnostics support for RNX UPDU."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

from .api import RnxPduConnectionError
from .coordinator import RnxPduConfigEntry

_LOGGER = logging.getLogger(__name__)

TO_REDACT = {CONF_PASSWORD, CONF_USERNAME}


async def async_get_config_entry_diagnostics(
    hass, entry: RnxPduConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    diag: dict[str, Any] = {
        "config_entry": async_redact_data(dict(entry.data), TO_REDACT),
    }

    if coordinator.pdu_info:
        diag["device_info"] = {
            "product_number": coordinator.pdu_info.product_number,
            "serial_number": coordinator.pdu_info.serial_number,
            "device_name": coordinator.pdu_info.device_name,
            "revision": coordinator.pdu_info.revision,
            "icm_firmware": coordinator.pdu_info.icm_firmware,
        }

    try:
        diag["raw_info"] = await coordinator.api.fetch_info()
    except RnxPduConnectionError:
        _LOGGER.debug("Could not fetch /api/info for diagnostics")

    try:
        diag["raw_status"] = await coordinator.api.fetch_status()
    except RnxPduConnectionError:
        _LOGGER.debug("Could not fetch /api/status for diagnostics")

    diag["outlets"] = [
        {
            "node_id": o.node_id,
            "label": o.label,
            "max_current": o.max_current,
            "locked": o.locked,
            "powercycle_delay": o.powercycle_delay,
        }
        for o in coordinator.outlets
    ]

    diag["modules"] = [
        {
            "node_id": m.node_id,
            "serial_number": m.serial_number,
            "part_number": m.part_number,
            "firmware_version": m.firmware_version,
        }
        for m in coordinator.modules
    ]

    diag["sensor_nodes"] = [
        {"node_id": s.node_id, "aux_port": s.aux_port}
        for s in coordinator.sensor_nodes
    ]

    return diag
