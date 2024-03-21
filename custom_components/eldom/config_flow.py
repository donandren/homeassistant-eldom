"""Config flow for Tuya."""
from __future__ import annotations

from typing import Any
import voluptuous as vol
from homeassistant import config_entries

from .api import EldomAPI
from .const import CONF_ENDPOINT, CONF_PASSWORD, CONF_USERNAME, DOMAIN, LOGGER


class EldomConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Tuya Config Flow."""

    @staticmethod
    def _try_login(user_input: dict[str, Any]) -> tuple[dict[Any, Any], dict[str, Any]]:
        """Try login."""
        response = {}

        data = {
            CONF_ENDPOINT: user_input[CONF_ENDPOINT],
            CONF_USERNAME: user_input[CONF_USERNAME],
            CONF_PASSWORD: user_input[CONF_PASSWORD],
        }

        api = EldomAPI(data[CONF_ENDPOINT])
        result = False
        try:
            result = api.login(data[CONF_USERNAME], data[CONF_PASSWORD])
        except Exception as e:
            response["error"] = str(e)
        response["result"] = result
        return response, data

    async def async_step_user(self, user_input=None):
        """Step user."""
        errors = {}
        placeholders = {}

        if user_input is not None:
            response, data = await self.hass.async_add_executor_job(
                self._try_login, user_input
            )

            if response.get("result", False):
                return self.async_create_entry(
                    title=user_input[CONF_USERNAME],
                    data=data,
                )
            errors["base"] = "login_error"
            placeholders = {"msg": response.get("error","?")}

        if user_input is None:
            user_input = {}

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_ENDPOINT,
                        default=user_input.get(CONF_ENDPOINT, "https://myeldom.com"),
                    ): str,
                    vol.Required(
                        CONF_USERNAME, default=user_input.get(CONF_USERNAME, "")
                    ): str,
                    vol.Required(
                        CONF_PASSWORD, default=user_input.get(CONF_PASSWORD, "")
                    ): str,
                }
            ),
            errors=errors,
            description_placeholders=placeholders,
        )
