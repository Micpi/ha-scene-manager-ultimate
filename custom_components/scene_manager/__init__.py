"""Scene Manager Ultimate integration."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
import logging
from pathlib import Path
import re
import time
from typing import Any

from homeassistant.components.scene import DOMAIN as SCENE_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ENTITY_ID, Platform
from homeassistant.core import Context, HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.storage import Store

try:
    from homeassistant.exceptions import ServiceValidationError
except ImportError:  # pragma: no cover - older Home Assistant fallback

    class ServiceValidationError(HomeAssistantError):
        """Fallback validation error."""


try:
    from homeassistant.components.lovelace import DOMAIN as LOVELACE_DOMAIN
    from homeassistant.components.lovelace.const import CONF_RESOURCES
except ImportError:  # pragma: no cover - Lovelace is always available on supported HA
    LOVELACE_DOMAIN = "lovelace"
    CONF_RESOURCES = "resources"


DOMAIN = "scene_manager"
VERSION = "1.1.1"

STORAGE_KEY = "scene_manager_data"
STORAGE_VERSION = 1

REGISTRY_ENTITY_ID = "sensor.scene_manager_registry"
CARD_REPOSITORY = "Micpi/scene-manager-card"
CARD_RESOURCE_URL = "/hacsfiles/scene-manager-card/scene-manager-card.js"
LEGACY_CARD_URL = f"/{DOMAIN}/card.js"
LEGACY_CARD_FILENAME = "scene-manager-card.js"

CONF_ORDER_KEY = "order_key"
CONF_REPLACE_ENTITY_ID = "replace_entity_id"

SERVICE_SAVE_SCENE = "save_scene"
SERVICE_DELETE_SCENE = "delete_scene"
SERVICE_REORDER_SCENES = "reorder_scenes"
SERVICE_ACTIVATE_SCENE = "activate_scene"
SERVICE_SET_LIVE_MODE = "set_live_mode"

SIGNAL_UPDATED = f"{DOMAIN}_updated"
PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH, Platform.BUTTON]

_LOGGER = logging.getLogger(__name__)


def _utc_now_iso() -> str:
    """Return the current UTC datetime as an ISO string."""
    return datetime.now(UTC).isoformat()


def _new_data() -> dict[str, Any]:
    """Return a normalized storage payload."""
    return {
        "meta": {},
        "order": {},
        "revision": 0,
        "updated_at": 0,
        "live_mode": False,
        "last_modified": None,
        "last_modified_by": None,
        "last_action": None,
        "last_action_by": None,
        "last_scene": None,
        "last_triggered": None,
    }


async def _async_load_data(store: Store) -> dict[str, Any]:
    """Load and normalize the integration storage."""
    stored = await store.async_load()
    data = _new_data()

    if isinstance(stored, dict):
        data.update(stored)

    if not isinstance(data.get("meta"), dict):
        data["meta"] = {}
    if not isinstance(data.get("order"), dict):
        data["order"] = {}

    for key, default in _new_data().items():
        data.setdefault(key, default)

    return data


def _public_meta(data: dict[str, Any]) -> dict[str, Any]:
    """Return metadata that the Lovelace card may safely consume."""
    meta = data.get("meta", {})
    if not isinstance(meta, dict):
        return {}

    public: dict[str, Any] = {}
    for entity_id, item in meta.items():
        if not isinstance(item, dict):
            continue
        public[entity_id] = {
            "icon": item.get("icon"),
            "color": item.get("color"),
            "room": item.get("room"),
            "order_key": item.get("order_key"),
            "updated_at": item.get("updated_at"),
            "updated_by": item.get("updated_by"),
            "entities": _public_snapshot(item.get("snapshot")),
        }
    return public


def _public_snapshot(snapshot: Any) -> dict[str, Any]:
    """Return a compact scene snapshot for the Lovelace card editor."""
    if not isinstance(snapshot, dict):
        return {}

    public: dict[str, Any] = {}
    for entity_id, item in snapshot.items():
        if not isinstance(entity_id, str) or not isinstance(item, dict):
            continue
        attrs = item.get("attributes")
        if not isinstance(attrs, dict):
            attrs = {}
        public[entity_id] = {
            "state": item.get("state"),
            "brightness": attrs.get("brightness"),
        }
    return public


def _slugify(value: str) -> str:
    """Convert a human scene id to a Home Assistant friendly slug."""
    slug = re.sub(r"[^a-z0-9_]+", "_", str(value).lower()).strip("_")
    return slug or f"scene_{int(time.time())}"


def _normalise_entities(entities: Any) -> list[str]:
    """Normalize service entity input to a list."""
    if isinstance(entities, str):
        return [entities]
    if isinstance(entities, list):
        return [entity for entity in entities if isinstance(entity, str)]
    raise ServiceValidationError("entities must be a string or a list of entity ids")


def _normalise_snapshot(snapshot: Any) -> dict[str, Any]:
    """Normalize a snapshot payload supplied by a card or automation."""
    if not isinstance(snapshot, dict):
        raise ServiceValidationError("snapshot must be an object")

    normalised: dict[str, Any] = {}
    for entity_id, item in snapshot.items():
        if not isinstance(entity_id, str) or not entity_id:
            continue
        if not isinstance(item, dict):
            continue

        state = item.get("state")
        if not isinstance(state, str):
            continue

        attrs = item.get("attributes")
        if isinstance(attrs, dict):
            attrs = deepcopy(attrs)
        else:
            attrs = {
                key: deepcopy(value)
                for key, value in item.items()
                if key not in ("state", "attributes")
            }

        normalised[entity_id] = {
            "state": state,
            "attributes": attrs,
        }

    if not normalised:
        raise ServiceValidationError("snapshot does not contain valid entities")
    return normalised


def _scene_create_entities(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Convert stored snapshots to the format expected by scene.create."""
    entities: dict[str, Any] = {}
    for entity_id, item in snapshot.items():
        if not isinstance(entity_id, str) or not isinstance(item, dict):
            continue
        state = item.get("state")
        if not isinstance(state, str):
            continue
        attrs = item.get("attributes")
        if isinstance(attrs, dict) and attrs:
            entity_state = deepcopy(attrs)
            entity_state["state"] = state
            entities[entity_id] = entity_state
        else:
            entities[entity_id] = state
    return entities


