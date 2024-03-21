"""Constants for the Tuya integration."""
from __future__ import annotations

import logging

from homeassistant.const import Platform

DOMAIN = "eldom"
LOGGER = logging.getLogger(__package__)

CONF_ENDPOINT = "endpoint"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_POLL_INTERVAL: str = "poll_interval"
CONF_POLL_INTERVAL_FAST: str = "poll_interval_fast"

DEFAULT_FAST_POLL = 3
DEFAULT_NORMAL_POLL = 60

BOOST = "Powerfull"

PLATFORMS = [
    Platform.WATER_HEATER,
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
]
