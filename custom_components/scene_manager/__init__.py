import logging
import json
import os
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.components.scene import DOMAIN as SCENE_DOMAIN
from homeassistant.helpers import entity_registry as er, area_registry as ar

_LOGGER = logging.getLogger(__name__)
DOMAIN = "scene_manager"
STORAGE_KEY = "scene_manager_data"
STORAGE_VERSION = 1

async def async_setup(hass: HomeAssistant, config: dict):
    # 1. Charger les données existantes
    store = hass.helpers.storage.Store(STORAGE_VERSION, STORAGE_KEY)
    data = await store.async_load() or {"meta": {}, "order": {}}

    # 2. Créer un Sensor virtuel pour envoyer les données au Frontend
    # On utilise l'état pour forcer le refresh (timestamp)
    def update_sensor():
        hass.states.async_set(
            "sensor.scene_manager_registry", 
            str(os.urandom(8).hex()), 
            {"meta": data["meta"], "order": data["order"]}
        )

    # Initialisation du sensor au démarrage
    update_sensor()

    # 3. Service: Sauvegarder Scène
    async def handle_save_scene(call: ServiceCall):
        scene_id = call.data.get("scene_id")
        entities = call.data.get("entities", [])
        icon = call.data.get("icon", "mdi:palette")
        color = call.data.get("color", "#9E9E9E")
        room = call.data.get("room", "unknown")
        
        full_entity_id = f"scene.{scene_id}"

        # A. Appeler le service natif scene.create
        await hass.services.async_call(
            SCENE_DOMAIN, "create",
            {"scene_id": scene_id, "snapshot_entities": entities},
            blocking=True
        )

        # B. Sauvegarder les métadonnées
        data["meta"][full_entity_id] = {"icon": icon, "color": color, "room": room}
        
        # Gestion de l'ordre (ajout si nouveau)
        if room not in data["order"]:
            data["order"][room] = []
        if full_entity_id not in data["order"][room]:
            data["order"][room].append(full_entity_id)

        await store.async_save(data)
        
        # C. Forcer l'icône sur l'entité scène native
        state = hass.states.get(full_entity_id)
        if state:
            new_attrs = dict(state.attributes)
            new_attrs['icon'] = icon
            new_attrs['theme_color'] = color
            hass.states.async_set(full_entity_id, state.state, new_attrs)

        update_sensor()

    # 4. Service: Supprimer Scène
    async def handle_delete_scene(call: ServiceCall):
        entity_id = call.data.get("entity_id")
        
        # Supprimer de HA
        hass.states.async_remove(entity_id)
        
        # Supprimer des métadonnées
        if entity_id in data["meta"]:
            del data["meta"][entity_id]
        
        # Supprimer de l'ordre
        for room, scenes in data["order"].items():
            if entity_id in scenes:
                scenes.remove(entity_id)
        
        await store.async_save(data)
        update_sensor()

    # 5. Service: Réorganiser (Drag & Drop)
    async def handle_reorder(call: ServiceCall):
        room = call.data.get("room")
        new_order = call.data.get("order", [])
        
        data["order"][room] = new_order
        await store.async_save(data)
        update_sensor()

    hass.services.async_register(DOMAIN, "save_scene", handle_save_scene)
    hass.services.async_register(DOMAIN, "delete_scene", handle_delete_scene)
    hass.services.async_register(DOMAIN, "reorder_scenes", handle_reorder)

    # Exposition du fichier JS pour le frontend
    hass.http.register_static_path(
        "/scene_manager/card.js",
        hass.config.path("custom_components/scene_manager/www/scene-manager-card.js"),
    )

    return True