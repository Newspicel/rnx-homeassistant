"""Number platform for RNX UPDU LED brightness and power cycle delay."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    POWERCYCLE_DELAY_MAX,
    POWERCYCLE_DELAY_MIN,
    LedBrightness,
)
from .coordinator import OutletInfo, RnxPduConfigEntry, RnxPduCoordinator
from .entity import RnxPduEntity, api_errors

LED_BRIGHTNESS_DESCRIPTION = NumberEntityDescription(
    key="led_brightness",
    translation_key="led_brightness",
    entity_category=EntityCategory.CONFIG,
    native_min_value=int(min(LedBrightness)),
    native_max_value=int(max(LedBrightness)),
    native_step=1,
)

POWERCYCLE_DELAY_DESCRIPTION = NumberEntityDescription(
    key="powercycle_delay",
    translation_key="powercycle_delay",
    entity_category=EntityCategory.CONFIG,
    native_min_value=POWERCYCLE_DELAY_MIN,
    native_max_value=POWERCYCLE_DELAY_MAX,
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

    # Per-outlet power cycle delay (only meaningful for switched outlets)
    for outlet in coordinator.outlets:
        if not outlet.switchable:
            continue
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
        with api_errors("set LED brightness"):
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
        with api_errors(f"set power cycle delay on {self.node_id}"):
            await self.coordinator.async_update_outlet_config(
                self._outlet, powercycleDelay=delay
            )
        self.async_write_ha_state()
