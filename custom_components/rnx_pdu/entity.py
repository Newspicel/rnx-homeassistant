"""Base entity for RNX UPDU."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import OutletInfo, RnxPduCoordinator


class RnxPduEntity(CoordinatorEntity[RnxPduCoordinator]):
    """Base entity for RNX UPDU devices."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: RnxPduCoordinator,
        description: EntityDescription,
        node_id: str,
        outlet: OutletInfo | None = None,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self.node_id = node_id
        self._attr_unique_id = f"{coordinator.serial}_{node_id}_{description.key}"
        self._attr_device_info = self._build_device_info(outlet)

    def _build_device_info(self, outlet: OutletInfo | None) -> DeviceInfo:
        """Build device info for the PDU or an outlet."""
        if outlet is not None:
            module = outlet.parent_module
            return DeviceInfo(
                identifiers={(DOMAIN, f"{self.coordinator.serial}_{outlet.node_id}")},
                name=f"Outlet {outlet.label}",
                manufacturer="RNX",
                model=module.part_number if module else None,
                sw_version=module.firmware_version if module else None,
                via_device=(DOMAIN, self.coordinator.serial),
            )
        # PDU-level device
        module = self.coordinator.modules[0] if self.coordinator.modules else None
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.serial)},
            name="RNX UPDU",
            manufacturer="RNX",
            model=module.part_number if module else None,
            sw_version=module.firmware_version if module else None,
            serial_number=module.serial_number if module else None,
            configuration_url=f"https://{self.coordinator.api.host}",
        )
