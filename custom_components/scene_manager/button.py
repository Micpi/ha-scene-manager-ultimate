"""Buttons for Scene Manager Ultimate."""

from __future__ import annotations

from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN, SIGNAL_UPDATED, VERSION, SceneManagerRuntime


def _button_key(entity_id: str) -> str:
    """Return a stable unique id suffix from a scene entity id."""
    return entity_id.replace(".", "_")


def _scene_name(manager: SceneManagerRuntime, entity_id: str) -> str:
    """Return a readable scene name."""
    # Prefer Home Assistant's friendly name when the scene state exists.
    state = manager.hass.states.get(entity_id)
    if state is not None:
        friendly_name = state.attributes.get("friendly_name")
        if friendly_name:
            return str(friendly_name)

    return entity_id.split(".", 1)[-1].replace("_", " ").title()


class SceneManagerSceneButton(ButtonEntity):
    """Button that activates one stored scene."""

    # Let Home Assistant combine device name and entity name.
    _attr_has_entity_name = True

    # Buttons update from dispatcher signals, not polling.
    _attr_should_poll = False

    def __init__(
        self,
        manager: SceneManagerRuntime,
        entry: ConfigEntry,
        scene_entity_id: str,
    ) -> None:
        """Initialize one dynamic scene activation button."""
        # Shared runtime coordinator used to activate and inspect scenes.
        self.manager = manager

        # Managed scene entity id activated by this button.
        self.scene_entity_id = scene_entity_id

        # Unique id stable across restarts for entity registry.
        self._attr_unique_id = f"{entry.entry_id}_{_button_key(scene_entity_id)}_activate"

        # Fixed-ish entity id generated from the scene entity id.
        self._attr_entity_id = f"button.scene_manager_activate_{scene_entity_id.split('.', 1)[-1]}"

        # Device metadata groups all Scene Manager entities together.
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Scene Manager Ultimate",
            "manufacturer": "Micpi",
            "model": "Scene Manager Ultimate",
            "sw_version": VERSION,
        }

    @property
    def name(self) -> str:
        """Return the button name."""
        return f"Activate {_scene_name(self.manager, self.scene_entity_id)}"

    @property
    def icon(self) -> str:
        """Return the scene icon."""
        item = self.manager.meta.get(self.scene_entity_id, {})
        if isinstance(item, dict):
            icon = item.get("icon")
            if icon:
                return str(icon)
        return "mdi:palette"

    @property
    def available(self) -> bool:
        """Return whether the scene is still available."""
        return (
            self.scene_entity_id in self.manager.meta
            and self.manager.hass.states.get(self.scene_entity_id) is not None
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return scene details."""
        item = self.manager.meta.get(self.scene_entity_id, {})
        if not isinstance(item, dict):
            item = {}
        return {
            "scene_entity_id": self.scene_entity_id,
            "room": item.get("room"),
            "order_key": item.get("order_key"),
            "updated_at": item.get("updated_at"),
            "updated_by": item.get("updated_by"),
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
        """Write the updated button state."""
        self.async_write_ha_state()

    async def async_press(self) -> None:
        """Activate the scene."""
        await self.manager.async_activate_entity_id(
            self.scene_entity_id,
            source="button",
        )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Scene Manager scene buttons."""
    # Runtime created by __init__.py during integration setup.
    manager: SceneManagerRuntime = hass.data[DOMAIN][entry.entry_id]

    # Scene ids that already have a Home Assistant button entity.
    known: set[str] = set()

    @callback
    def add_missing_buttons() -> None:
        """Create buttons for scenes that appeared after setup."""
        # Button entities created during this update pass.
        new_entities: list[SceneManagerSceneButton] = []
        for scene_entity_id in sorted(manager.meta):
            if scene_entity_id in known:
                continue
            known.add(scene_entity_id)
            new_entities.append(SceneManagerSceneButton(manager, entry, scene_entity_id))

        if new_entities:
            async_add_entities(new_entities)

    add_missing_buttons()
    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_UPDATED, add_missing_buttons)
    )
