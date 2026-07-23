"""Switches for Scene Manager Ultimate."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN, SIGNAL_UPDATED, VERSION, SceneManagerRuntime


class SceneManagerLiveModeSwitch(SwitchEntity):
    """Persistent live scene editing switch."""

    # Fixed entity id used by the Lovelace card and automations.
    _attr_entity_id = "switch.scene_manager_live_mode"

    # Let Home Assistant combine device name and entity name.
    _attr_has_entity_name = True

    # Icon displayed by Home Assistant for live edit mode.
    _attr_icon = "mdi:flash"

    # User-visible switch name suffix.
    _attr_name = "Live Mode"

    # Switch updates from dispatcher signals, not polling.
    _attr_should_poll = False

    def __init__(self, manager: SceneManagerRuntime, entry: ConfigEntry) -> None:
        """Initialize the persistent live mode switch."""
        # Shared runtime coordinator used to read/write live mode.
        self.manager = manager

        # Unique id stable across restarts for entity registry.
        self._attr_unique_id = f"{entry.entry_id}_live_mode"

        # Device metadata groups all Scene Manager entities together.
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Scene Manager Ultimate",
            "manufacturer": "Micpi",
            "model": "Scene Manager Ultimate",
            "sw_version": VERSION,
        }

    @property
    def is_on(self) -> bool:
        """Return whether live editing is enabled."""
        return self.manager.live_mode

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return live mode details."""
        return {
            "description": "When enabled, the card applies light changes while editing scenes.",
            "stored": True,
        }

    async def async_added_to_hass(self) -> None:
        """Subscribe to runtime updates."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_UPDATED,
                self._handle_runtime_update,
            )
        )

    @callback
    def _handle_runtime_update(self) -> None:
        """Write the updated switch state."""
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable live editing."""
        await self.manager.async_set_live_mode(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable live editing."""
        await self.manager.async_set_live_mode(False)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Scene Manager switches."""
    # Runtime created by __init__.py during integration setup.
    manager: SceneManagerRuntime = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SceneManagerLiveModeSwitch(manager, entry)])
