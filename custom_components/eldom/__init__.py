from typing import NamedTuple

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .api import Device, EldomAPI
from .const import (
    CONF_ENDPOINT,
    CONF_PASSWORD,
    CONF_POLL_INTERVAL,
    CONF_POLL_INTERVAL_FAST,
    CONF_USERNAME,
    DEFAULT_FAST_POLL,
    DEFAULT_NORMAL_POLL,
    DOMAIN,
    LOGGER,
    PLATFORMS,
)
from .coordinator import EldomCoordinator


class HomeAssistantEldomData(NamedTuple):
    """Smart Life data stored in the Home Assistant data object."""

    api: EldomAPI
    coordinators: dict[str, EldomCoordinator]
    devices: dict[str, Device]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Async setup hass config entry."""
    LOGGER.debug("Setting up configuration for Eldom devices!")
    hass.data.setdefault(DOMAIN, {})

    if hass.data[DOMAIN].get(entry.entry_id) is None:
        hass_data = HomeAssistantEldomData(
            api=EldomAPI(entry.data[CONF_ENDPOINT]), devices={}, coordinators={}
        )
        hass.data[DOMAIN][entry.entry_id] = hass_data
    else:
        hass_data: HomeAssistantEldomData = hass.data[DOMAIN][entry.entry_id]

    api = hass_data.api
    devices = hass_data.devices
    coordinators = hass_data.coordinators

    conf = {
        CONF_POLL_INTERVAL: DEFAULT_NORMAL_POLL,
        CONF_POLL_INTERVAL_FAST: DEFAULT_FAST_POLL,
    }

    # login
    lr = await hass.async_add_executor_job(
        api.login, entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD]
    )
    LOGGER.debug("login %s", lr)

    # get devices
    result = await hass.async_add_executor_job(api.get_devices)
    LOGGER.debug("get_devices %s devices", len(result))

    # populate
    for dev in result:
        devices[dev.real_device_id] = dev

    # Create one coordinator for each device
    for id, device in devices.items():
        # Create device
        device_registry = dr.async_get(hass)
        LOGGER.debug("adding device %s", device)
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, id)},
            name=device.display_name,
            hw_version=device.hw_version,
            sw_version=device.sw_version,
            model=f"{device.device_type.name} (unsupported)",
            configuration_url=f"{api._endpoint}/#/device/flatboiler/{device.id}",
        )
        state = await hass.async_add_executor_job(api.get_state, device)
        # Set up coordinator
        coordinators[id] = EldomCoordinator(hass, api, id, device, state, conf)
    # clean up device entities
    await cleanup_device_registry(hass, devices)

    # Forward the setup to the platforms.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def cleanup_device_registry(
    hass: HomeAssistant, devices: dict[str, Device]
) -> None:
    """Remove deleted device registry entry if there are no remaining entities."""
    device_registry = dr.async_get(hass)
    for dev_id, device_entry in list(device_registry.devices.items()):
        for item in device_entry.identifiers:
            if item[0] == DOMAIN and item[1] not in devices:
                device_registry.async_remove_device(dev_id)
                break


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unloading the Eldom platforms."""

    LOGGER.debug("unload entry id = %s", entry.entry_id)
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove a config entry."""
    LOGGER.debug("remove entry id = %s", entry.entry_id)
    hass_data: HomeAssistantEldomData = hass.data[DOMAIN][entry.entry_id]
    for _, c in hass_data.coordinators.items():
        await c.async_shutdown()

    hass.data[DOMAIN].pop(entry.entry_id)
    if not hass.data[DOMAIN]:
        hass.data.pop(DOMAIN)
