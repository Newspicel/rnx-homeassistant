"""Binary sensor platform for RNX UPDU relay states and alarms."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import RnxPduConfigEntry, RnxPduCoordinator
from .entity import RnxPduEntity

RELAY_DESCRIPTION = BinarySensorEntityDescription(
    key="relay_state",
    translation_key="relay_state",
    device_class=BinarySensorDeviceClass.POWER,
)

ALARM_DESCRIPTION = BinarySensorEntityDescription(
    key="alarm",
    translation_key="alarm",
    device_class=BinarySensorDeviceClass.PROBLEM,
    entity_category=EntityCategory.DIAGNOSTIC,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: RnxPduConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up RNX UPDU binary sensors."""
    coordinator = config_entry.runtime_data
    entities: list[BinarySensorEntity] = []

    for outlet in coordinator.outlets:
        entities.append(
            RnxPduRelaySensor(coordinator, RELAY_DESCRIPTION, outlet.node_id, outlet)
        )
        # Alarm per outlet
        entities.append(
            RnxPduAlarmSensor(coordinator, ALARM_DESCRIPTION, outlet.node_id, outlet)
        )

    # PDU-level alarm
    entities.append(RnxPduAlarmSensor(coordinator, ALARM_DESCRIPTION, "PDU"))

    async_add_entities(entities)


class RnxPduRelaySensor(RnxPduEntity, BinarySensorEntity):
    """Binary sensor for an RNX UPDU outlet relay state."""

    @property
    def is_on(self) -> bool | None:
        """Return true if the relay is on."""
        if self.coordinator.data is None:
            return None
        relay = self.coordinator.data.relays.get(self.node_id)
        if relay is None:
            return None
        return relay.operational_state


class RnxPduAlarmSensor(RnxPduEntity, BinarySensorEntity):
    """Binary sensor for active alarms/conditions on a node."""

    @property
    def is_on(self) -> bool | None:
        """Return true if any alarm condition is active for this node."""
        if self.coordinator.data is None:
            return None
        return any(
            c.node_id == self.node_id for c in self.coordinator.data.conditions
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return alarm condition details."""
        if self.coordinator.data is None:
            return None
        active = [
            c for c in self.coordinator.data.conditions if c.node_id == self.node_id
        ]
        if not active:
            return None
        return {
            "active_conditions": [
                {
                    "severity": c.severity,
                    "metric": c.metric,
                    "threshold": c.threshold,
                }
                for c in active
            ],
        }
