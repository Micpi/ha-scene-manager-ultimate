import logging
import json
import os
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.scene import DOMAIN as SCENE_DOMAIN
# --- IMPORT CORRIGÉ ---
from homeassistant.helpers.storage import Store 

_LOGGER = logging.getLogger(__name__)
DOMAIN = "scene_manager"
STORAGE_KEY = "scene_manager_data"
STORAGE_VERSION = 1

async def async_setup(hass: HomeAssistant, config: dict):
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    
    # --- LIGNE CORRIGÉE ---
    # On utilise la classe Store importée directement
    store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
    
    data = await store.async_load() or {"meta": {}, "order": {}}

    # Fonction pour mettre à jour le sensor
    def update_sensor():
        hass.states.async_set(
            "sensor.scene_manager_registry", 
            str(os.urandom(8).hex()), 
            {"meta": data["meta"], "order": data["order"]}
        )

    # Init du sensor
    update_sensor()

    # --- DÉFINITION DES SERVICES ---
    
    async def handle_save_scene(call: ServiceCall):
        scene_id = call.data.get("scene_id")
        entities = call.data.get("entities", [])
        icon = call.data.get("icon", "mdi:palette")
        color = call.data.get("color", "#9E9E9E")
        room = call.data.get("room", "unknown")
        
        full_entity_id = f"scene.{scene_id}"

        # Appel natif
        await hass.services.async_call(
            SCENE_DOMAIN, "create",
            {"scene_id": scene_id, "snapshot_entities": entities},
            blocking=True
        )

        # Sauvegarde Meta
        data["meta"][full_entity_id] = {"icon": icon, "color": color, "room": room}
        
        if room not in data["order"]: data["order"][room] = []
        if full_entity_id not in data["order"][room]: data["order"][room].append(full_entity_id)

        await store.async_save(data)
        
        # Force state update (pour l'icone immédiate)
        state = hass.states.get(full_entity_id)
        if state:
            new_attrs = dict(state.attributes)
            new_attrs['icon'] = icon
            new_attrs['theme_color'] = color
            hass.states.async_set(full_entity_id, state.state, new_attrs)

        update_sensor()

    async def handle_delete_scene(call: ServiceCall):
        entity_id = call.data.get("entity_id")
        
        # On essaie de supprimer l'entité de HA
        try:
            hass.states.async_remove(entity_id)
        except:
            pass # Pas grave si elle n'existe déjà plus
        
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
        # Remplacement du script Python manuel
        eid = call.data.get("entity_id")
        st = call.data.get("state")
        attrs = call.data.get("attributes")
        icn = call.data.get("icon")
        clr = call.data.get("color")
        
        if eid:
            ns = hass.states.get(eid)
            c_st = ns.state if ns else (st or "unknown")
            c_at = dict(ns.attributes) if ns else {} # Copie propre
            
            if st: c_st = st
            if attrs: c_at.update(attrs)
            if icn: c_at['icon'] = icn
            if clr: c_at['theme_color'] = clr
            
            hass.states.async_set(eid, c_st, c_at)

    # Enregistrement des services
    hass.services.async_register(DOMAIN, "save_scene", handle_save_scene)
    hass.services.async_register(DOMAIN, "delete_scene", handle_delete_scene)
    hass.services.async_register(DOMAIN, "reorder_scenes", handle_reorder)
    
    # On enregistre les alias "python_script" pour garder la compatibilité avec le JS
    hass.services.async_register("python_script", "set_state", handle_set_state)
    hass.services.async_register("python_script", "delete_entity", handle_delete_scene)

    # Exposition du fichier JS
    hass.http.register_static_path(
        "/scene_manager/card.js",
        hass.config.path("custom_components/scene_manager/www/scene-manager-card.js"),
    )

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Supprime l'intégration."""
    return True