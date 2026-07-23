"""Scene Manager Ultimate integration."""

from __future__ import annotations

from copy import deepcopy
import logging
from pathlib import Path
import re
import time
from typing import Any

from homeassistant.components.scene import DOMAIN as SCENE_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_URL
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.storage import Store

try:
    from homeassistant.components.lovelace.const import LOVELACE_DATA, MODE_STORAGE
except ImportError:  # pragma: no cover - Lovelace internals changed over time
    LOVELACE_DATA = "lovelace"
    MODE_STORAGE = "storage"

try:
    from homeassistant.exceptions import ServiceValidationError
except ImportError:  # pragma: no cover - older Home Assistant versions
    ServiceValidationError = HomeAssistantError  # type: ignore[misc,assignment]

_LOGGER = logging.getLogger(__name__)

DOMAIN = "scene_manager"
VERSION = "1.0.18"

STORAGE_KEY = "scene_manager_data"
STORAGE_VERSION = 1
REGISTRY_ENTITY_ID = "sensor.scene_manager_registry"

CARD_REPOSITORY = "Micpi/scene-manager-card"
CARD_RESOURCE_URL = "/hacsfiles/scene-manager-card/scene-manager-card.js"
LEGACY_CARD_URL = f"/{DOMAIN}/card.js"
LEGACY_CARD_FILENAME = "scene-manager-card.js"

CONF_ORDER_KEY = "order_key"
CONF_REPLACE_ENTITY_ID = "replace_entity_id"

_SERVICE_SAVE_SCENE = "save_scene"
_SERVICE_DELETE_SCENE = "delete_scene"
_SERVICE_REORDER_SCENES = "reorder_scenes"


def _new_data() -> dict[str, Any]:
    return {"meta": {}, "order": {}, "revision": 0}


async def _async_load_data(store: Store) -> dict[str, Any]:
    raw = await store.async_load()
    if not isinstance(raw, dict):
        return _new_data()

    meta = raw.get("meta")
    order = raw.get("order")

    raw["meta"] = meta if isinstance(meta, dict) else {}
    raw["order"] = order if isinstance(order, dict) else {}
    raw["revision"] = int(raw.get("revision", 0) or 0)
    return raw


def _public_meta(meta: dict[str, Any]) -> dict[str, Any]:
    public: dict[str, Any] = {}
    for entity_id, scene_data in meta.items():
        if not isinstance(scene_data, dict):
            continue
        public[entity_id] = {
            key: value for key, value in scene_data.items() if key != "snapshot"
        }
    return public


def _publish_registry(hass: HomeAssistant, data: dict[str, Any]) -> None:
    hass.states.async_set(
        REGISTRY_ENTITY_ID,
        str(data.get("revision", 0)),
        {
            "version": VERSION,
            "card_repository": CARD_REPOSITORY,
            "card_resource_url": CARD_RESOURCE_URL,
            "meta": _public_meta(data["meta"]),
            "order": data["order"],
        },
    )


async def _async_save_data(
    hass: HomeAssistant, store: Store, data: dict[str, Any]
) -> None:
    data["revision"] = int(data.get("revision", 0) or 0) + 1
    data["updated_at"] = time.time()
    await store.async_save(data)
    _publish_registry(hass, data)


def _slugify(value: Any, fallback: str | None = None) -> str:
    if not isinstance(value, str):
        value = "" if value is None else str(value)
    slug = re.sub(r"[^a-z0-9_]+", "_", value.lower()).strip("_")
    if not slug:
        if fallback is not None:
            return fallback
        raise ServiceValidationError("scene_id must contain at least one valid character")
    return slug


def _scene_entity_id_from_call(call: ServiceCall) -> str:
    entity_id = call.data.get("entity_id")
    scene_id = call.data.get("scene_id")

    if isinstance(entity_id, str) and entity_id:
        if not entity_id.startswith("scene."):
            raise ServiceValidationError("entity_id must be a scene entity")
        return entity_id

    if isinstance(scene_id, str) and scene_id:
        if scene_id.startswith("scene."):
            return scene_id
        return f"scene.{_slugify(scene_id)}"

    raise ServiceValidationError("entity_id or scene_id is required")


def _normalise_entities(value: Any) -> list[str]:
    if isinstance(value, str):
        entities = [value]
    elif isinstance(value, list):
        entities = value
    else:
        raise ServiceValidationError("entities must be a list of entity IDs")

    clean_entities = [
        entity_id.strip()
        for entity_id in entities
        if isinstance(entity_id, str) and entity_id.strip()
    ]
    if not clean_entities:
        raise ServiceValidationError("At least one entity is required")
    return clean_entities


