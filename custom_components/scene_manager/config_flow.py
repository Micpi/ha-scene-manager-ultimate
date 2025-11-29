from homeassistant import config_entries
from . import DOMAIN

class SceneManagerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Gère le flux de configuration UI."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Gère l'étape initiale (quand on clique sur Ajouter)."""
        
        # Empêche d'installer l'intégration deux fois
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        # Si l'utilisateur valide (il n'y a pas d'options à remplir ici)
        if user_input is not None:
            return self.async_create_entry(title="Scene Manager Ultimate", data={})

        # Affiche le formulaire (vide ici, juste un bouton Valider)
        return self.async_show_form(step_id="user")