def _normalise_color(color: Any) -> str:
    """Normalize the optional scene color."""
    if isinstance(color, str) and re.match(r"^#[0-9a-fA-F]{6}$", color):
        return color
    return "#9E9E9E"


def _scene_entity_id_from_call(call: ServiceCall) -> str:
    """Return a scene entity id from a service call."""
    raw = call.data.get(CONF_ENTITY_ID) or call.data.get("entity_id") or call.data.get("scene_id")
    if not raw:
        raise ServiceValidationError("entity_id or scene_id is required")

    return _normalise_scene_entity_id(raw)


def _normalise_scene_entity_id(raw: Any) -> str:
    """Return a normalized scene entity id from a raw value."""
    value = str(raw)
    if value.startswith(f"{SCENE_DOMAIN}."):
        return value
    return f"{SCENE_DOMAIN}.{_slugify(value)}"


def _scene_id_from_entity_id(entity_id: str) -> str:
    """Return the scene service id from an entity id."""
    if entity_id.startswith(f"{SCENE_DOMAIN}."):
        return entity_id.split(".", 1)[1]
    return _slugify(entity_id)


def _remove_from_order(order: dict[str, Any], entity_id: str) -> None:
    """Remove a scene id from every stored order list."""
    for key, value in list(order.items()):
        if isinstance(value, list):
            order[key] = [item for item in value if item != entity_id]