def _normalise_color(value: Any) -> str:
    if isinstance(value, list) and len(value) >= 3:
        try:
            red, green, blue = (max(0, min(255, int(channel))) for channel in value[:3])
        except (TypeError, ValueError):
            return "#9E9E9E"
        return f"#{red:02X}{green:02X}{blue:02X}"

    if isinstance(value, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", value.strip()):
        return value.strip()

    return "#9E9E9E"


def _remove_from_order(data: dict[str, Any], entity_id: str) -> None:
    for key, scenes in list(data["order"].items()):
        if not isinstance(scenes, list):
            data["order"][key] = []
            continue
        data["order"][key] = [scene for scene in scenes if scene != entity_id]


async def _async_restore_scenes(hass: HomeAssistant, data: dict[str, Any]) -> int:
    restored_count = 0
    for scene_entity_id, scene_data in data["meta"].items():
        if not isinstance(scene_data, dict):
            continue

        snapshot = scene_data.get("snapshot")
        if not isinstance(snapshot, dict) or not snapshot:
            continue

        scene_id = (
            scene_entity_id.split(".", 1)[1]
            if "." in scene_entity_id
            else scene_entity_id
        )

        try:
            await hass.services.async_call(
                SCENE_DOMAIN,
                "create",
                {"scene_id": scene_id, "entities": deepcopy(snapshot)},
                blocking=True,
            )

            state = hass.states.get(scene_entity_id)
            if state is not None:
                attrs = dict(state.attributes)
                if scene_data.get("icon"):
                    attrs["icon"] = scene_data["icon"]
                if scene_data.get("color"):
                    attrs["theme_color"] = scene_data["color"]
                if scene_data.get("room"):
                    attrs["room"] = scene_data["room"]
                if scene_data.get(CONF_ORDER_KEY):
                    attrs[CONF_ORDER_KEY] = scene_data[CONF_ORDER_KEY]
                hass.states.async_set(scene_entity_id, state.state, attrs)

            restored_count += 1
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Failed to restore scene %s: %s", scene_entity_id, err)

    return restored_count


async def _async_get_lovelace_resources(hass: HomeAssistant) -> Any | None:
    lovelace_data = hass.data.get(LOVELACE_DATA)
    if lovelace_data is None:
        return None

    if isinstance(lovelace_data, dict):
        resource_mode = lovelace_data.get("resource_mode", MODE_STORAGE)
        resources = lovelace_data.get("resources")
    else:
        resource_mode = getattr(lovelace_data, "resource_mode", MODE_STORAGE)
        resources = getattr(lovelace_data, "resources", None)

    if resource_mode != MODE_STORAGE or resources is None:
        return None

    if hasattr(resources, "async_get_info"):
        await resources.async_get_info()

    return resources


def _resource_url_path(url: Any) -> str:
    if not isinstance(url, str):
        return ""
    return url.split("?", 1)[0]


async def _async_remove_legacy_lovelace_resource(hass: HomeAssistant) -> bool:
    resources = await _async_get_lovelace_resources(hass)
    if resources is None or not hasattr(resources, "async_items"):
        return False

    removed = False
    for item in list(resources.async_items() or []):
        if _resource_url_path(item.get(CONF_URL)) != LEGACY_CARD_URL:
            continue
        item_id = item.get("id")
        if item_id is None or not hasattr(resources, "async_delete_item"):
            continue
        await resources.async_delete_item(item_id)
        removed = True
    return removed


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the integration from YAML."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Scene Manager Ultimate from a config entry."""
    _LOGGER.info("Setting up Scene Manager Ultimate v%s", VERSION)

    store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
    data = await _async_load_data(store)

    restored_count = await _async_restore_scenes(hass, data)
    _LOGGER.info("Scene Manager restored %d scene(s)", restored_count)

    if data.pop("resource_registered", None):
        await _async_remove_legacy_lovelace_resource(hass)
        await store.async_save(data)

    _publish_registry(hass, data)

    async def handle_save_scene(call: ServiceCall) -> None:
        scene_id = _slugify(call.data.get("scene_id"))
        full_entity_id = f"scene.{scene_id}"
        replace_entity_id = call.data.get(CONF_REPLACE_ENTITY_ID)
        entities = _normalise_entities(call.data.get("entities"))
        icon = call.data.get("icon") or "mdi:palette"
        color = _normalise_color(call.data.get("color", "#9E9E9E"))
        room = _slugify(call.data.get("room"), "unknown")
        order_key = _slugify(call.data.get(CONF_ORDER_KEY), room)

        snapshot: dict[str, Any] = {}
        for entity_id in entities:
            state_obj = hass.states.get(entity_id)
            if state_obj is None:
                _LOGGER.debug("Skipping unknown snapshot entity: %s", entity_id)
                continue
            entity_data = dict(state_obj.attributes)
            entity_data["state"] = state_obj.state
            snapshot[entity_id] = entity_data

        if not snapshot:
            raise ServiceValidationError("No valid entity state could be captured")

        await hass.services.async_call(
            SCENE_DOMAIN,
            "create",
            {"scene_id": scene_id, "snapshot_entities": entities},
            blocking=True,
        )

        if (
            isinstance(replace_entity_id, str)
            and replace_entity_id.startswith("scene.")
            and replace_entity_id != full_entity_id
        ):
            hass.states.async_remove(replace_entity_id)
            data["meta"].pop(replace_entity_id, None)
            _remove_from_order(data, replace_entity_id)

        _remove_from_order(data, full_entity_id)
        data["order"].setdefault(order_key, [])
        if full_entity_id not in data["order"][order_key]:
            data["order"][order_key].append(full_entity_id)

        data["meta"][full_entity_id] = {
            "icon": icon,
            "color": color,
            "room": room,
            CONF_ORDER_KEY: order_key,
            "snapshot": snapshot,
        }

        state = hass.states.get(full_entity_id)
        if state is not None:
            attrs = dict(state.attributes)
            attrs["icon"] = icon
            attrs["theme_color"] = color
            attrs["room"] = room
            attrs[CONF_ORDER_KEY] = order_key
            hass.states.async_set(full_entity_id, state.state, attrs)

        await _async_save_data(hass, store, data)

    async def handle_delete_scene(call: ServiceCall) -> None:
        entity_id = _scene_entity_id_from_call(call)
        hass.states.async_remove(entity_id)
        data["meta"].pop(entity_id, None)
        _remove_from_order(data, entity_id)
        await _async_save_data(hass, store, data)

    async def handle_reorder_scenes(call: ServiceCall) -> None:
        order_key = _slugify(
            call.data.get(CONF_ORDER_KEY) or call.data.get("room"),
            "unknown",
        )
        order = call.data.get("order", [])
        if not isinstance(order, list):
            raise ServiceValidationError("order must be a list of scene entity IDs")

        data["order"][order_key] = [
            entity_id
            for entity_id in order
            if isinstance(entity_id, str) and entity_id.startswith("scene.")
        ]
        await _async_save_data(hass, store, data)

    hass.services.async_register(DOMAIN, _SERVICE_SAVE_SCENE, handle_save_scene)
    hass.services.async_register(DOMAIN, _SERVICE_DELETE_SCENE, handle_delete_scene)
    hass.services.async_register(DOMAIN, _SERVICE_REORDER_SCENES, handle_reorder_scenes)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    hass.services.async_remove(DOMAIN, _SERVICE_SAVE_SCENE)
    hass.services.async_remove(DOMAIN, _SERVICE_DELETE_SCENE)
    hass.services.async_remove(DOMAIN, _SERVICE_REORDER_SCENES)

    if hass.states.get(REGISTRY_ENTITY_ID) is not None:
        hass.states.async_remove(REGISTRY_ENTITY_ID)

    return True


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Clean up when the integration is removed."""
    store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
    data = await _async_load_data(store)

    await _async_remove_legacy_lovelace_resource(hass)

    if data.get("copied_to_www"):
        legacy_www_file = Path(hass.config.path("www")) / LEGACY_CARD_FILENAME
        if legacy_www_file.exists():
            try:
                await hass.async_add_executor_job(legacy_www_file.unlink)
            except OSError as err:
                _LOGGER.debug("Could not remove legacy www card file: %s", err)

    for notification_id in (
        "scene_manager_add_resource",
        "scene_manager_add_resource_configflow",
        "scene_manager_add_resource_options",
    ):
        try:
            await hass.services.async_call(
                "persistent_notification",
                "dismiss",
                {"notification_id": notification_id},
                blocking=True,
            )
        except Exception:  # noqa: BLE001
            pass

    if hass.states.get(REGISTRY_ENTITY_ID) is not None:
        hass.states.async_remove(REGISTRY_ENTITY_ID)

    await store.async_remove()
