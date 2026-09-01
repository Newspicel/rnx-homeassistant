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
from .entity import RnxPduEntity, api_errors

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
        # Outlets without a relay are metered only and cannot be switched.
        if not outlet.switchable:
            continue
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
        with api_errors(f"turn on outlet {self.node_id}"):
            await self.coordinator.api.switch_relay(self.node_id, state=True)
        await self.coordinator.async_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the outlet off."""
        with api_errors(f"turn off outlet {self.node_id}"):
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
    """Switch entity to lock/unlock an outlet.

    The device models this as an outlet mode built from three config flags:
    ``locked`` off is Manual, and when locked ``lockedOn`` selects Locked-On
    or Locked-Off (with ``allowCycle`` promoting Locked-On to Forced-On).
    """

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
        relay = (
            self.coordinator.data.relays.get(self.node_id)
            if self.coordinator.data
            else None
        )
        # Lock the outlet in the state it is in now, assuming on if unknown.
        state = relay.admin_state if relay else None
        locked_on = True if state is None else state
        with api_errors(f"lock outlet {self.node_id}"):
            await self.coordinator.async_update_outlet_config(
                self._outlet, locked=True, lockedOn=locked_on, allowCycle=False
            )
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Unlock the outlet."""
        with api_errors(f"unlock outlet {self.node_id}"):
            await self.coordinator.async_update_outlet_config(
                self._outlet, locked=False
            )
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        """Return true if the outlet is locked."""
        return self._outlet.locked
