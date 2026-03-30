"""DataUpdateCoordinator for RNX UPDU."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import RnxPduApi, RnxPduAuthError, RnxPduConnectionError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

type RnxPduConfigEntry = ConfigEntry[RnxPduCoordinator]


@dataclass
class MeterData:
    """Parsed meter data for a single node."""

    power_w: float | None = None
    reactive_power_var: float | None = None
    apparent_power_va: float | None = None
    current_a: float | None = None
    voltage_v: float | None = None
    power_factor: float | None = None
    energy_kwh: float | None = None


@dataclass
class RelayData:
    """Parsed relay data for a single outlet."""

    operational_state: bool = False
    admin_state: bool = False


@dataclass
class OutletInfo:
    """Static info about an outlet discovered from the node tree."""

    node_id: str
    label: str
    max_current: int
    parent_module: ModuleInfo | None = None


@dataclass
class ModuleInfo:
    """Static info about a module discovered from the node tree."""

    node_id: str
    serial_number: str
    part_number: str
    firmware_version: str
    label: int


@dataclass
class RnxPduData:
    """Coordinator data holding all parsed live data."""

    meters: dict[str, MeterData]
    relays: dict[str, RelayData]


def parse_node_tree(nodes: list[dict[str, Any]]) -> tuple[list[OutletInfo], list[ModuleInfo]]:
    """Walk the node tree from login and extract outlet and module info."""
    modules: dict[str, ModuleInfo] = {}
    outlets: list[OutletInfo] = []

    # First pass: collect modules
    for node in nodes:
        if node.get("type") == 5:  # Module
            pom = node.get("pom", {})
            fw = pom.get("runningFirmware", {})
            info = ModuleInfo(
                node_id=node["nodeId"],
                serial_number=pom.get("serialNumber", ""),
                part_number=pom.get("partNumber", ""),
                firmware_version=fw.get("version", ""),
                label=pom.get("label", 0),
            )
            modules[node["nodeId"]] = info

    # Second pass: collect outlets and link to parent module
    for node in nodes:
        if node.get("type") == 7:  # Outlet
            outlet_data = node.get("outlet", {})
            parent_id = node.get("parentId", "")
            outlets.append(
                OutletInfo(
                    node_id=node["nodeId"],
                    label=outlet_data.get("label", node["nodeId"]),
                    max_current=outlet_data.get("maxCurrent", 0),
                    parent_module=modules.get(parent_id),
                )
            )

    return outlets, list(modules.values())


def _parse_meter(raw: dict[str, Any]) -> MeterData:
    """Parse a single meter entry from the API response."""
    power = raw.get("power", {})
    energy = raw.get("energy", {})
    return MeterData(
        power_w=power.get("p"),
        reactive_power_var=power.get("q"),
        apparent_power_va=power.get("s"),
        current_a=power.get("irms"),
        voltage_v=power.get("vrms"),
        power_factor=power.get("pf"),
        energy_kwh=energy.get("eActPos"),
    )


class RnxPduCoordinator(DataUpdateCoordinator[RnxPduData]):
    """Coordinator that polls the RNX UPDU for live data."""

    config_entry: RnxPduConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: RnxPduConfigEntry,
        api: RnxPduApi,
        outlets: list[OutletInfo],
        modules: list[ModuleInfo],
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.api = api
        self.outlets = outlets
        self.modules = modules
        self.serial = modules[0].serial_number if modules else config_entry.entry_id

    async def _async_update_data(self) -> RnxPduData:
        """Fetch live data from the PDU."""
        try:
            raw = await self.api.fetch_live()
        except RnxPduAuthError as err:
            raise ConfigEntryAuthFailed from err
        except RnxPduConnectionError as err:
            raise UpdateFailed(f"Error communicating with PDU: {err}") from err

        meters: dict[str, MeterData] = {}
        for entry in raw.get("meters", []):
            node_id = entry.get("nodeId")
            if node_id:
                meters[node_id] = _parse_meter(entry)

        relays: dict[str, RelayData] = {}
        for entry in raw.get("relays", []):
            node_id = entry.get("nodeId")
            if node_id:
                relays[node_id] = RelayData(
                    operational_state=entry.get("operationalState") == 1,
                    admin_state=entry.get("adminState") == 1,
                )

        return RnxPduData(meters=meters, relays=relays)
