"""Config flow for Scene Manager Ultimate."""

from __future__ import annotations

from homeassistant import config_entries

from . import DOMAIN


class SceneManagerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the Scene Manager Ultimate config flow."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Create the single Scene Manager Ultimate entry."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        return self.async_create_entry(title="Scene Manager Ultimate", data={})
