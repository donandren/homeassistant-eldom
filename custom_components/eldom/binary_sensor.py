"""Support for smartlife sensors."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HomeAssistantEldomData
from .api import DeviceType
from .const import BOOST, DOMAIN, LOGGER
from .coordinator import EldomCoordinator
from .entity import EldomBaseEntity


@dataclass
class EldomSensorEntityDescription(BinarySensorEntityDescription):
    """Describes Eldom binary sensor entity."""


SENSORS: dict[DeviceType, tuple[EldomSensorEntityDescription, ...]] = {
    DeviceType.FLAT_WATER_HEATER: (
        EldomSensorEntityDescription(
            key="heating_active", name="Heating", icon="mdi:heating-coil"
        ),
        EldomSensorEntityDescription(
            key="first_cylinder_active",
            name="Heating Cylinder 1",
            icon="mdi:heating-coil",
        ),
        EldomSensorEntityDescription(
            key="second_cylinder_active",
            name="Heating Cylinder 2",
            icon="mdi:heating-coil",
        ),
        EldomSensorEntityDescription(
            key="has_boost",
            name=BOOST,
            device_class=BinarySensorDeviceClass.RUNNING,
        ),
    )
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    hass_data: HomeAssistantEldomData = hass.data[DOMAIN][entry.entry_id]
    entities = []

    for id, device in hass_data.devices.items():
        if descriptions := SENSORS.get(device.device_type):
            coordinator = hass_data.coordinators[id]
            for description in descriptions:
                LOGGER.debug(
                    "creating sensor %s for %s:%s",
                    description.name,
                    id,
                    device.display_name,
                )
                entities.append(EldomBinarySensorEntity(coordinator, description))

    async_add_entities(entities)


class EldomBinarySensorEntity(EldomBaseEntity, BinarySensorEntity):
    def __init__(
        self,
        coordinator: EldomCoordinator,
        description: EldomSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator, description)

    @property
    def is_on(self) -> bool:
        if self.coordinator.state is not None and hasattr(
            self.coordinator.state, self.entity_description.key
        ):
            return getattr(self.coordinator.state, self.entity_description.key)
        return False
