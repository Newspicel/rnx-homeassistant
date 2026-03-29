"""Switch platform for RNX PDU outlet relays."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import RnxPduConfigEntry, RnxPduCoordinator
from .entity import RnxPduEntity

SWITCH_DESCRIPTION = SwitchEntityDescription(
    key="outlet_switch",
    translation_key="outlet_switch",
    device_class=SwitchDeviceClass.OUTLET,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: RnxPduConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up RNX PDU outlet switches."""
    coordinator = config_entry.runtime_data
    async_add_entities(
        RnxPduSwitch(coordinator, SWITCH_DESCRIPTION, outlet.node_id, outlet)
        for outlet in coordinator.outlets
    )


class RnxPduSwitch(RnxPduEntity, SwitchEntity):
    """Switch entity for an RNX PDU outlet relay."""

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the outlet on."""
        raw_relays = await self.coordinator.api.switch_relay(self.node_id, state=True)
        self.coordinator.update_relays_from_response(raw_relays)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the outlet off."""
        raw_relays = await self.coordinator.api.switch_relay(self.node_id, state=False)
        self.coordinator.update_relays_from_response(raw_relays)
        await self.coordinator.async_request_refresh()

    @property
    def is_on(self) -> bool | None:
        """Return true if the outlet relay is on."""
        if self.coordinator.data is None:
            return None
        relay = self.coordinator.data.relays.get(self.node_id)
        if relay is None:
            return None
        return relay.admin_state
