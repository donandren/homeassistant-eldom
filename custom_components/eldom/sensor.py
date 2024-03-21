"""Support for smartlife sensors."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from . import HomeAssistantEldomData
from .api import DeviceType
from .const import DOMAIN, LOGGER
from .coordinator import EldomCoordinator
from .entity import EldomBaseEntity


@dataclass
class EldomSensorEntityDescription(SensorEntityDescription):
    """Describes Eldom sensor entity."""


SENSORS: dict[DeviceType, tuple[EldomSensorEntityDescription, ...]] = {
    DeviceType.FLAT_WATER_HEATER: (
        EldomSensorEntityDescription(
            key="current_temp",
            name="Temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            icon="mdi:water-thermometer",
        ),
        EldomSensorEntityDescription(
            key="first_cylinder_temp",
            name="Temperature Cylinder 1",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            icon="mdi:water-thermometer",
        ),
        EldomSensorEntityDescription(
            key="second_cylinder_temp",
            name="Temperature Cylinder 2",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            icon="mdi:water-thermometer",
        ),
        EldomSensorEntityDescription(
            key="energy_total",
            name="Total energy consumption",
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        ),
        EldomSensorEntityDescription(
            key="energy_day",
            name="Energy Consumption R1",
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL,
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        ),
        EldomSensorEntityDescription(
            key="energy_night",
            name="Energy Consumption R2",
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL,
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        ),
        EldomSensorEntityDescription(
            key="saved_energy_kwh",
            name="Saved energy",
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL,
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
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
                entities.append(EldomSensorEntity(coordinator, description))

    async_add_entities(entities)


class EldomSensorEntity(EldomBaseEntity, SensorEntity):
    def __init__(
        self,
        coordinator: EldomCoordinator,
        description: EldomSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator, description)

    @property
    def native_value(self) -> StateType:
        """Return the value reported by the sensor."""

        if self.coordinator.state is not None and hasattr(
            self.coordinator.state, self.entity_description.key
        ):
            return getattr(self.coordinator.state, self.entity_description.key)

        return None
