import logging
import json
import os
import shutil
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.scene import DOMAIN as SCENE_DOMAIN
from homeassistant.helpers.storage import Store 
# --- IMPORT NOUVEAU POUR LA CORRECTION HTTP ---
from homeassistant.components.http import StaticPathConfig

_LOGGER = logging.getLogger(__name__)
DOMAIN = "scene_manager"
STORAGE_KEY = "scene_manager_data"
STORAGE_VERSION = 1

async def async_setup(hass: HomeAssistant, config: dict):
    # Register static path so the frontend asset is available even before
    # a config entry is created. This exposes the file at /scene_manager/card.js
    try:
        await hass.http.async_register_static_paths([
            StaticPathConfig(
                "/scene_manager/card.js",
                hass.config.path("custom_components/scene_manager/www/scene-manager-card.js"),
                True,
            )
        ])
    except Exception:
        # If API not available, just ignore; path will be registered when the
        # config entry is set up (in async_setup_entry).
        _LOGGER.debug("Could not register static path at startup; will try on setup_entry")

    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    _LOGGER.info("scene_manager: async_setup_entry called (V1.0.11)")

    store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
    data = await store.async_load() or {"meta": {}, "order": {}}
    _LOGGER.info("scene_manager: loaded storage data. Scenes count: %d", len(data.get("meta", {})))

    # --- RESTAURATION DES SCÈNES ---
    # On recrée les scènes dans Home Assistant à partir des snapshots sauvegardés
    restored_count = 0
    for scene_entity_id, scene_data in data.get("meta", {}).items():
        try:
            # scene_entity_id est sous la forme "scene.salon_film"
            # On extrait l'ID court "salon_film"
            if "." in scene_entity_id:
                scene_id = scene_entity_id.split(".", 1)[1]
            else:
                scene_id = scene_entity_id

            snapshot = scene_data.get("snapshot", {})
            
            # Si on a un snapshot, on recrée la scène
            if snapshot:
                await hass.services.async_call(
                    SCENE_DOMAIN, "create",
                    {"scene_id": scene_id, "entities": snapshot},
                    blocking=True
                )
                
                # On restaure aussi les attributs cosmétiques (icône, couleur) sur l'entité créée
                state = hass.states.get(scene_entity_id)
                if state:
                    new_attrs = dict(state.attributes)
                    if "icon" in scene_data:
                        new_attrs['icon'] = scene_data["icon"]
                    if "color" in scene_data:
                        new_attrs['theme_color'] = scene_data["color"]
                    hass.states.async_set(scene_entity_id, state.state, new_attrs)
                
                restored_count += 1
        except Exception as e:
            _LOGGER.warning("scene_manager: Failed to restore scene %s: %s", scene_entity_id, e)
            
    _LOGGER.info("scene_manager: Restored %d scenes from storage", restored_count)

    def update_sensor():
        hass.states.async_set(
            "sensor.scene_manager_registry", 
            str(os.urandom(8).hex()), 
            {"meta": data["meta"], "order": data["order"]}
        )

    update_sensor()

    # --- SERVICES ---
    
    async def handle_save_scene(call: ServiceCall):
        _LOGGER.info("scene_manager: handle_save_scene called with data: %s", call.data)
        try:
            scene_id = call.data.get("scene_id")
            entities = call.data.get("entities", [])
            icon = call.data.get("icon", "mdi:palette")
            color = call.data.get("color", "#9E9E9E")
            room = call.data.get("room", "unknown")
            
            # Nettoyage de sécurité du scene_id
            import re
            clean_id = re.sub(r'[^a-z0-9_]', '_', scene_id.lower()).strip('_')
            if clean_id != scene_id:
                _LOGGER.warning("scene_manager: scene_id '%s' cleaned to '%s'", scene_id, clean_id)
                scene_id = clean_id
            
            full_entity_id = f"scene.{scene_id}"

            # 1. Capturer l'état actuel des entités pour la persistance (Snapshot)
            snapshot = {}
            for entity_id in entities:
                state_obj = hass.states.get(entity_id)
                if state_obj:
                    # On sauvegarde l'état et les attributs pour pouvoir les restaurer via scene.create
                    entity_data = dict(state_obj.attributes)
                    entity_data["state"] = state_obj.state
                    snapshot[entity_id] = entity_data

            # 2. Créer la scène dans Home Assistant (immédiat)
            try:
                await hass.services.async_call(
                    SCENE_DOMAIN, "create",
                    {"scene_id": scene_id, "snapshot_entities": entities},
                    blocking=True
                )
                _LOGGER.info("scene_manager: HA scene created: %s", full_entity_id)
            except Exception as e:
                _LOGGER.error("scene_manager: Failed to create HA scene: %s", e)
                return # Stop if we can't create the scene

            # 3. Mettre à jour les métadonnées AVEC LE SNAPSHOT
            data["meta"][full_entity_id] = {
                "icon": icon, 
                "color": color, 
                "room": room,
                "snapshot": snapshot # On sauvegarde le snapshot !
            }
            
            if room not in data["order"]: data["order"][room] = []
            if full_entity_id not in data["order"][room]: data["order"][room].append(full_entity_id)

            # 4. Sauvegarder sur le disque
            try:
                await store.async_save(data)
                _LOGGER.info("scene_manager: SUCCESS - Data saved to storage. Total scenes: %d", len(data["meta"]))
            except Exception as e:
                _LOGGER.error("scene_manager: CRITICAL - Failed to save to storage: %s", e)
            
            # 5. Mettre à jour l'état pour l'UI immédiate
            state = hass.states.get(full_entity_id)
            if state:
                new_attrs = dict(state.attributes)
                new_attrs['icon'] = icon
                new_attrs['theme_color'] = color
                hass.states.async_set(full_entity_id, state.state, new_attrs)

            update_sensor()
            
        except Exception as e:
            _LOGGER.error("scene_manager: Unexpected error in handle_save_scene: %s", e)

    async def handle_delete_scene(call: ServiceCall):
        entity_id = call.data.get("entity_id")
        try:
            hass.states.async_remove(entity_id)
        except:
            pass
        
        if entity_id in data["meta"]: del data["meta"][entity_id]
        
        for room, scenes in data["order"].items():
            if entity_id in scenes: scenes.remove(entity_id)
        
        await store.async_save(data)
        update_sensor()

    async def handle_reorder(call: ServiceCall):
        room = call.data.get("room")
        new_order = call.data.get("order", [])
        data["order"][room] = new_order
        await store.async_save(data)
        update_sensor()
    
    async def handle_set_state(call: ServiceCall):
        eid = call.data.get("entity_id")
        st = call.data.get("state")
        attrs = call.data.get("attributes")
        icn = call.data.get("icon")
        clr = call.data.get("color")
        
        if eid:
            ns = hass.states.get(eid)
            c_st = ns.state if ns else (st or "unknown")
            c_at = dict(ns.attributes) if ns else {}
            
            if st: c_st = st
            if attrs: c_at.update(attrs)
            if icn: c_at['icon'] = icn
            if clr: c_at['theme_color'] = clr
            
            hass.states.async_set(eid, c_st, c_at)

    hass.services.async_register(DOMAIN, "save_scene", handle_save_scene)
    hass.services.async_register(DOMAIN, "delete_scene", handle_delete_scene)
    hass.services.async_register(DOMAIN, "reorder_scenes", handle_reorder)
    hass.services.async_register("python_script", "set_state", handle_set_state)
    hass.services.async_register("python_script", "delete_entity", handle_delete_scene)

    # --- CORRECTION MAJEURE ICI ---
    # On utilise la nouvelle méthode async_register_static_paths
    try:
        await hass.http.async_register_static_paths([
            StaticPathConfig(
                "/scene_manager/card.js",
                hass.config.path("custom_components/scene_manager/www/scene-manager-card.js"),
                True
            )
        ])
    except RuntimeError as err:
        # Route already registered (e.g. registered in async_setup). Ignore.
        _LOGGER.debug("scene_manager: static path already registered: %s", err)
    except Exception as err:
        _LOGGER.debug("scene_manager: could not register static path: %s", err)

    # Copier le fichier JS dans le répertoire `www/` de Home Assistant si possible
    try:
        www_dir = hass.config.path("www")
        if www_dir and os.path.isdir(www_dir):
            src = hass.config.path("custom_components/scene_manager/www/scene-manager-card.js")
            dst = os.path.join(www_dir, "scene-manager-card.js")
            try:
                # Écrire seulement si le fichier n'existe pas ou diffère
                if (not os.path.exists(dst)) or (os.path.getmtime(src) > os.path.getmtime(dst)):
                    shutil.copyfile(src, dst)
                    _LOGGER.info("scene_manager: copied scene-manager-card.js to %s", dst)
                    # mark that we copied the file so we can remove it on uninstall
                    data["copied_to_www"] = True
                    await store.async_save(data)
            except Exception as ex:
                _LOGGER.debug("scene_manager: could not copy JS to www: %s", ex)
    except Exception:
        pass

    # Inform the user (persistent notification) to add the resource in Lovelace
    try:
        # On utilise une nouvelle clé 'resource_notified_v2' pour forcer l'affichage
        # au moins une fois après cette mise à jour, même si une ancienne installation existait.
        already_notified = data.get("resource_notified_v2", False)
        user_wants_notification = entry.data.get("notify_add_resource", True)
        
        _LOGGER.debug("scene_manager: already_notified=%s, user_wants=%s", already_notified, user_wants_notification)

        if user_wants_notification and not already_notified:
            message = (
                "La carte `scene-manager-card.js` a été copiée dans `/local/` sur votre instance Home Assistant.\n\n"
                "Pour l'ajouter à Lovelace :\n"
                "1. UI → Configuration → Tableaux de bord → Ressources\n"
                "2. Cliquez sur 'Ajouter une ressource' → URL : `/local/scene-manager-card.js` → Type : Module JavaScript\n\n"
                "Vous pouvez forcer le rafraîchissement en ajoutant `?v=...` à l'URL si nécessaire."
            )
            _LOGGER.debug("scene_manager: creating persistent notification to ask user to add resource")
            await hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": "Scene Manager — Ajouter la ressource Lovelace",
                    "message": message,
                    "notification_id": "scene_manager_add_resource",
                },
                blocking=True,
            )
            data["resource_notified_v2"] = True
            await store.async_save(data)
            _LOGGER.debug("scene_manager: persistent notification created and storage updated")
    except Exception as ex:
        _LOGGER.debug("scene_manager: could not create persistent notification: %s", ex)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    # remove services
    hass.services.async_remove(DOMAIN, "save_scene")
    hass.services.async_remove(DOMAIN, "delete_scene")
    hass.services.async_remove(DOMAIN, "reorder_scenes")

    # remove the registry sensor
    try:
        if hass.states.get("sensor.scene_manager_registry"):
            hass.states.async_remove("sensor.scene_manager_registry")
    except Exception:
        pass

    return True

async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Called when the entry is removed (deleted) from Home Assistant."""
    store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
    try:
        data = await store.async_load() or {}
    except Exception:
        data = {}

    # remove copied www file if we created it
    try:
        if data.get("copied_to_www"):
            www_file = hass.config.path("www/scene-manager-card.js")
            if os.path.exists(www_file):
                try:
                    os.remove(www_file)
                    _LOGGER.info("scene_manager: removed copied www file %s", www_file)
                except Exception as ex:
                    _LOGGER.debug("scene_manager: could not remove www file: %s", ex)
    except Exception:
        pass

    # dismiss persistent notifications we may have created
    for nid in ("scene_manager_add_resource", "scene_manager_add_resource_configflow", "scene_manager_add_resource_options"):
        try:
            hass.services.async_call("persistent_notification", "dismiss", {"notification_id": nid})
        except Exception:
            pass

    # remove stored data file to ensure a clean reinstall
    try:
        await store.async_remove()
        _LOGGER.info("scene_manager: removed stored data on remove_entry")
    except Exception:
        pass