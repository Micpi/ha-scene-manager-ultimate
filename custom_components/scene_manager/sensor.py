"""Sensors for Scene Manager Ultimate."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN, REGISTRY_ENTITY_ID, SIGNAL_UPDATED, VERSION, SceneManagerRuntime


def _parse_timestamp(value: str | None) -> datetime | None:
    """Parse an ISO timestamp for Home Assistant timestamp sensors."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


class SceneManagerBaseSensor(SensorEntity):
    """Base Scene Manager sensor."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        manager: SceneManagerRuntime,
        entry: ConfigEntry,
        key: str,
        name: str,
    ) -> None:
        self.manager = manager
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_name = name
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Scene Manager Ultimate",
            "manufacturer": "Micpi",
            "model": "Scene Manager Ultimate",
            "sw_version": VERSION,
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
        """Write the updated sensor state."""
        self.async_write_ha_state()


class SceneManagerRegistrySensor(SceneManagerBaseSensor):
    """Registry sensor consumed by the Lovelace card."""

    _attr_entity_id = REGISTRY_ENTITY_ID
    _attr_icon = "mdi:database-sync"

    def __init__(self, manager: SceneManagerRuntime, entry: ConfigEntry) -> None:
        super().__init__(manager, entry, "registry", "Registry")

    @property
    def native_value(self) -> int:
        """Return the current registry revision."""
        return self.manager.revision

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return registry data for the Lovelace card."""
        return self.manager.registry_attributes


class SceneManagerSceneCountSensor(SceneManagerBaseSensor):
    """Sensor exposing the amount of stored scenes."""

    _attr_entity_id = "sensor.scene_manager_scene_count"
    _attr_icon = "mdi:palette-swatch"

    def __init__(self, manager: SceneManagerRuntime, entry: ConfigEntry) -> None:
        super().__init__(manager, entry, "scene_count", "Scenes")

    @property
    def native_value(self) -> int:
        """Return the scene count."""
        return self.manager.scene_count


class SceneManagerLastModifiedSensor(SceneManagerBaseSensor):
    """Timestamp of the last scene manager modification."""

    _attr_entity_id = "sensor.scene_manager_last_modified"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, manager: SceneManagerRuntime, entry: ConfigEntry) -> None:
        super().__init__(manager, entry, "last_modified", "Last Modified")

    @property
    def native_value(self) -> datetime | None:
        """Return the last modification timestamp."""
        return _parse_timestamp(self.manager.last_modified)


class SceneManagerLastModifiedBySensor(SceneManagerBaseSensor):
    """User who last modified Scene Manager data."""

    _attr_entity_id = "sensor.scene_manager_last_modified_by"
    _attr_icon = "mdi:account-edit"

    def __init__(self, manager: SceneManagerRuntime, entry: ConfigEntry) -> None:
        super().__init__(manager, entry, "last_modified_by", "Last Modified By")

    @property
    def native_value(self) -> str:
        """Return the last modifier."""
        return self.manager.last_modified_by or "unknown"


class SceneManagerLastActionSensor(SceneManagerBaseSensor):
    """Last Scene Manager action."""

    _attr_entity_id = "sensor.scene_manager_last_action"
    _attr_icon = "mdi:history"

    def __init__(self, manager: SceneManagerRuntime, entry: ConfigEntry) -> None:
        super().__init__(manager, entry, "last_action", "Last Action")

    @property
    def native_value(self) -> str:
        """Return the last action."""
        return self.manager.last_action or "idle"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the latest action details."""
        return {
            "user": self.manager.last_action_by,
            "scene": self.manager.last_scene,
            "triggered_at": self.manager.last_triggered,
            "live_mode": self.manager.live_mode,
        }


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Scene Manager sensors."""
    manager: SceneManagerRuntime = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            SceneManagerRegistrySensor(manager, entry),
            SceneManagerSceneCountSensor(manager, entry),
            SceneManagerLastModifiedSensor(manager, entry),
            SceneManagerLastModifiedBySensor(manager, entry),
            SceneManagerLastActionSensor(manager, entry),
        ]
    )
