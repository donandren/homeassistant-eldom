from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EldomCoordinator


class EldomBaseEntity(CoordinatorEntity[EldomCoordinator]):
    """Eldom base entity class."""

    def __init__(self, coordinator: EldomCoordinator, description: EntityDescription):
        super().__init__(coordinator)
        self._attr_unique_id = f"{self.coordinator.id}-{description.key}"
        self.entity_description = description
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self.coordinator.id)},
            "model": self.coordinator.device.device_type.name,
        }
