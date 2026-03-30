"""Switch platform for RNX UPDU outlet relays and outlet lock."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import OutletInfo, RnxPduConfigEntry, RnxPduCoordinator
from .entity import RnxPduEntity

SWITCH_DESCRIPTION = SwitchEntityDescription(
    key="outlet_switch",
    translation_key="outlet_switch",
    device_class=SwitchDeviceClass.OUTLET,
)

LOCK_DESCRIPTION = SwitchEntityDescription(
    key="outlet_lock",
    translation_key="outlet_lock",
    entity_category=EntityCategory.CONFIG,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: RnxPduConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up RNX UPDU outlet switches."""
    coordinator = config_entry.runtime_data
    entities: list[SwitchEntity] = []

    for outlet in coordinator.outlets:
        entities.append(
            RnxPduSwitch(coordinator, SWITCH_DESCRIPTION, outlet.node_id, outlet)
        )
        entities.append(
            RnxPduLockSwitch(coordinator, LOCK_DESCRIPTION, outlet.node_id, outlet)
        )

    async_add_entities(entities)


class RnxPduSwitch(RnxPduEntity, SwitchEntity):
    """Switch entity for an RNX UPDU outlet relay."""

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the outlet on."""
        await self.coordinator.api.switch_relay(self.node_id, state=True)
        await self.coordinator.async_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the outlet off."""
        await self.coordinator.api.switch_relay(self.node_id, state=False)
        await self.coordinator.async_refresh()

    @property
    def is_on(self) -> bool | None:
        """Return true if the outlet relay is on."""
        if self.coordinator.data is None:
            return None
        relay = self.coordinator.data.relays.get(self.node_id)
        if relay is None:
            return None
        return relay.admin_state


class RnxPduLockSwitch(RnxPduEntity, SwitchEntity):
    """Switch entity to lock/unlock an outlet."""

    _outlet: OutletInfo

    def __init__(
        self,
        coordinator: RnxPduCoordinator,
        description: SwitchEntityDescription,
        node_id: str,
        outlet: OutletInfo,
    ) -> None:
        super().__init__(coordinator, description, node_id, outlet)
        self._outlet = outlet

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Lock the outlet in its current state."""
        relay = self.coordinator.data.relays.get(self.node_id) if self.coordinator.data else None
        locked_on = relay.admin_state if relay else True
        await self.coordinator.api.set_node_config(
            self.node_id, {"outlet": {"locked": True, "lockedOn": locked_on}}
        )
        self._outlet.locked = True
        self._outlet.locked_on = locked_on
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Unlock the outlet."""
        await self.coordinator.api.set_node_config(
            self.node_id, {"outlet": {"locked": False}}
        )
        self._outlet.locked = False
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        """Return true if the outlet is locked."""
        return self._outlet.locked
