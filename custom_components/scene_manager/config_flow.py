"""Config flow for Scene Manager Ultimate."""

from __future__ import annotations

from homeassistant import config_entries
import voluptuous as vol

from . import DOMAIN


class SceneManagerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the Scene Manager Ultimate config flow."""

    # Config flow schema version used by Home Assistant migrations.
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Create the single Scene Manager Ultimate entry."""
        # Only one Scene Manager entry is allowed because it owns fixed entity ids.
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        # Empty form lets Home Assistant create the integration from the UI.
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({}),
            )

        # Persistent entry data is empty because runtime state lives in Store storage.
        return self.async_create_entry(title="Scene Manager Ultimate", data={})
