"""Button platform for RNX UPDU power cycle, reboot, and identify."""

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

CANCEL_REBOOT_DESCRIPTION = ButtonEntityDescription(
    key="cancel_reboot",
    translation_key="cancel_reboot",
    entity_category=EntityCategory.CONFIG,
)

IDENTIFY_DESCRIPTION = ButtonEntityDescription(
    key="identify",
    translation_key="identify",
    entity_category=EntityCategory.CONFIG,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: RnxPduConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up RNX UPDU buttons."""
    coordinator = config_entry.runtime_data
    entities: list[ButtonEntity] = []

    for outlet in coordinator.outlets:
        entities.append(
            RnxPduPowerCycleButton(
                coordinator, POWER_CYCLE_DESCRIPTION, outlet.node_id, outlet
            )
        )
        if outlet.identifiable:
            entities.append(
                RnxPduIdentifyButton(
                    coordinator, IDENTIFY_DESCRIPTION, outlet.node_id, outlet
                )
            )

    # PDU-level buttons
    entities.append(RnxPduRebootButton(coordinator, REBOOT_DESCRIPTION, "PDU"))
    entities.append(
        RnxPduCancelRebootButton(coordinator, CANCEL_REBOOT_DESCRIPTION, "PDU")
    )

    # Module-level identify buttons
    for module in coordinator.modules:
        if module.identifiable:
            entities.append(
                RnxPduIdentifyButton(
                    coordinator, IDENTIFY_DESCRIPTION, module.node_id
                )
            )

    async_add_entities(entities)


class RnxPduPowerCycleButton(RnxPduEntity, ButtonEntity):
    """Button to power-cycle an outlet."""

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.coordinator.api.cycle_relay(self.node_id)
        await self.coordinator.async_refresh()


class RnxPduRebootButton(RnxPduEntity, ButtonEntity):
    """Button to reboot the PDU controller."""

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.coordinator.api.reboot()


class RnxPduCancelRebootButton(RnxPduEntity, ButtonEntity):
    """Button to cancel a scheduled reboot."""

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.coordinator.api.cancel_reboot()


class RnxPduIdentifyButton(RnxPduEntity, ButtonEntity):
    """Button to toggle physical identification (LED blink) on a node."""

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.coordinator.api.identify(self.node_id)
