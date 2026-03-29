"""Button platform for RNX PDU power cycle and reboot."""

from __future__ import annotations

from homeassistant.components.button import (
    ButtonDeviceClass,
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import RnxPduConfigEntry, RnxPduCoordinator
from .entity import RnxPduEntity

POWER_CYCLE_DESCRIPTION = ButtonEntityDescription(
    key="power_cycle",
    translation_key="power_cycle",
    device_class=ButtonDeviceClass.RESTART,
)

REBOOT_DESCRIPTION = ButtonEntityDescription(
    key="reboot",
    translation_key="reboot",
    device_class=ButtonDeviceClass.RESTART,
    entity_category=EntityCategory.CONFIG,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: RnxPduConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up RNX PDU buttons."""
    coordinator = config_entry.runtime_data
    entities: list[RnxPduEntity] = []

    for outlet in coordinator.outlets:
        entities.append(
            RnxPduPowerCycleButton(
                coordinator, POWER_CYCLE_DESCRIPTION, outlet.node_id, outlet
            )
        )

    entities.append(RnxPduRebootButton(coordinator, REBOOT_DESCRIPTION, "PDU"))

    async_add_entities(entities)


class RnxPduPowerCycleButton(RnxPduEntity, ButtonEntity):
    """Button to power-cycle an outlet."""

    async def async_press(self) -> None:
        """Handle the button press."""
        raw_relays = await self.coordinator.api.cycle_relay(self.node_id)
        self.coordinator.update_relays_from_response(raw_relays)
        await self.coordinator.async_request_refresh()


class RnxPduRebootButton(RnxPduEntity, ButtonEntity):
    """Button to reboot the PDU controller."""

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.coordinator.api.reboot()
