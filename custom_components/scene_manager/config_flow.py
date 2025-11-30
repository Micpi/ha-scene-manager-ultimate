from homeassistant import config_entries
from . import DOMAIN
import voluptuous as vol


class SceneManagerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Gère le flux de configuration UI."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Gère l'étape initiale (quand on clique sur Ajouter)."""

        # Empêche d'installer l'intégration deux fois
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        # Formulaire : option pour afficher une notification d'aide à l'ajout de la ressource
        if user_input is not None:
            notify = bool(user_input.get("notify_add_resource", True))

            # Créer une notification persistante si l'utilisateur le souhaite
            if notify and hasattr(self, 'hass') and self.hass is not None:
                try:
                    message = (
                        "La carte `scene-manager-card.js` est disponible.\n\n"
                        "Pour l'ajouter à Lovelace :\n"
                        "1. UI → Configuration → Tableaux de bord → Ressources\n"
                        "2. Cliquez sur 'Ajouter une ressource' → URL : `/local/scene-manager-card.js` → Type : Module JavaScript\n\n"
                        "Alternativement vous pouvez utiliser la route servie par l'intégration : `/scene_manager/card.js`."
                    )
                    self.hass.services.async_call(
                        "persistent_notification",
                        "create",
                        {
                            "title": "Scene Manager — Ajouter la ressource Lovelace",
                            "message": message,
                            "notification_id": "scene_manager_add_resource_configflow",
                        },
                    )
                except Exception:
                    # Ne pas empêcher la création de l'entrée si la notification échoue
                    pass

            return self.async_create_entry(title="Scene Manager Ultimate", data={"notify_add_resource": notify})

        # Affiche le formulaire pour choisir si on affiche l'aide d'ajout de ressource
        schema = vol.Schema({vol.Optional("notify_add_resource", default=True): bool})
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_get_options_flow(self, config_entry):
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for Scene Manager integration."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            # If requested, create a persistent notification to guide adding the resource
            if user_input.get("show_resource_notification"):
                try:
                    message = (
                        "La carte `scene-manager-card.js` est disponible.\n\n"
                        "Pour l'ajouter à Lovelace :\n"
                        "1. UI → Configuration → Tableaux de bord → Ressources\n"
                        "2. Cliquez sur 'Ajouter une ressource' → URL : `/local/scene-manager-card.js` → Type : Module JavaScript\n\n"
                        "Alternativement vous pouvez utiliser la route servie par l'intégration : `/scene_manager/card.js`."
                    )
                    self.hass.services.async_call(
                        "persistent_notification",
                        "create",
                        {
                            "title": "Scene Manager — Ajouter la ressource Lovelace",
                            "message": message,
                            "notification_id": "scene_manager_add_resource_options",
                        },
                    )
                except Exception:
                    pass

            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema({vol.Optional("show_resource_notification", default=False): bool})
        return self.async_show_form(step_id="init", data_schema=schema)