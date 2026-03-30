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
class EnvironmentData:
    """Parsed environment sensor data for a single node."""

    temperature_c: float | None = None
    humidity_pct: float | None = None
    pressure_pa: float | None = None


@dataclass
class RcmNodeData:
    """Parsed residual current monitoring data for a single node."""

    rms_ma: float | None = None
    dc_ma: float | None = None


@dataclass
class ConditionInfo:
    """Parsed active alarm/condition."""

    condition_id: int
    condition_type: int
    severity: int
    start: int
    node_id: str
    metric: int
    threshold: int | None = None
    end: int | None = None


@dataclass
class PduDeviceInfo:
    """Static device info from /api/info."""

    product_number: str
    serial_number: str
    device_name: str
    revision: int
    icm_firmware: str


@dataclass
class OutletInfo:
    """Static info about an outlet discovered from the node tree."""

    node_id: str
    label: str
    max_current: int
    identifiable: bool = False
    locked: bool = False
    locked_on: bool = False
    allow_cycle: bool = False
    powercycle_delay: int = 0
    parent_module: ModuleInfo | None = None


@dataclass
class ModuleInfo:
    """Static info about a module discovered from the node tree."""

    node_id: str
    serial_number: str
    part_number: str
    firmware_version: str
    label: int
    identifiable: bool = False


@dataclass
class SensorNodeInfo:
    """Static info about an environment sensor node."""

    node_id: str
    aux_port: int


@dataclass
class RnxPduData:
    """Coordinator data holding all parsed live data."""

    meters: dict[str, MeterData]
    relays: dict[str, RelayData]
    environment: dict[str, EnvironmentData]
    rcms: dict[str, RcmNodeData]
    conditions: list[ConditionInfo]
    uptime_s: int | None = None


def parse_node_tree(
    nodes: list[dict[str, Any]],
) -> tuple[list[OutletInfo], list[ModuleInfo], list[SensorNodeInfo]]:
    """Walk the node tree from login and extract outlet, module, and sensor info."""
    modules: dict[str, ModuleInfo] = {}
    outlets: list[OutletInfo] = []
    sensor_nodes: list[SensorNodeInfo] = []

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
                identifiable=node.get("identifiable", False),
            )
            modules[node["nodeId"]] = info

    # Second pass: collect outlets and link to parent module
    for node in nodes:
        if node.get("type") == 7:  # Outlet
            outlet_data = node.get("outlet", {})
            outlet_config = node.get("config", {}).get("outlet", {})
            parent_id = node.get("parentId", "")
            outlets.append(
                OutletInfo(
                    node_id=node["nodeId"],
                    label=outlet_data.get("label", node["nodeId"]),
                    max_current=outlet_data.get("maxCurrent", 0),
                    identifiable=node.get("identifiable", False),
                    locked=outlet_config.get("locked", False),
                    locked_on=outlet_config.get("lockedOn", False),
                    allow_cycle=outlet_config.get("allowCycle", False),
                    powercycle_delay=outlet_config.get("powercycleDelay", 0),
                    parent_module=modules.get(parent_id),
                )
            )
        elif node.get("type") == 9:  # Sensor
            sensor_data = node.get("sensor", {})
            sensor_nodes.append(
                SensorNodeInfo(
                    node_id=node["nodeId"],
                    aux_port=sensor_data.get("auxPort", 0),
                )
            )

    return outlets, list(modules.values()), sensor_nodes


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
        sensor_nodes: list[SensorNodeInfo],
        pdu_info: PduDeviceInfo | None = None,
        led_brightness: int | None = None,
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
        self.sensor_nodes = sensor_nodes
        self.pdu_info = pdu_info
        self.led_brightness = led_brightness
        self.serial = (
            pdu_info.serial_number
            if pdu_info
            else modules[0].serial_number if modules else config_entry.entry_id
        )

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

        environment: dict[str, EnvironmentData] = {}
        for entry in raw.get("sensors", []):
            node_id = entry.get("nodeId")
            if node_id:
                environment[node_id] = EnvironmentData(
                    temperature_c=entry.get("t"),
                    humidity_pct=entry.get("rh"),
                    pressure_pa=entry.get("dp"),
                )

        rcms: dict[str, RcmNodeData] = {}
        for entry in raw.get("rcms", []):
            node_id = entry.get("nodeId")
            if node_id:
                rcms[node_id] = RcmNodeData(
                    rms_ma=entry.get("rms"),
                    dc_ma=entry.get("dc"),
                )

        # Fetch uptime (lightweight GET)
        uptime_s: int | None = None
        try:
            status = await self.api.fetch_status()
            uptime_ms = status.get("uptime")
            if uptime_ms is not None:
                uptime_s = uptime_ms // 1000
        except (RnxPduAuthError, RnxPduConnectionError):
            _LOGGER.debug("Failed to fetch uptime, skipping")

        # Fetch active conditions/alarms
        conditions: list[ConditionInfo] = []
        try:
            cond_data = await self.api.fetch_conditions()
            for entry in cond_data.get("active", []):
                conditions.append(
                    ConditionInfo(
                        condition_id=entry["id"],
                        condition_type=entry["type"],
                        severity=entry["severity"],
                        start=entry["start"],
                        node_id=entry["nodeId"],
                        metric=entry["metric"],
                        threshold=entry.get("threshold"),
                        end=entry.get("end"),
                    )
                )
        except (RnxPduAuthError, RnxPduConnectionError):
            _LOGGER.debug("Failed to fetch conditions, skipping")

        return RnxPduData(
            meters=meters,
            relays=relays,
            environment=environment,
            rcms=rcms,
            conditions=conditions,
            uptime_s=uptime_s,
        )
