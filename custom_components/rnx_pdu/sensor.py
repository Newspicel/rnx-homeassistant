"""Sensor platform for RNX UPDU."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfApparentPower,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import MeterData, RnxPduConfigEntry, RnxPduCoordinator
from .entity import RnxPduEntity


@dataclass(frozen=True, kw_only=True)
class RnxPduSensorEntityDescription(SensorEntityDescription):
    """Describes an RNX UPDU sensor."""

    value_fn: Callable[[MeterData], float | None]


SENSOR_DESCRIPTIONS: tuple[RnxPduSensorEntityDescription, ...] = (
    RnxPduSensorEntityDescription(
        key="power",
        translation_key="power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=1,
        value_fn=lambda m: m.power_w,
    ),
    RnxPduSensorEntityDescription(
        key="current",
        translation_key="current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=3,
        value_fn=lambda m: m.current_a,
    ),
    RnxPduSensorEntityDescription(
        key="voltage",
        translation_key="voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        suggested_display_precision=1,
        value_fn=lambda m: m.voltage_v,
    ),
    RnxPduSensorEntityDescription(
        key="energy",
        translation_key="energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=3,
        value_fn=lambda m: m.energy_kwh,
    ),
    RnxPduSensorEntityDescription(
        key="power_factor",
        translation_key="power_factor",
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=lambda m: m.power_factor,
    ),
    RnxPduSensorEntityDescription(
        key="apparent_power",
        translation_key="apparent_power",
        device_class=SensorDeviceClass.APPARENT_POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfApparentPower.VOLT_AMPERE,
        suggested_display_precision=1,
        value_fn=lambda m: m.apparent_power_va,
    ),
    RnxPduSensorEntityDescription(
        key="reactive_power",
        translation_key="reactive_power",
        device_class=SensorDeviceClass.REACTIVE_POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="var",
        suggested_display_precision=1,
        value_fn=lambda m: m.reactive_power_var,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: RnxPduConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up RNX UPDU sensors."""
    coordinator = config_entry.runtime_data
    entities: list[RnxPduSensor] = []

    # PDU-level sensors
    for desc in SENSOR_DESCRIPTIONS:
        entities.append(RnxPduSensor(coordinator, desc, "PDU"))

    # Per-outlet sensors
    for outlet in coordinator.outlets:
        for desc in SENSOR_DESCRIPTIONS:
            entities.append(RnxPduSensor(coordinator, desc, outlet.node_id, outlet))

    async_add_entities(entities)


class RnxPduSensor(RnxPduEntity, SensorEntity):
    """Sensor entity for an RNX UPDU meter reading."""

    entity_description: RnxPduSensorEntityDescription

    @property
    def native_value(self) -> float | None:
        """Return the sensor value."""
        if self.coordinator.data is None:
            return None
        meter = self.coordinator.data.meters.get(self.node_id)
        if meter is None:
            return None
        return self.entity_description.value_fn(meter)
