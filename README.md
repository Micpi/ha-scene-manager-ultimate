# Scene Manager Ultimate

Scene Manager Ultimate est une integration Home Assistant qui permet de creer, restaurer, organiser et declencher des scenes depuis une carte Lovelace embarquee.

![Version](https://img.shields.io/badge/version-1.0.16-blue)
![Maintenance](https://img.shields.io/badge/maintainer-Micpi-green)
![HACS](https://img.shields.io/badge/HACS-Custom%20Integration-orange)

## Fonctionnalites

- Creation de scenes en capturant l'etat actuel des entites selectionnees.
- Restauration automatique des scenes creees par l'integration apres redemarrage.
- Carte Lovelace `scene-manager-card` incluse dans l'integration.
- Enregistrement automatique de la ressource Lovelace quand Home Assistant utilise les ressources en mode UI/storage.
- Repli propre avec notification persistante si les ressources Lovelace sont gerees en YAML.
- Tri par piece, drag and drop, icone et couleur par scene.
- Nettoyage de la ressource et des donnees au retrait de l'integration.

## Installation HACS

1. Ajoutez ce depot comme depot personnalise HACS de type **Integration**.
2. Installez **Scene Manager Ultimate**.
3. Redemarrez Home Assistant.
4. Allez dans **Parametres** > **Appareils et services** > **Ajouter une integration**.
5. Cherchez **Scene Manager Ultimate** et validez.

La carte est servie par l'integration a cette URL :

```text
/scene_manager/card.js?v=1.0.16
```

En mode Lovelace UI/storage, l'integration tente d'ajouter cette ressource automatiquement. En mode YAML, ajoutez-la manuellement :

```yaml
resources:
  - url: /scene_manager/card.js?v=1.0.16
    type: module
```

## Carte Lovelace

Exemple minimal :

```yaml
type: custom:scene-manager-card
title: Mes scenes
icon: mdi:home-floor-1
```

Options principales :

| Option | Type | Description |
| --- | --- | --- |
| `title` | string | Titre affiche en haut de la carte. |
| `icon` | string | Icone du titre. |
| `room` | string | Piece fixe a afficher, par exemple `salon`. |
| `show_title` | boolean | Affiche ou masque l'en-tete. |
| `button_style` | string | `filled`, `outline` ou `ghost`. |
| `button_shape` | string | `rounded`, `box` ou `circle`. |
| `manual_lights` | boolean | Active la configuration manuelle des pieces/lumieres. |
| `manual_rooms` | list | Liste de pieces manuelles avec leurs lumieres. |

## Services

### `scene_manager.save_scene`

Cree ou met a jour une scene.

- `scene_id` : identifiant de scene, par exemple `salon_film`.
- `entities` : liste d'entites a capturer.
- `icon` : icone MDI.
- `color` : couleur hexadecimale, par exemple `#03A9F4`.
- `room` : piece utilisee pour le filtrage.
- `replace_entity_id` : ancienne scene a supprimer lors d'un renommage.

### `scene_manager.delete_scene`

Supprime une scene et ses metadonnees.

- `entity_id` : entite scene a supprimer.

### `scene_manager.reorder_scenes`

Met a jour l'ordre d'affichage des scenes pour une piece.

- `room` : piece concernee.
- `order` : liste ordonnee d'entites `scene.*`.

## Depannage

Si Home Assistant affiche `Custom element doesn't exist: scene-manager-card`, verifiez que la ressource existe dans **Parametres** > **Tableaux de bord** > menu **Ressources** :

```text
URL: /scene_manager/card.js?v=1.0.16
Type: module
```

Si votre configuration Lovelace est en mode YAML, l'ajout automatique n'est pas possible : ajoutez la ressource dans votre YAML puis rechargez Home Assistant.
