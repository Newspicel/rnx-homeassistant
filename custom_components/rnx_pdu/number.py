"""Number platform for RNX UPDU LED brightness and power cycle delay."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import OutletInfo, RnxPduConfigEntry, RnxPduCoordinator
from .entity import RnxPduEntity

LED_BRIGHTNESS_DESCRIPTION = NumberEntityDescription(
    key="led_brightness",
    translation_key="led_brightness",
    entity_category=EntityCategory.CONFIG,
    native_min_value=0,
    native_max_value=4,
    native_step=1,
)

POWERCYCLE_DELAY_DESCRIPTION = NumberEntityDescription(
    key="powercycle_delay",
    translation_key="powercycle_delay",
    entity_category=EntityCategory.CONFIG,
    native_min_value=0,
    native_max_value=900,
    native_step=1,
    native_unit_of_measurement="s",
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: RnxPduConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up RNX UPDU number entities."""
    coordinator = config_entry.runtime_data
    entities: list[NumberEntity] = []

    # PDU-level LED brightness
    if coordinator.led_brightness is not None:
        entities.append(
            RnxPduLedBrightnessNumber(
                coordinator, LED_BRIGHTNESS_DESCRIPTION, "PDU"
            )
        )

    # Per-outlet power cycle delay
    for outlet in coordinator.outlets:
        entities.append(
            RnxPduPowercycleDelayNumber(
                coordinator, POWERCYCLE_DELAY_DESCRIPTION, outlet.node_id, outlet
            )
        )

    async_add_entities(entities)


class RnxPduLedBrightnessNumber(RnxPduEntity, NumberEntity):
    """Number entity for front-panel LED brightness."""

    @property
    def native_value(self) -> float | None:
        """Return current LED brightness."""
        return self.coordinator.led_brightness

    async def async_set_native_value(self, value: float) -> None:
        """Set LED brightness."""
        brightness = int(value)
        await self.coordinator.api.set_led_brightness(brightness)
        self.coordinator.led_brightness = brightness
        self.async_write_ha_state()


class RnxPduPowercycleDelayNumber(RnxPduEntity, NumberEntity):
    """Number entity for outlet power cycle delay in seconds."""

    _outlet: OutletInfo

    def __init__(
        self,
        coordinator: RnxPduCoordinator,
        description: NumberEntityDescription,
        node_id: str,
        outlet: OutletInfo,
    ) -> None:
        super().__init__(coordinator, description, node_id, outlet)
        self._outlet = outlet

    @property
    def native_value(self) -> float | None:
        """Return current power cycle delay."""
        return self._outlet.powercycle_delay

    async def async_set_native_value(self, value: float) -> None:
        """Set power cycle delay."""
        delay = int(value)
        await self.coordinator.api.set_node_config(
            self.node_id, {"outlet": {"powercycleDelay": delay}}
        )
        self._outlet.powercycle_delay = delay
        self.async_write_ha_state()
