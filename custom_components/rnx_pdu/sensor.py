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
    EntityCategory,
    UnitOfApparentPower,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfTime,
    PERCENTAGE,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import (
    EnvironmentData,
    MeterData,
    RcmNodeData,
    RnxPduConfigEntry,
    RnxPduCoordinator,
)
from .entity import RnxPduEntity


@dataclass(frozen=True, kw_only=True)
class RnxPduSensorEntityDescription(SensorEntityDescription):
    """Describes an RNX UPDU sensor."""

    value_fn: Callable[[MeterData], float | None]


@dataclass(frozen=True, kw_only=True)
class RnxPduEnvironmentSensorDescription(SensorEntityDescription):
    """Describes an RNX UPDU environment sensor."""

    value_fn: Callable[[EnvironmentData], float | None]


@dataclass(frozen=True, kw_only=True)
class RnxPduRcmSensorDescription(SensorEntityDescription):
    """Describes an RNX UPDU residual current sensor."""

    value_fn: Callable[[RcmNodeData], float | None]


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

ENVIRONMENT_DESCRIPTIONS: tuple[RnxPduEnvironmentSensorDescription, ...] = (
    RnxPduEnvironmentSensorDescription(
        key="temperature",
        translation_key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        value_fn=lambda e: e.temperature_c,
    ),
    RnxPduEnvironmentSensorDescription(
        key="humidity",
        translation_key="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=1,
        value_fn=lambda e: e.humidity_pct,
    ),
    RnxPduEnvironmentSensorDescription(
        key="differential_pressure",
        translation_key="differential_pressure",
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPressure.PA,
        suggested_display_precision=1,
        value_fn=lambda e: e.pressure_pa,
    ),
)

RCM_DESCRIPTIONS: tuple[RnxPduRcmSensorDescription, ...] = (
    RnxPduRcmSensorDescription(
        key="rcm_rms",
        translation_key="rcm_rms",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        suggested_display_precision=1,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda r: r.rms_ma,
    ),
    RnxPduRcmSensorDescription(
        key="rcm_dc",
        translation_key="rcm_dc",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        suggested_display_precision=1,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda r: r.dc_ma,
    ),
)

UPTIME_DESCRIPTION = SensorEntityDescription(
    key="uptime",
    translation_key="uptime",
    device_class=SensorDeviceClass.DURATION,
    state_class=SensorStateClass.TOTAL_INCREASING,
    native_unit_of_measurement=UnitOfTime.SECONDS,
    entity_category=EntityCategory.DIAGNOSTIC,
    suggested_display_precision=0,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: RnxPduConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up RNX UPDU sensors."""
    coordinator = config_entry.runtime_data
    entities: list[SensorEntity] = []

    # PDU-level meter sensors
    for desc in SENSOR_DESCRIPTIONS:
        entities.append(RnxPduSensor(coordinator, desc, "PDU"))

    # Per-outlet meter sensors
    for outlet in coordinator.outlets:
        for desc in SENSOR_DESCRIPTIONS:
            entities.append(RnxPduSensor(coordinator, desc, outlet.node_id, outlet))

    # Environment sensors (temperature, humidity, pressure)
    for sensor_node in coordinator.sensor_nodes:
        for desc in ENVIRONMENT_DESCRIPTIONS:
            entities.append(
                RnxPduEnvironmentSensor(coordinator, desc, sensor_node.node_id)
            )

    # RCM sensors (residual current) — only if nodes report RCM data
    # RCM nodes are discovered from live data; create entities for any inlet with hasRcm
    # For now, create from live data keys if present
    if coordinator.data and coordinator.data.rcms:
        for node_id in coordinator.data.rcms:
            for desc in RCM_DESCRIPTIONS:
                entities.append(RnxPduRcmSensor(coordinator, desc, node_id))

    # Uptime sensor (PDU-level)
    entities.append(RnxPduUptimeSensor(coordinator, UPTIME_DESCRIPTION, "PDU"))

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


class RnxPduEnvironmentSensor(RnxPduEntity, SensorEntity):
    """Sensor entity for an RNX UPDU environment reading."""

    entity_description: RnxPduEnvironmentSensorDescription

    @property
    def native_value(self) -> float | None:
        """Return the sensor value."""
        if self.coordinator.data is None:
            return None
        env = self.coordinator.data.environment.get(self.node_id)
        if env is None:
            return None
        return self.entity_description.value_fn(env)


class RnxPduRcmSensor(RnxPduEntity, SensorEntity):
    """Sensor entity for an RNX UPDU residual current reading."""

    entity_description: RnxPduRcmSensorDescription

    @property
    def native_value(self) -> float | None:
        """Return the sensor value."""
        if self.coordinator.data is None:
            return None
        rcm = self.coordinator.data.rcms.get(self.node_id)
        if rcm is None:
            return None
        return self.entity_description.value_fn(rcm)


class RnxPduUptimeSensor(RnxPduEntity, SensorEntity):
    """Sensor entity for PDU uptime."""

    @property
    def native_value(self) -> int | None:
        """Return the uptime in seconds."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.uptime_s
