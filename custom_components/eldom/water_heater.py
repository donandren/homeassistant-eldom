from dataclasses import dataclass
from typing import Any

from homeassistant.components.water_heater import (
    ATTR_TEMPERATURE,
    WaterHeaterEntity,
    WaterHeaterEntityEntityDescription,
    WaterHeaterEntityFeature,
)
from homeassistant.const import UnitOfTemperature

from . import HomeAssistantEldomData
from .api import DeviceType, Mode
from .const import BOOST, DOMAIN, LOGGER
from .coordinator import EldomCoordinator, SetState
from .entity import EldomBaseEntity


@dataclass
class EldomHeaterEntityDescription(WaterHeaterEntityEntityDescription):
    """Describes Eldom sensor entity."""


HEATERS: dict[DeviceType, EldomHeaterEntityDescription] = {
    # Eldom Flat Boiler
    DeviceType.FLAT_WATER_HEATER: EldomHeaterEntityDescription(
        key="heater", name=DeviceType.FLAT_WATER_HEATER.name
    )
}


async def async_setup_entry(hass, config_entry, async_add_entities):
    hass_data: HomeAssistantEldomData = hass.data[DOMAIN][config_entry.entry_id]
    entities = []

    for id, device in hass_data.devices.items():
        if descr := HEATERS.get(device.device_type):
            coordinator = hass_data.coordinators[id]
            LOGGER.debug("creating heater for %s:%s", id, device.display_name)
            entities.append(EldomHeaterEntity(coordinator, descr))

    async_add_entities(entities, True)


class EldomHeaterEntity(EldomBaseEntity, WaterHeaterEntity):
    _attr_supported_features = (
        WaterHeaterEntityFeature.TARGET_TEMPERATURE
        | WaterHeaterEntityFeature.OPERATION_MODE
        | WaterHeaterEntityFeature.ON_OFF
    )
    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    def __init__(
        self,
        coordinator: EldomCoordinator,
        description: WaterHeaterEntityEntityDescription,
    ) -> None:
        super().__init__(coordinator, description)
        self._attr_name = coordinator.device.display_name
        self._attr_max_temp = 75
        self._attr_min_temp = 35
        self._attr_operation_list = [
            Mode.HEATING.name,
            Mode.OFF.name,
            Mode.SMART.name,
            Mode.TIMERS.name,
            Mode.STUDY.name,
            BOOST,
        ]

    @property
    def current_operation(self) -> str | None:
        """Return current operation ie. eco, electric, performance, ..."""
        if self.coordinator.state.has_boost:
            return BOOST
        return self.coordinator.state.state.name

    @property
    def is_on(self) -> bool:
        return self.coordinator.state.state is not Mode.OFF

    @property
    def current_temperature(self) -> float | None:
        return self.coordinator.state.current_temp

    @property
    def target_temperature(self) -> float | None:
        return self.coordinator.state.set_temp

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        LOGGER.debug(f"set_temperature {kwargs}")
        if ATTR_TEMPERATURE in kwargs:
            await self.coordinator.async_set_state(
                SetState.TEMP, int(kwargs[ATTR_TEMPERATURE])
            )
        else:
            raise NotImplementedError()

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        """Set new target operation mode."""
        LOGGER.debug(f"set_operation_mode: {operation_mode}")
        if operation_mode == BOOST:
            await self.async_turn_on()
            await self.coordinator.async_set_state(SetState.BOOST, True)
            self.coordinator.state.has_boost = True
        else:
            await self.coordinator.async_set_state(SetState.MODE, Mode[operation_mode])
            self.coordinator.state.state = Mode[operation_mode]

    async def async_turn_on(self, **kwargs: Any) -> None:
        """turn on"""
        LOGGER.debug(f"turn_on: {kwargs}")
        if self.is_on is not True:
            await self.coordinator.async_set_state(SetState.MODE, Mode.HEATING)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """turn off"""
        LOGGER.debug(f"turn_off: {kwargs}")
        await self.coordinator.async_set_state(SetState.MODE, Mode.OFF)