async def _async_get_lovelace_resources(hass: HomeAssistant) -> list[dict[str, Any]] | None:
    """Return the mutable Lovelace resources list when available."""
    lovelace = hass.data.get(LOVELACE_DOMAIN)
    if not lovelace:
        return None

    storage = getattr(lovelace, "_storage", None)
    if storage is None:
        return None

    config = await storage.async_load(False)
    if not isinstance(config, dict):
        return None

    resources = config.setdefault(CONF_RESOURCES, [])
    if not isinstance(resources, list):
        config[CONF_RESOURCES] = []
        resources = config[CONF_RESOURCES]

    return resources


def _resource_url_path(resource: dict[str, Any]) -> str:
    """Normalize a Lovelace resource URL without the query string."""
    url = str(resource.get("url", ""))
    return url.split("?", 1)[0]


async def _async_remove_legacy_lovelace_resource(hass: HomeAssistant) -> bool:
    """Remove the pre-split embedded card Lovelace resource."""
    resources = await _async_get_lovelace_resources(hass)
    if resources is None:
        return False

    before = len(resources)
    resources[:] = [
        resource
        for resource in resources
        if _resource_url_path(resource) != LEGACY_CARD_URL
    ]
    return len(resources) != before


class SceneManagerRuntime:
    """Runtime coordinator for Scene Manager entities and services."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.store: Store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self.data: dict[str, Any] = _new_data()

    @property
    def revision(self) -> int:
        """Return the current storage revision."""
        return int(self.data.get("revision", 0) or 0)

    @property
    def meta(self) -> dict[str, Any]:
        """Return all scene metadata."""
        meta = self.data.get("meta")
        if isinstance(meta, dict):
            return meta
        self.data["meta"] = {}
        return self.data["meta"]

    @property
    def order(self) -> dict[str, Any]:
        """Return all stored scene order lists."""
        order = self.data.get("order")
        if isinstance(order, dict):
            return order
        self.data["order"] = {}
        return self.data["order"]

    @property
    def live_mode(self) -> bool:
        """Return whether live scene editing is enabled."""
        return bool(self.data.get("live_mode", False))

    @property
    def scene_count(self) -> int:
        """Return the number of stored scenes."""
        return len(self.meta)

    @property
    def last_modified(self) -> str | None:
        """Return the last modification timestamp."""
        value = self.data.get("last_modified")
        return value if isinstance(value, str) else None

    @property
    def last_modified_by(self) -> str | None:
        """Return the last modifier display name."""
        value = self.data.get("last_modified_by")
        return value if isinstance(value, str) else None

    @property
    def last_action(self) -> str | None:
        """Return the last action name."""
        value = self.data.get("last_action")
        return value if isinstance(value, str) else None

    @property
    def last_action_by(self) -> str | None:
        """Return the last action user display name."""
        value = self.data.get("last_action_by")
        return value if isinstance(value, str) else None

    @property
    def last_scene(self) -> str | None:
        """Return the last touched scene entity id."""
        value = self.data.get("last_scene")
        return value if isinstance(value, str) else None

    @property
    def last_triggered(self) -> str | None:
        """Return the last scene activation timestamp."""
        value = self.data.get("last_triggered")
        return value if isinstance(value, str) else None

    @property
    def registry_attributes(self) -> dict[str, Any]:
        """Return attributes exposed by sensor.scene_manager_registry."""
        return {
            "meta": _public_meta(self.data),
            "order": deepcopy(self.order),
            "card_repository": CARD_REPOSITORY,
            "card_resource_url": CARD_RESOURCE_URL,
            "legacy_card_resource_url": LEGACY_CARD_URL,
            "live_mode": self.live_mode,
            "last_modified": self.last_modified,
            "last_modified_by": self.last_modified_by,
            "last_action": self.last_action,
            "last_action_by": self.last_action_by,
            "last_scene": self.last_scene,
            "last_triggered": self.last_triggered,
            "revision": self.revision,
        }

    async def async_setup(self) -> None:
        """Load storage, restore scenes, and remove old card artifacts."""
        self.data = await _async_load_data(self.store)
        await self.async_restore_scenes()

        if self.data.pop("resource_registered", None) is not None:
            await _async_remove_legacy_lovelace_resource(self.hass)
            await self.store.async_save(self.data)

        await self.async_remove_legacy_card_file()
        self.async_notify_updated()

    async def async_remove(self) -> None:
        """Remove stored data and old frontend leftovers."""
        await _async_remove_legacy_lovelace_resource(self.hass)
        await self.async_remove_legacy_card_file()

        for notification_id in (
            "scene_manager_card_resource",
            "scene_manager_card_split",
        ):
            try:
                await self.hass.components.persistent_notification.async_dismiss(notification_id)
            except (AttributeError, HomeAssistantError):
                pass

        await self.store.async_remove()
        self.async_notify_updated()

    async def async_remove_legacy_card_file(self) -> None:
        """Delete the legacy embedded card file if it still exists."""
        legacy_file = (
            Path(__file__).resolve().parent / "www" / LEGACY_CARD_FILENAME
        )
        try:
            if legacy_file.exists():
                legacy_file.unlink()
        except OSError as err:
            _LOGGER.debug("Could not remove legacy card file %s: %s", legacy_file, err)

    async def async_restore_scenes(self) -> None:
        """Restore dynamic scene entities from storage."""
        for entity_id, item in list(self.meta.items()):
            if not isinstance(item, dict):
                continue

            snapshot = item.get("snapshot")
            if not isinstance(snapshot, dict) or not snapshot:
                continue

            scene_id = _scene_id_from_entity_id(entity_id)
            await self.hass.services.async_call(
                SCENE_DOMAIN,
                "create",
                {"scene_id": scene_id, "entities": _scene_create_entities(snapshot)},
                blocking=True,
            )
            self.async_set_scene_attributes(entity_id, item)

    async def async_user_label(self, context: Context | None) -> str:
        """Return a stable, readable label for the service caller."""
        user_id = getattr(context, "user_id", None)
        if not user_id:
            return "system"

        try:
            user = await self.hass.auth.async_get_user(user_id)
        except (HomeAssistantError, AttributeError):
            return str(user_id)

        if user is None:
            return str(user_id)

        for attr in ("name", "username"):
            value = getattr(user, attr, None)
            if value:
                return str(value)

        return str(user_id)

    async def async_save_data(
        self,
        *,
        action: str | None = None,
        scene_entity_id: str | None = None,
        modified: bool = False,
        context: Context | None = None,
        user: str | None = None,
        when: str | None = None,
    ) -> None:
        """Persist data and notify platforms."""
        when = when or _utc_now_iso()
        user = user or await self.async_user_label(context)

        self.data["revision"] = self.revision + 1
        self.data["updated_at"] = time.time()

        if modified:
            self.data["last_modified"] = when
            self.data["last_modified_by"] = user

        if action:
            self.data["last_action"] = action
            self.data["last_action_by"] = user
            self.data["last_scene"] = scene_entity_id
            self.data["last_triggered"] = when

        await self.store.async_save(self.data)
        self.async_notify_updated()

    def async_notify_updated(self) -> None:
        """Notify all entities that runtime data changed."""
        async_dispatcher_send(self.hass, SIGNAL_UPDATED)

    def async_set_scene_attributes(self, entity_id: str, item: dict[str, Any]) -> None:
        """Attach Scene Manager metadata to a Home Assistant scene state."""
        state = self.hass.states.get(entity_id)
        if state is None:
            return

        attrs = dict(state.attributes)
        attrs.update(
            {
                "icon": item.get("icon", "mdi:palette"),
                "theme_color": item.get("color", "#9E9E9E"),
                "scene_manager_room": item.get("room"),
                "scene_manager_order_key": item.get("order_key"),
                "scene_manager_last_modified": item.get("updated_at"),
                "scene_manager_last_modified_by": item.get("updated_by"),
            }
        )
        self.hass.states.async_set(entity_id, state.state, attrs)

    async def async_handle_save_scene(self, call: ServiceCall) -> None:
        """Create or update a dynamic scene and store its metadata."""
        raw_scene_id = call.data.get("scene_id")
        if not raw_scene_id:
            raise ServiceValidationError("scene_id is required")

        scene_id = _slugify(str(raw_scene_id))
        entity_id = f"{SCENE_DOMAIN}.{scene_id}"
        snapshot_payload = call.data.get("snapshot")
        entities_payload = call.data.get("entities")

        if isinstance(snapshot_payload, dict):
            snapshot = _normalise_snapshot(snapshot_payload)
        elif isinstance(entities_payload, dict):
            snapshot = _normalise_snapshot(entities_payload)
        else:
            entities = _normalise_entities(entities_payload)
            snapshot: dict[str, Any] = {}
            for entity in entities:
                state = self.hass.states.get(entity)
                if state is not None:
                    snapshot[entity] = {
                        "state": state.state,
                        "attributes": dict(state.attributes),
                    }

            if not snapshot:
                raise ServiceValidationError("No valid entities to capture")

        replace_entity_id = call.data.get(CONF_REPLACE_ENTITY_ID)
        if replace_entity_id and replace_entity_id != entity_id:
            replace_entity_id = _normalise_scene_entity_id(replace_entity_id)
            self.meta.pop(replace_entity_id, None)
            _remove_from_order(self.order, replace_entity_id)
            self.hass.states.async_remove(replace_entity_id)

        await self.hass.services.async_call(
            SCENE_DOMAIN,
            "create",
            {"scene_id": scene_id, "entities": _scene_create_entities(snapshot)},
            blocking=True,
            context=call.context,
        )

        when = _utc_now_iso()
        user = await self.async_user_label(call.context)
        existing = self.meta.get(entity_id, {})
        item = {
            "icon": str(call.data.get("icon") or existing.get("icon") or "mdi:palette"),
            "color": _normalise_color(call.data.get("color") or existing.get("color")),
            "room": str(call.data.get("room") or existing.get("room") or "unknown"),
            "order_key": str(
                call.data.get(CONF_ORDER_KEY)
                or existing.get("order_key")
                or call.data.get("room")
                or "unknown"
            ),
            "snapshot": snapshot,
            "created_at": existing.get("created_at") or when,
            "created_by": existing.get("created_by") or user,
            "updated_at": when,
            "updated_by": user,
        }
        self.meta[entity_id] = item
        self.async_set_scene_attributes(entity_id, item)

        order_key = item["order_key"]
        requested_order = call.data.get("order")
        if isinstance(requested_order, list):
            self.order[order_key] = self._normalise_saved_order(
                requested_order,
                entity_id,
                replace_entity_id,
            )
        else:
            current_order = self.order.setdefault(order_key, [])
            if isinstance(current_order, list):
                if replace_entity_id in current_order:
                    index = current_order.index(replace_entity_id)
                    current_order[index] = entity_id
                elif entity_id not in current_order:
                    current_order.append(entity_id)
                self.order[order_key] = [
                    value for value in current_order if isinstance(value, str)
                ]

        await self.async_save_data(
            action=SERVICE_SAVE_SCENE,
            scene_entity_id=entity_id,
            modified=True,
            context=call.context,
            user=user,
            when=when,
        )

    def _normalise_saved_order(
        self,
        requested_order: list[Any],
        entity_id: str,
        replace_entity_id: str | None,
    ) -> list[str]:
        """Normalize a card-supplied order while preserving the saved scene."""
        order: list[str] = []
        for raw_value in requested_order:
            if not isinstance(raw_value, str):
                continue
            value = _normalise_scene_entity_id(raw_value)
            if replace_entity_id and value == replace_entity_id:
                value = entity_id
            if value not in order:
                order.append(value)

        if entity_id not in order:
            order.append(entity_id)

        return order

    async def async_handle_delete_scene(self, call: ServiceCall) -> None:
        """Delete a dynamic scene and its metadata."""
        entity_id = _scene_entity_id_from_call(call)
        state_exists = self.hass.states.get(entity_id) is not None
        removed = self.meta.pop(entity_id, None)

        if removed is None and not state_exists:
            raise ServiceValidationError(f"{entity_id} was not found")

        _remove_from_order(self.order, entity_id)
        self.hass.states.async_remove(entity_id)

        await self.async_save_data(
            action=SERVICE_DELETE_SCENE,
            scene_entity_id=entity_id,
            modified=True,
            context=call.context,
        )

    async def async_handle_reorder_scenes(self, call: ServiceCall) -> None:
        """Persist the card scene order for a room or custom order key."""
        room = str(call.data.get("room") or "unknown")
        order_key = str(call.data.get(CONF_ORDER_KEY) or room)
        order = call.data.get("order")

        if not isinstance(order, list):
            raise ServiceValidationError("order must be a list of entity ids")

        self.order[order_key] = [value for value in order if isinstance(value, str)]
        await self.async_save_data(
            action=SERVICE_REORDER_SCENES,
            modified=True,
            context=call.context,
        )

    async def async_handle_activate_scene(self, call: ServiceCall) -> None:
        """Activate a stored scene through the integration service."""
        entity_id = _scene_entity_id_from_call(call)
        source = str(call.data.get("source") or "service")
        transition = call.data.get("transition")
        await self.async_activate_entity_id(
            entity_id,
            source=source,
            transition=transition,
            context=call.context,
        )

    async def async_handle_set_live_mode(self, call: ServiceCall) -> None:
        """Set the persistent live edit mode flag."""
        enabled = call.data.get("enabled")
        if enabled is None:
            raise ServiceValidationError("enabled is required")
        await self.async_set_live_mode(bool(enabled), context=call.context)

    async def async_activate_entity_id(
        self,
        entity_id: str,
        *,
        source: str,
        transition: Any | None = None,
        context: Context | None = None,
    ) -> None:
        """Activate one scene and track the action."""
        if self.hass.states.get(entity_id) is None:
            raise ServiceValidationError(f"{entity_id} was not found")

        service_data: dict[str, Any] = {CONF_ENTITY_ID: entity_id}
        if transition is not None:
            service_data["transition"] = transition

        await self.hass.services.async_call(
            SCENE_DOMAIN,
            "turn_on",
            service_data,
            blocking=True,
            context=context,
        )

        await self.async_save_data(
            action=f"{SERVICE_ACTIVATE_SCENE}:{source}",
            scene_entity_id=entity_id,
            context=context,
        )

    async def async_set_live_mode(
        self,
        enabled: bool,
        *,
        context: Context | None = None,
    ) -> None:
        """Persist live edit mode."""
        if self.live_mode == enabled:
            self.async_notify_updated()
            return

        self.data["live_mode"] = enabled
        await self.async_save_data(
            action=SERVICE_SET_LIVE_MODE,
            modified=True,
            context=context,
        )


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up Scene Manager Ultimate from YAML."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Scene Manager Ultimate from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    manager = SceneManagerRuntime(hass, entry)
    hass.data[DOMAIN][entry.entry_id] = manager
    await manager.async_setup()

    hass.services.async_register(DOMAIN, SERVICE_SAVE_SCENE, manager.async_handle_save_scene)
    hass.services.async_register(
        DOMAIN,
        SERVICE_DELETE_SCENE,
        manager.async_handle_delete_scene,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REORDER_SCENES,
        manager.async_handle_reorder_scenes,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ACTIVATE_SCENE,
        manager.async_handle_activate_scene,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_LIVE_MODE,
        manager.async_handle_set_live_mode,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Scene Manager Ultimate config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False

    for service in (
        SERVICE_SAVE_SCENE,
        SERVICE_DELETE_SCENE,
        SERVICE_REORDER_SCENES,
        SERVICE_ACTIVATE_SCENE,
        SERVICE_SET_LIVE_MODE,
    ):
        hass.services.async_remove(DOMAIN, service)

    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return True


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Clean up storage when the config entry is removed."""
    manager = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if manager is None:
        manager = SceneManagerRuntime(hass, entry)
        manager.data = await _async_load_data(manager.store)

    await manager.async_remove()
