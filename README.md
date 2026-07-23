# Scene Manager Ultimate

Scene Manager Ultimate est le backend Home Assistant utilise par la carte Lovelace **Scene Manager Card**. L'integration gere le stockage, la restauration et les services de scenes; la carte est publiee dans un depot HACS separe pour permettre des mises a jour UI independantes.

![Version](https://img.shields.io/badge/version-1.1.2-blue)
![Maintenance](https://img.shields.io/badge/maintainer-Micpi-green)
![HACS](https://img.shields.io/badge/HACS-Custom%20Integration-orange)

## Fonctionnalites

- Creation de scenes en capturant l'etat actuel des entites selectionnees.
- Restauration automatique des scenes creees par l'integration apres redemarrage.
- Entites Home Assistant natives : capteurs, switch de mode live et boutons d'action.
- Registre public `sensor.scene_manager_registry` pour synchroniser la carte.
- Suivi de la derniere modification, de l'utilisateur responsable et de la derniere action.
- Tri par piece ou par cle d'ordre optionnelle.
- Services stables pour sauvegarder, supprimer, reordonner et declencher les scenes.
- Nettoyage silencieux des anciennes ressources Lovelace creees par les versions qui embarquaient la carte.

## Installation HACS

1. Ajoutez ce depot comme depot personnalise HACS de type **Integration**.
2. Installez **Scene Manager Ultimate**.
3. Redemarrez Home Assistant.
4. Allez dans **Parametres** > **Appareils et services** > **Ajouter une integration**.
5. Cherchez **Scene Manager Ultimate** et validez.

## Carte Lovelace

La carte est maintenant publiee separement :

```text
https://github.com/Micpi/scene-manager-card
```

Ajoutez ce depot dans HACS comme depot personnalise de type **Lovelace**, puis installez **Scene Manager Card**.

Ressource HACS attendue :

```yaml
resources:
  - url: /hacsfiles/scene-manager-card/scene-manager-card.js
    type: module
```

Exemple minimal :

```yaml
type: custom:scene-manager-card
title: Mes scenes
icon: mdi:home-floor-1
```

## Entites creees

- `sensor.scene_manager_registry` : registre lu par la carte, avec `meta`, `order`, revision et informations de carte HACS.
- `sensor.scene_manager_scene_count` : nombre de scenes gerees.
- `sensor.scene_manager_last_modified` : date de derniere modification.
- `sensor.scene_manager_last_modified_by` : utilisateur qui a fait la derniere modification connue.
- `sensor.scene_manager_last_action` : derniere action tracee, avec scene, source et utilisateur en attributs.
- `switch.scene_manager_live_mode` : active ou desactive la modification live depuis la carte et conserve le choix.
- `button.scene_manager_activate_*` : un bouton par scene sauvegardee pour declencher la scene via l'integration.

Quand le mode live est desactive, la carte permet de preparer ou modifier la selection sans piloter les lumieres en direct. Quand il est active, les changements d'etat et de luminosite sont appliques immediatement pendant l'edition.

## Services

### `scene_manager.save_scene`

Cree ou met a jour une scene.

- `scene_id` : identifiant de scene, par exemple `salon_film`.
- `entities` : liste d'entites a capturer.
- `snapshot` : instantane optionnel envoye par la carte pour l'edition non-live.
- `icon` : icone MDI.
- `color` : couleur hexadecimale, par exemple `#03A9F4`.
- `room` : piece utilisee pour le filtrage.
- `order_key` : cle de tri optionnelle pour isoler plusieurs jeux de scenes.
- `replace_entity_id` : ancienne scene a supprimer lors d'un renommage.
- `original_entity_id` : scene editee avant sauvegarde, utilisee pour conserver sa position meme en cas de renommage.
- `position` : index visuel zero-based a conserver pendant la sauvegarde.
- `order` : liste ordonnee optionnelle a appliquer dans la meme sauvegarde.

### `scene_manager.delete_scene`

Supprime une scene et ses metadonnees.

- `entity_id` : entite scene a supprimer.

### `scene_manager.reorder_scenes`

Met a jour l'ordre d'affichage des scenes.

- `room` : piece concernee.
- `order_key` : cle de tri optionnelle. Si absente, `room` est utilise.
- `order` : liste ordonnee d'entites `scene.*`.

### `scene_manager.activate_scene`

Declenche une scene sauvegardee et met a jour le capteur de derniere action.

- `entity_id` : entite scene a declencher.
- `transition` : transition optionnelle en secondes.
- `source` : origine de l'action, par exemple `card`, `button` ou `automation`.

### `scene_manager.set_live_mode`

Active ou desactive le mode live persistant.

- `enabled` : `true` ou `false`.

## Migration depuis les versions avec carte embarquee

Les anciennes versions pouvaient ajouter une ressource `/scene_manager/card.js`. A partir de `v1.0.18`, l'integration ne sert plus cette carte. Installez `scene-manager-card` via HACS et utilisez `/hacsfiles/scene-manager-card/scene-manager-card.js`.
