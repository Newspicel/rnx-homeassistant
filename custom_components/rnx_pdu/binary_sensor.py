"""Binary sensor platform for RNX PDU relay states."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import RnxPduConfigEntry, RnxPduCoordinator
from .entity import RnxPduEntity

RELAY_DESCRIPTION = BinarySensorEntityDescription(
    key="relay_state",
    translation_key="relay_state",
    device_class=BinarySensorDeviceClass.POWER,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: RnxPduConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up RNX PDU relay binary sensors."""
    coordinator = config_entry.runtime_data
    entities: list[RnxPduRelaySensor] = []

    for outlet in coordinator.outlets:
        entities.append(
            RnxPduRelaySensor(coordinator, RELAY_DESCRIPTION, outlet.node_id, outlet)
        )

    async_add_entities(entities)


class RnxPduRelaySensor(RnxPduEntity, BinarySensorEntity):
    """Binary sensor for an RNX PDU outlet relay state."""

    @property
    def is_on(self) -> bool | None:
        """Return true if the relay is on."""
        if self.coordinator.data is None:
            return None
        relay = self.coordinator.data.relays.get(self.node_id)
        if relay is None:
            return None
        return relay.operational_state
