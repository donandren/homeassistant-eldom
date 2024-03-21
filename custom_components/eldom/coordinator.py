import datetime as dt
from enum import StrEnum

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import Device, DeviceState, EldomAPI, Mode
from .const import (
    CONF_POLL_INTERVAL,
    CONF_POLL_INTERVAL_FAST,
    DEFAULT_FAST_POLL,
    DEFAULT_NORMAL_POLL,
    LOGGER,
)


class SetState(StrEnum):
    MODE = "mode"
    """set target mode"""

    TEMP = "temp"
    """set target temperature"""

    BOOST = "boost"
    """power boost"""


class EldomCoordinator(DataUpdateCoordinator[DeviceState]):
    _fast_poll_count = 0
    _initialized = False

    def __init__(
        self,
        hass: HomeAssistant,
        api: EldomAPI,
        id: str,
        device: Device,
        state: DeviceState,
        conf: dict,
    ):
        self.id = id
        self._api = api
        self.device = device

        self._normal_poll_interval = int(
            conf.get(CONF_POLL_INTERVAL, DEFAULT_NORMAL_POLL)
        )
        self._fast_poll_interval = int(
            conf.get(CONF_POLL_INTERVAL_FAST, DEFAULT_FAST_POLL)
        )

        """Initialize coordinator parent"""
        super().__init__(
            hass,
            LOGGER,
            name=f"Eldom:{self.device.display_name}",
            update_interval=dt.timedelta(seconds=self._fast_poll_interval),
            update_method=self.async_update,
        )
        self.data = state

    def _set_poll_mode(self, fast: bool):
        self._fast_poll_count = 0 if fast else -1
        interval = self._fast_poll_interval if fast else self._normal_poll_interval
        self.update_interval = dt.timedelta(seconds=interval)
        self._schedule_refresh()

    def _update_poll(self):
        if self._fast_poll_count > -1:
            self._fast_poll_count += 1
            if self._fast_poll_count > 5:
                self._set_poll_mode(fast=False)

    async def async_update(self):
        self._update_poll()

        if not self._initialized:
            await self._initialize()

        return await self.hass.async_add_executor_job(self._api.get_state, self.device)

    async def _initialize(self):
        pass
        # try:
        #     if self._client.service_info is not None:
        #         self._initialized = True
        #         reg = device_registry.async_get(self.hass)
        #         reg.async_update_device(
        #             self.device_id,
        #             name=self._client.service_info.name,
        #             manufacturer=self._client.device_manifacturer,
        #             hw_version=self._client.device_version,
        #         )
        # except Exception as e:
        #     LOGGER.warning("Failed to initialize %s: %s", self.address, str(e))

    @property
    def state(self) -> DeviceState:
        return self.data

    async def async_set_state(self, key: SetState, value) -> bool:
        match key:
            case SetState.TEMP:
                await self.hass.async_add_executor_job(
                    self._api.set_temperature, self.device, int(value)
                )
            case SetState.BOOST:
                await self.hass.async_add_executor_job(
                    self._api.set_power_boost, self.device, True
                )
            case SetState.MODE:
                await self.hass.async_add_executor_job(
                    self._api.set_state, self.device, Mode(value)
                )
            case _:
                LOGGER.warning("async_set_state: invalid key %s - %s", key, value)
                return False

        # self.state[key] = value

        LOGGER.info("async_set_state: %s - %s", key, value)

        # self.async_set_updated_data(self.state)
        self._set_poll_mode(fast=True)
        return True

    # async def async_shutdown(self) -> None:
    #     # await self._client.disconnect(force=True)
    #     await super().async_shutdown()
