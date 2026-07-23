"""Config flow for Scene Manager Ultimate."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from . import (
    CONF_AUTO_REGISTER_RESOURCE,
    CONF_NOTIFY_RESOURCE_FALLBACK,
    DEFAULT_OPTIONS,
    DOMAIN,
)


def _options_schema(config_entry: config_entries.ConfigEntry | None = None) -> vol.Schema:
    data = dict(DEFAULT_OPTIONS)
    if config_entry is not None:
        data.update(config_entry.data)
        data.update(config_entry.options)

    return vol.Schema(
        {
            vol.Optional(
                CONF_AUTO_REGISTER_RESOURCE,
                default=bool(data[CONF_AUTO_REGISTER_RESOURCE]),
            ): bool,
            vol.Optional(
                CONF_NOTIFY_RESOURCE_FALLBACK,
                default=bool(data[CONF_NOTIFY_RESOURCE_FALLBACK]),
            ): bool,
        }
    )


class SceneManagerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the Scene Manager Ultimate config flow."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial setup step."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(
                title="Scene Manager Ultimate",
                data={
                    CONF_AUTO_REGISTER_RESOURCE: bool(
                        user_input.get(CONF_AUTO_REGISTER_RESOURCE, True)
                    ),
                    CONF_NOTIFY_RESOURCE_FALLBACK: bool(
                        user_input.get(CONF_NOTIFY_RESOURCE_FALLBACK, True)
                    ),
                },
            )

        return self.async_show_form(step_id="user", data_schema=_options_schema())

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return the options flow handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Scene Manager Ultimate options."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={
                    CONF_AUTO_REGISTER_RESOURCE: bool(
                        user_input.get(CONF_AUTO_REGISTER_RESOURCE, True)
                    ),
                    CONF_NOTIFY_RESOURCE_FALLBACK: bool(
                        user_input.get(CONF_NOTIFY_RESOURCE_FALLBACK, True)
                    ),
                },
            )

        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(self.config_entry),
        )
